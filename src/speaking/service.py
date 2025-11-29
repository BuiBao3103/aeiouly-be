"""Service layer for Speaking module"""
import os
import tempfile
import sys
import asyncio
from fastapi import UploadFile
# Fix for Python 3.13+: ensure audioop-lts is used if available
try:
    import audioop_lts as audioop
    sys.modules['audioop'] = audioop
except ImportError:
    try:
        import audioop
    except ImportError:
        pass  # Let pydub handle the error
from pydub import AudioSegment
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.speaking.schemas import (
    SpeechToTextResponse,
    SpeakingSessionCreate,
    SpeakingSessionResponse,
    SpeakingSessionListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    HintResponse,
    FinalEvaluationResponse
)
from src.speaking.exceptions import (
    SpeechToTextException,
    SpeakingSessionNotFoundException,
    SpeakingSessionCreationFailedException,
    AgentSessionNotFoundException,
    HintNotAvailableException,
    ChatSendFailedException
)
from src.speaking.models import SpeakingSession, SpeakingChatMessage
from src.config import settings
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import get_database_url
from src.utils.agent_utils import (
    call_agent_with_logging,
    build_agent_query,
    extract_agent_response_text,
    get_agent_state,
    update_session_state,
)
from src.utils.audio_utils import convert_audio_to_wav, validate_audio_file
from src.storage import S3StorageService
import logging
from fastapi import HTTPException
from datetime import datetime
from langdetect import detect, LangDetectException


# Logger for speaking service
logger = logging.getLogger(__name__)

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện nói"

class SpeakingService:
    """Service for speaking practice and speech-to-text conversion"""
    
    # Regional location for Chirp models
    # Chirp 3 available at: "us", "eu" and more regions
    # Chirp 2 available at: us-central1, europe-west4, asia-southeast1
    # Using "us" for Chirp 3 (best for auto-detect)
    SPEECH_REGION = "us"
    
    # Target model for speech recognition
    # Chirp 3 supports native auto-detect with language_codes=["auto"] or ["en-US", "vi-VN"]
    TARGET_MODEL = "chirp_3"
    
    # Target format: always convert to WAV with LINEAR16 encoding at 16000 Hz
    TARGET_SAMPLE_RATE = 16000
    TARGET_ENCODING = cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16
    
    # Supported input formats (will be converted to WAV)
    SUPPORTED_INPUT_FORMATS = ['.webm', '.ogg', '.opus', '.wav', '.mp3', '.m4a', '.flac', '.aac', '.mpeg']
    MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024
    MAX_AUDIO_DURATION_SECONDS = 60
    
    VALID_AI_GENDERS = {"male", "female", "neutral"}

    def __init__(self):
        """Initialize SpeakingService with Google Cloud Speech client and ADK runner"""
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        try:
            # Initialize SpeechClient with regional endpoint for Chirp models
            # Chirp models are only available at regional locations, not global
            logger.info(f"Initializing Speech client with region: {self.SPEECH_REGION}")
            self.client = SpeechClient(
                client_options=ClientOptions(
                    api_endpoint=f"{self.SPEECH_REGION}-speech.googleapis.com"
                )
            )
            self.project_id = settings.GOOGLE_CLOUD_PROJECT_ID
            if not self.project_id:
                logger.warning("GOOGLE_CLOUD_PROJECT_ID not set, speech-to-text may not work")
        except Exception as e:
            logger.error(f"Could not initialize Google Cloud Speech client: {e}", exc_info=True)
            self.client = None
            self.project_id = None
        
        # Initialize ADK session service and runner
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        
        # Initialize runner with speaking_practice (coordinator)
        from src.speaking.speaking_practice_agent.agent import speaking_practice
        self.runner = Runner(
            agent=speaking_practice,
            app_name="SpeakingPractice",
            session_service=self.session_service
        )
        try:
            self.storage_service = S3StorageService()
        except Exception as storage_error:
            logger.warning(f"Could not initialize storage service: {storage_error}")
            self.storage_service = None

    @classmethod
    def _resolve_ai_gender(cls, value: Optional[str]) -> str:
        """Normalize ai_gender, defaulting to neutral when legacy data is missing."""
        if isinstance(value, str) and value.lower() in cls.VALID_AI_GENDERS:
            return value.lower()
        return "neutral"

    def _prepare_audio_data(
        self,
        audio_file: UploadFile,
    ) -> tuple[bytes, str]:
        """
        Validate and convert audio file to WAV format, return audio data and file extension.
        
        Returns:
            tuple: (audio_data: bytes, file_ext: str)
        """
        input_file_path, file_ext = validate_audio_file(
            audio_file=audio_file,
            supported_formats=self.SUPPORTED_INPUT_FORMATS,
            max_size_bytes=self.MAX_AUDIO_FILE_SIZE,
            max_duration_seconds=self.MAX_AUDIO_DURATION_SECONDS,
            exception_cls=SpeechToTextException,
        )
        wav_file_path = None

        try:
            # Optimize: Only convert if necessary
            # Check if file is already in correct format (WAV, 16000 Hz, mono, LINEAR16)
            needs_conversion = True
            if file_ext == '.wav':
                try:
                    audio_seg = AudioSegment.from_file(input_file_path)
                    # Only convert if format doesn't match target
                    if (audio_seg.frame_rate == self.TARGET_SAMPLE_RATE and 
                        audio_seg.channels == 1):
                        # File is already in correct format, skip conversion
                        needs_conversion = False
                        final_file_path = input_file_path
                except Exception:
                    # If can't read, we'll convert to be safe
                    pass
            
            # Convert to WAV only if needed
            if needs_conversion:
                fd, wav_file_path = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                convert_audio_to_wav(
                    input_file_path=input_file_path,
                    output_file_path=wav_file_path,
                    target_sample_rate=self.TARGET_SAMPLE_RATE,
                    exception_cls=SpeechToTextException,
                )
                final_file_path = wav_file_path
            
            # Read converted WAV file
            with open(final_file_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data, file_ext
            
        except SpeechToTextException:
            raise
        except Exception as e:
            logger.error(f"Error preparing audio data: {type(e).__name__}: {str(e)}", exc_info=True)
            raise SpeechToTextException(f"Lỗi khi chuẩn bị file âm thanh: {str(e)}")
        finally:
            # Clean up temporary files
            if os.path.exists(input_file_path):
                try:
                    os.unlink(input_file_path)
                except Exception:
                    pass
            if wav_file_path and os.path.exists(wav_file_path):
                try:
                    os.unlink(wav_file_path)
                except Exception:
                    pass

    def _recognize_single(
        self,
        audio_data: bytes,
        language_code: str,
    ) -> tuple[str, float]:
        """
        Perform speech recognition with a single language.
        
        Args:
            audio_data: Audio data in bytes (WAV format, LINEAR16, 16000 Hz)
            language_code: Language code to use (e.g., "en-US", "vi-VN")
        
        Returns:
            tuple: (transcribed_text: str, average_confidence: float)
        """
        # Build config for v2 API with chirp_2 model
        config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=self.TARGET_ENCODING,
                sample_rate_hertz=self.TARGET_SAMPLE_RATE,
                audio_channel_count=1,
            ),
            language_codes=[language_code],
            model=self.TARGET_MODEL,  # Use chirp_2 model for best accuracy with accented speech
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True,
                max_alternatives=3,  # Get multiple alternatives for better accuracy
            )
        )
        
        # Create request for v2 API with regional recognizer path
        recognizer = f"projects/{self.project_id}/locations/{self.SPEECH_REGION}/recognizers/_"
        request = cloud_speech.RecognizeRequest(
            recognizer=recognizer,
            config=config,
            content=audio_data,
        )
        
        # Perform speech recognition
        response = self.client.recognize(request=request)
        
        # Extract text and calculate average confidence
        transcribed_text = ""
        confidences = []
        
        for result in response.results:
            if not result.alternatives:
                continue
            top_alternative = result.alternatives[0]
            confidence = top_alternative.confidence or 0.0
            transcript = top_alternative.transcript
            transcribed_text += transcript + " "
            confidences.append(confidence)
        
        transcribed_text = transcribed_text.strip()
        
        if not transcribed_text:
            logger.error("No transcript found in API response")
            raise SpeechToTextException("Không thể nhận dạng giọng nói từ file âm thanh")
        
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return transcribed_text, average_confidence

    def speech_to_text(
        self,
        audio_file: UploadFile,
        language_code: str = "en-US",
        is_save: bool = False,
        auto_detect: bool = False,
    ) -> SpeechToTextResponse:
        """
        Convert audio to text using Google Cloud Speech-to-Text API
        All audio formats are converted to WAV (LINEAR16, 16000 Hz) before sending to Google Cloud
        Supports: WebM, OGG, WAV, MP3, M4A, FLAC, AAC
        
        Uses chirp_3 model for best accuracy with accented speech, especially useful for 
        Vietnamese speakers speaking English. Chirp 3 supports native auto-detect and is 
        trained on millions of hours of multilingual audio, providing superior accuracy 
        compared to standard models.
        
        Args:
            audio_file: Audio file to transcribe
            language_code: Language code (default: "en-US"). Ignored if auto_detect=True
            is_save: Whether to save audio file to S3
            auto_detect: If True, automatically detects between English (en-US) and Vietnamese (vi-VN)
                using Chirp 3's native auto-detection feature
        """
        if not self.client:
            logger.error("Google Cloud Speech client chưa được khởi tạo")
            raise SpeechToTextException("Google Cloud Speech client chưa được khởi tạo")
        
        if not self.project_id:
            logger.error("GOOGLE_CLOUD_PROJECT_ID chưa được cấu hình")
            raise SpeechToTextException("GOOGLE_CLOUD_PROJECT_ID chưa được cấu hình")
        
        # Prepare audio data (validate and convert to WAV)
        audio_data, _ = self._prepare_audio_data(audio_file)
        
        try:
            # Build config for v2 API with Chirp 3 model
            # Chirp 3 supports native auto-detect with language_codes=["auto"] or hint with specific languages
            if auto_detect:
                # Use language hints ["en-US", "vi-VN"] to improve accuracy (better than ["auto"])
                # Chirp 3 will automatically detect which language is being spoken
                config = cloud_speech.RecognitionConfig(
                    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                    language_codes=["en-US", "vi-VN"],  # Hint languages to improve accuracy
                    model=self.TARGET_MODEL,  # chirp_3
                    features=cloud_speech.RecognitionFeatures(
                        enable_automatic_punctuation=True,
                        # Note: enable_denoiser not available in current SDK version
                    )
                )
            else:
                # Use specified language code with explicit decoding
                config = cloud_speech.RecognitionConfig(
                    explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                        encoding=self.TARGET_ENCODING,
                        sample_rate_hertz=self.TARGET_SAMPLE_RATE,
                        audio_channel_count=1,
                    ),
                    language_codes=[language_code],
                    model=self.TARGET_MODEL,  # chirp_3
                    features=cloud_speech.RecognitionFeatures(
                        enable_automatic_punctuation=True,
                        # Note: enable_denoiser not available in current SDK version
                    )
                )
            
            # Create request for v2 API with regional recognizer path
            recognizer = f"projects/{self.project_id}/locations/{self.SPEECH_REGION}/recognizers/_"
            request = cloud_speech.RecognizeRequest(
                recognizer=recognizer,
                config=config,
                content=audio_data,
            )
            
            # Perform speech recognition
            response = self.client.recognize(request=request)
            
            # Extract text and detected language
            transcribed_text = ""
            detected_language = None
            
            for result in response.results:
                if not result.alternatives:
                    continue
                top_alternative = result.alternatives[0]
                transcript = top_alternative.transcript
                transcribed_text += transcript + " "
                
                # In Chirp 3, language_code is returned in the result when using auto-detect
                if auto_detect:
                    result_language = getattr(result, "language_code", None)
                    if result_language:
                        detected_language = result_language
            
            transcribed_text = transcribed_text.strip()
            
            if not transcribed_text:
                logger.error("No transcript found in API response")
                raise SpeechToTextException("Không thể nhận dạng giọng nói từ file âm thanh")

            # If auto_detect but no language_code in results, use langdetect as fallback
            if auto_detect and not detected_language:
                try:
                    lang_code = detect(transcribed_text)
                    language_map = {
                        "en": "en-US",
                        "vi": "vi-VN",
                    }
                    detected_language = language_map.get(lang_code, "en-US")
                except LangDetectException:
                    detected_language = "en-US"

            # Upload audio if needed
            audio_url = None
            if is_save:
                audio_url = self._upload_user_audio(audio_file)
            
            # Log final result only
            logger.info(
                f"Speech-to-text result: text='{transcribed_text[:100]}{'...' if len(transcribed_text) > 100 else ''}', "
                f"detected_language={detected_language}, audio_url={'yes' if audio_url else 'no'}"
            )
            
            return SpeechToTextResponse(
                text=transcribed_text,
                audio_url=audio_url,
                is_save=bool(is_save and audio_url),
                detected_language=detected_language if auto_detect else None,
            )
            
        except SpeechToTextException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in speech_to_text: {type(e).__name__}: {str(e)}", exc_info=True)
            raise SpeechToTextException(f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")
    
    
    def _upload_user_audio(self, audio_file: UploadFile) -> Optional[str]:
        """Upload learner audio to S3 (if configured) and return the public URL."""
        if not self.storage_service or not audio_file:
            return None
        try:
            audio_file.file.seek(0)
        except Exception as seek_err:
            logger.warning(f"Could not reset audio stream before upload: {seek_err}")
            return None
        try:
            return self.storage_service.upload_speaking_audio(
                fileobj=audio_file.file,
                content_type=audio_file.content_type or "audio/wav"
            )
        except Exception as upload_err:
            logger.error(f"Failed to upload learner audio: {upload_err}", exc_info=True)
            return None
    
    async def create_speaking_session(
        self,
        user_id: int,
        session_data: SpeakingSessionCreate,
        db: Session
    ) -> SpeakingSessionResponse:
        """Create a new speaking practice session"""
        try:
            # Create database session
            db_session = SpeakingSession(
                user_id=user_id,
                my_character=session_data.my_character,
                ai_character=session_data.ai_character,
                ai_gender=session_data.ai_gender,
                scenario=session_data.scenario,
                level=session_data.level,
                status="active"
            )
            
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            # Initialize agent session
            await self.session_service.create_session(
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(db_session.id),
                state={
                    "session_id": db_session.id,
                    "my_character": session_data.my_character,
                    "ai_character": session_data.ai_character,
                    "ai_gender": session_data.ai_gender,
                    "scenario": session_data.scenario,
                    "level": session_data.level.value,
                    "chat_history": [],
                    "hint_history": [],
                }
            )
            
            # Generate initial AI greeting via intro_message tool
            query = build_agent_query(
                source="start_conversation_button",
                message="Generate opening line"
            )
            
            await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(db_session.id),
                query=query,
                logger=logger
            )
            
            state = await get_agent_state(
                session_service=self.session_service,
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(db_session.id),
            )
            conversation_data = state.get("chat_response", {}) if isinstance(state, dict) else {}
            
            if not isinstance(conversation_data, dict):
                raise HTTPException(status_code=500, detail="Agent không trả về dữ liệu hợp lệ")
            
            greeting_text = (conversation_data.get("response_text") or "").strip()
            if not greeting_text:
                raise HTTPException(status_code=500, detail="Agent không tạo được câu chào đầu tiên")
            
            translation_candidate = conversation_data.get("translation_sentence")
            translation_sentence = None
            if isinstance(translation_candidate, str):
                translation_sentence = translation_candidate.strip() or None
            
            ai_message = SpeakingChatMessage(
                session_id=db_session.id,
                role="assistant",
                content=greeting_text,
                is_audio=False,
                translation_sentence=translation_sentence
            )
            db.add(ai_message)
            db.commit()
            
            return SpeakingSessionResponse(
                id=db_session.id,
                user_id=db_session.user_id,
                my_character=db_session.my_character,
                ai_character=db_session.ai_character,
                ai_gender=self._resolve_ai_gender(db_session.ai_gender),
                scenario=db_session.scenario,
                level=db_session.level,
                status=db_session.status,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating speaking session: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo phiên luyện nói: {str(e)}")
    
    async def get_speaking_session(
        self,
        session_id: int,
        user_id: int,
        db: Session
    ) -> Optional[SpeakingSessionResponse]:
        """Get a specific speaking session"""
        session = db.query(SpeakingSession).filter(
            SpeakingSession.id == session_id,
            SpeakingSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        return SpeakingSessionResponse(
            id=session.id,
            user_id=session.user_id,
            my_character=session.my_character,
            ai_character=session.ai_character,
            ai_gender=self._resolve_ai_gender(session.ai_gender),
            scenario=session.scenario,
            level=session.level,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def get_user_speaking_sessions(
        self,
        user_id: int,
        db: Session
    ) -> List[SpeakingSessionListResponse]:
        """Get all speaking sessions for a user"""
        sessions = db.query(SpeakingSession).filter(
            SpeakingSession.user_id == user_id
        ).order_by(desc(SpeakingSession.created_at)).all()
        
        return [
            SpeakingSessionListResponse(
                id=session.id,
                my_character=session.my_character,
                ai_character=session.ai_character,
                ai_gender=self._resolve_ai_gender(session.ai_gender),
                scenario=session.scenario,
                level=session.level,
                status=session.status,
                created_at=session.created_at
            )
            for session in sessions
        ]
    
    def delete_speaking_session(self, session_id: int, user_id: int, db: Session) -> bool:
        """Delete a speaking session"""
        session = db.query(SpeakingSession).filter(
            SpeakingSession.id == session_id,
            SpeakingSession.user_id == user_id
        ).first()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        return True
    
    async def send_chat_message(
        self,
        session_id: int,
        user_id: int,
        message_data: ChatMessageCreate,
        audio_url: Optional[str] = None,
        db: Session = None
    ) -> ChatMessageResponse:
        """Send a chat message (text with optional audio URL) and get agent response"""
        try:
            # Get session
            session = db.query(SpeakingSession).filter(
                SpeakingSession.id == session_id,
                SpeakingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            if session.status == "completed":
                raise HTTPException(status_code=400, detail="Phiên luyện nói đã kết thúc")
       
            
            # Get message content and determine if it's audio
            user_message_text = message_data.content
            is_audio = bool(audio_url)  # Set is_audio=True if audio_url is provided
            
            if not user_message_text:
                raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống")
            
            # Prepare user message (don't commit yet - will commit with agent message)
            user_message = SpeakingChatMessage(
                session_id=session_id,
                role="user",
                content=user_message_text,
                is_audio=is_audio,
                audio_url=audio_url,
            )
            db.add(user_message)
            # Don't commit yet - will commit both messages together
            
            # Store user message in temporary state key for conversation_agent callback
            # Only messages routed to conversation_agent will be added to chat_history
            await update_session_state(
                session_service=self.session_service,
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(session_id),
                state_delta={
                    "pending_user_message": user_message_text.strip(),
                },
                author="system",
                invocation_id_prefix="pending_user_message",
                logger=logger
            )
            
            # Query for speaking_practice to route to conversation agent
            query = build_agent_query(
                source="chat_input",
                message=user_message_text
            )
            
            # Get agent response with logging (speaking_practice will route appropriately)
            await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=query,
                logger=logger
            )
            
            # Query state only once after agent call (reuse for all checks)
            state = await get_agent_state(
                session_service=self.session_service,
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(session_id),
            )
            
            
            conversation_data = state.get("chat_response", {}) if isinstance(state, dict) else {}
            
            if not isinstance(conversation_data, dict):
                raise HTTPException(status_code=500, detail="Agent không trả về dữ liệu hợp lệ")
            
            agent_response = (conversation_data.get("response_text") or "").strip()
            if not agent_response:
                raise HTTPException(status_code=500, detail="Agent không tạo được phản hồi")
            
            translation_candidate = conversation_data.get("translation_sentence")
            translation_sentence = None
            if isinstance(translation_candidate, str):
                translation_sentence = translation_candidate.strip() or None
            
            # Save agent response (both messages committed together for better performance)
            agent_message = SpeakingChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_response,
                is_audio=False,
                audio_url=None,
                translation_sentence=translation_sentence
            )
            db.add(agent_message)
            
            # Single commit for both user and agent messages + session status update
            db.commit()
            db.refresh(user_message)
            db.refresh(agent_message)
            
            session_payload = SpeakingSessionResponse(
                id=session.id,
                user_id=session.user_id,
                my_character=session.my_character,
                ai_character=session.ai_character,
                ai_gender=self._resolve_ai_gender(session.ai_gender),
                scenario=session.scenario,
                level=session.level,
                status=session.status,
                created_at=session.created_at,
                updated_at=session.updated_at
            )

            return ChatMessageResponse(
                id=agent_message.id,
                session_id=agent_message.session_id,
                role=agent_message.role,
                content=agent_message.content,
                translation_sentence=agent_message.translation_sentence,
                is_audio=agent_message.is_audio,
                audio_url=agent_message.audio_url,
                session=session_payload,
                created_at=agent_message.created_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error sending chat message: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi tin nhắn: {str(e)}")
    
    def get_chat_history(
        self,
        session_id: int,
        user_id: int,
        db: Session
    ) -> List[ChatMessageResponse]:
        """Get chat history for a session"""
        # Verify session belongs to user
        session = db.query(SpeakingSession).filter(
            SpeakingSession.id == session_id,
            SpeakingSession.user_id == user_id
        ).first()
        
        if not session:
            return []
        
        messages = db.query(SpeakingChatMessage).filter(
            SpeakingChatMessage.session_id == session_id
        ).order_by(SpeakingChatMessage.created_at).all()
        
        return [
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                translation_sentence=msg.translation_sentence,
                is_audio=msg.is_audio,
                audio_url=msg.audio_url,
                session=None,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    
    async def get_conversation_hint(
        self,
        session_id: int,
        user_id: int,
        db: Session
    ) -> HintResponse:
        """Get conversation hint for the last AI message"""
        try:
            # Get session
            session = db.query(SpeakingSession).filter(
                SpeakingSession.id == session_id,
                SpeakingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # Get agent session
            state = await get_agent_state(
                session_service=self.session_service,
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(session_id),
            )
            last_ai_message = state.get("last_ai_message", "")
            
            if not last_ai_message:
                # Try to get from chat history
                chat_history = state.get("chat_history", [])
                for msg in reversed(chat_history):
                    if msg.get("role") == "assistant":
                        last_ai_message = msg.get("content", "")
                        break
            
            if not last_ai_message:
                raise HTTPException(status_code=400, detail="Không có tin nhắn AI để tạo gợi ý")
            
            # Check if hint already exists in hint_history for this message
            hint_history = state.get("hint_history", {}) or {}
            cached_hint = None
            last_ai_order = state.get("last_ai_message_order")
            if last_ai_order is not None:
                cached_hint = hint_history.get(str(last_ai_order))

            if cached_hint and isinstance(cached_hint, dict):
                hint_text = cached_hint.get("hint", "")
                if hint_text:
                    return HintResponse(hint=hint_text, last_ai_message=last_ai_message)

            # No cached hint; call agent to generate one
            query = build_agent_query(
                source="hint_button",
                message="gợi ý"
            )
            
            try:
                hint_response = await call_agent_with_logging(
                    runner=self.runner,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    query=query,
                    logger=logger
                )
            except Exception as agent_error:
                logger.error(f"Error calling hint agent: {agent_error}")
                raise HTTPException(status_code=500, detail=f"Lỗi khi gọi agent tạo gợi ý: {str(agent_error)}")
            
            # Read hint from state after agent finishes
            try:
                state_after = await get_agent_state(
                    session_service=self.session_service,
                    app_name="SpeakingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id),
                )
                
                # Get hint from current_hint_result (output_key)
                hint_result_data = state_after.get("current_hint_result", {})
                if isinstance(hint_result_data, dict):
                    final_hint = hint_result_data.get("hint_text", "")
                else:
                    final_hint = hint_response or ""
            except Exception as state_error:
                logger.error(f"Error reading state after agent run: {state_error}")
                final_hint = hint_response or ""
            
            if not isinstance(final_hint, str) or not final_hint.strip():
                logger.error(f"Invalid hint: type={type(final_hint)}, value={final_hint}")
                raise HTTPException(status_code=502, detail="Không có gợi ý hợp lệ được tạo bởi AI")
            
            return HintResponse(
                hint=final_hint,
                last_ai_message=last_ai_message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_conversation_hint: {type(e).__name__}: {e}", exc_info=True)
            msg = str(e) if e else "Unknown error"
            if "Session not found" in msg:
                raise HTTPException(status_code=404, detail="Không tìm thấy phiên làm việc của agent")
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy gợi ý: {msg}")
    
    async def skip_conversation_turn(
        self,
        session_id: int,
        user_id: int,
        db: Session
    ) -> ChatMessageResponse:
        """Trigger AI to move the conversation forward without a new user utterance."""
        # Get and validate session
        session = db.query(SpeakingSession).filter(
            SpeakingSession.id == session_id,
            SpeakingSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
        
        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Phiên luyện nói đã kết thúc")
        
        # Ask skip_response agent to produce the next natural turn
        query = build_agent_query(
            source="skip_button",
            message="generate skip response"
        )
        
        try:
            await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=query,
                logger=logger
            )
        except Exception as agent_error:
            logger.error(f"Error calling skip agent: {agent_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Lỗi khi bỏ qua lượt: {agent_error}")
        
        # Check if conversation ended and get response from state if needed
        try:
            state = await get_agent_state(
                session_service=self.session_service,
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(session_id),
            )

        except Exception as state_error:
            logger.warning(f"Could not check conversation status: {state_error}")
            state = {}
        
        conversation_data = state.get("chat_response", {}) if isinstance(state, dict) else {}
        
        if not isinstance(conversation_data, dict):
            raise HTTPException(status_code=500, detail="Agent không trả về dữ liệu hợp lệ")
        
        final_response = (conversation_data.get("response_text") or "").strip()
        if not final_response:
            raise HTTPException(status_code=500, detail="Agent không tạo được phản hồi khi bỏ qua lượt")
        
        translation_candidate = conversation_data.get("translation_sentence")
        translation_sentence = None
        if isinstance(translation_candidate, str):
            translation_sentence = translation_candidate.strip() or None
        
        agent_message = SpeakingChatMessage(
            session_id=session_id,
            role="assistant",
            content=final_response,
            is_audio=False,
            audio_url=None,
            translation_sentence=translation_sentence
        )
        db.add(agent_message)
        db.commit()
        db.refresh(agent_message)
        
        session_payload = SpeakingSessionResponse(
            id=session.id,
            user_id=session.user_id,
            my_character=session.my_character,
            ai_character=session.ai_character,
            ai_gender=self._resolve_ai_gender(session.ai_gender),
            scenario=session.scenario,
            level=session.level,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at
        )

        return ChatMessageResponse(
            id=agent_message.id,
            session_id=agent_message.session_id,
            role=agent_message.role,
            content=agent_message.content,
            translation_sentence=agent_message.translation_sentence,
            is_audio=agent_message.is_audio,
            audio_url=agent_message.audio_url,
            session=session_payload,
            created_at=agent_message.created_at
        )
    
    async def get_final_evaluation(
        self,
        session_id: int,
        user_id: int,
        db: Session
    ) -> FinalEvaluationResponse:
        """Get final evaluation for completed session"""
        try:
            # Get session
            session = db.query(SpeakingSession).filter(
                SpeakingSession.id == session_id,
                SpeakingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # update session status to completed
            session.status = "completed"
            db.commit()
            
            # Get final evaluation from speaking_practice (will call final_evaluator tool)
            # Using trigger phrase that matches speaking_practice instruction
            evaluation_response = await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=build_agent_query(
                    source="final_evaluation_button",
                    message="đánh giá cuối"
                ),
                logger=logger
            )
            
            # Get structured output from agent session state
            try:
                # Get the structured output from the agent's session state
                state = await get_agent_state(
                    session_service=self.session_service,
                    app_name="SpeakingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id),
                )
                
                # Extract structured evaluation from session state
                final_eval = state.get("final_evaluation", {})
                
                if final_eval:
                    overall = float(final_eval.get("overall_score", 0))
                    pronunciation = float(final_eval.get("pronunciation_score", 0))
                    fluency = float(final_eval.get("fluency_score", 0))
                    vocabulary = float(final_eval.get("vocabulary_score", 0))
                    grammar = float(final_eval.get("grammar_score", 0))
                    interaction = float(final_eval.get("interaction_score", 0))
                    feedback = str(final_eval.get("feedback", ""))
                    suggestions = final_eval.get("suggestions", [])
                    if not isinstance(suggestions, list):
                        suggestions = []
                else:
                    # Fallback if no structured output
                    overall = 0.0
                    pronunciation = 0.0
                    fluency = 0.0
                    vocabulary = 0.0
                    grammar = 0.0
                    interaction = 0.0
                    feedback = evaluation_response
                    suggestions = []
                    
            except Exception as e:
                logger.error(f"Error getting structured output: {e}")
                # Fallback to zeros
                overall = 0.0
                pronunciation = 0.0
                fluency = 0.0
                vocabulary = 0.0
                grammar = 0.0
                interaction = 0.0
                feedback = evaluation_response
                suggestions = []

            return FinalEvaluationResponse(
                session_id=session_id,
                overall_score=overall,
                pronunciation_score=pronunciation,
                fluency_score=fluency,
                vocabulary_score=vocabulary,
                grammar_score=grammar,
                interaction_score=interaction,
                feedback=feedback,
                suggestions=suggestions,
                completed_at=datetime.now()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_final_evaluation: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy đánh giá: {str(e)}")