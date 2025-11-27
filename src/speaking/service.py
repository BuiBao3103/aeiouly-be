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
from google.cloud import speech

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


# Logger for speaking service
logger = logging.getLogger(__name__)

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện nói"

class SpeakingService:
    """Service for speaking practice and speech-to-text conversion"""
    
    # Target format: always convert to WAV with LINEAR16 encoding at 16000 Hz
    TARGET_SAMPLE_RATE = 16000
    TARGET_ENCODING = speech.RecognitionConfig.AudioEncoding.LINEAR16
    
    # Supported input formats (will be converted to WAV)
    SUPPORTED_INPUT_FORMATS = ['.webm', '.ogg', '.opus', '.wav', '.mp3', '.m4a', '.flac', '.aac', '.mpeg']
    MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024
    MAX_AUDIO_DURATION_SECONDS = 60
    
    def __init__(self):
        """Initialize SpeakingService with Google Cloud Speech client and ADK runner"""
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        try:
            self.client = speech.SpeechClient()
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Speech client: {e}")
            self.client = None
        
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

    def speech_to_text(
        self,
        audio_file: UploadFile,
        language_code: str = "en-US",
    ) -> SpeechToTextResponse:
        """
        Convert audio to text using Google Cloud Speech-to-Text API
        All audio formats are converted to WAV (LINEAR16, 16000 Hz) before sending to Google Cloud
        Supports: WebM, OGG, WAV, MP3, M4A, FLAC, AAC
        """
        if not self.client:
            raise SpeechToTextException("Google Cloud Speech client chưa được khởi tạo")
        
        # Validate and save audio file
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
                wav_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
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
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Build config with fixed WAV format (LINEAR16, 16000 Hz)
            config = speech.RecognitionConfig(
                encoding=self.TARGET_ENCODING,
                sample_rate_hertz=self.TARGET_SAMPLE_RATE,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            
            # Perform speech recognition
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract text from results
            transcribed_text = ""
            for result in response.results:
                transcribed_text += result.alternatives[0].transcript + " "
            
            transcribed_text = transcribed_text.strip()
            
            if not transcribed_text:
                raise SpeechToTextException("Không thể nhận dạng giọng nói từ file âm thanh")
            
            return SpeechToTextResponse(text=transcribed_text)
            
        except SpeechToTextException:
            raise
        except Exception as e:
            raise SpeechToTextException(f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")
        finally:
            # Clean up temporary files
            if os.path.exists(input_file_path):
                os.unlink(input_file_path)
            if wav_file_path and os.path.exists(wav_file_path):
                os.unlink(wav_file_path)
    
    
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
                    "conversation_ended": False
                }
            )
            
            # Generate initial AI greeting via intro_message tool
            query = build_agent_query(
                source="start_conversation_button",
                message="Generate opening line"
            )
            
            initial_response = await call_agent_with_logging(
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
                ai_gender=db_session.ai_gender,
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
            ai_gender=session.ai_gender,
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
                ai_gender=session.ai_gender,
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
        audio_file: Optional[UploadFile] = None,
        db: Session = None
    ) -> ChatMessageResponse:
        """Send a chat message (text or audio) and get agent response"""
        try:
            # Get session
            session = db.query(SpeakingSession).filter(
                SpeakingSession.id == session_id,
                SpeakingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # Determine if message is audio or text
            user_message_text = message_data.content
            is_audio = False
            user_audio_url = None
            
            if audio_file:
                # Convert audio to text
                if not self.client:
                    raise HTTPException(status_code=500, detail="Speech-to-text service chưa được khởi tạo")
                
                try:
                    # Read file content once into memory for parallel processing
                    audio_file.file.seek(0)
                    audio_content = audio_file.file.read()
                    audio_file.file.seek(0)
                    
                    # Create helper functions that work with bytes
                    from io import BytesIO
                    
                    def _stt_from_bytes(content: bytes, filename: str, content_type: str):
                        """Helper to run speech-to-text from bytes"""
                        file_obj = UploadFile(
                            filename=filename,
                            file=BytesIO(content),
                            headers={"content-type": content_type} if content_type else {}
                        )
                        return self.speech_to_text(file_obj, "en-US")
                    
                    def _upload_from_bytes(content: bytes, filename: str, content_type: str):
                        """Helper to upload from bytes"""
                        file_obj = UploadFile(
                            filename=filename,
                            file=BytesIO(content),
                            headers={"content-type": content_type} if content_type else {}
                        )
                        return self._upload_user_audio(file_obj)
                    
                    # Run speech-to-text and upload in parallel
                    stt_task = asyncio.to_thread(
                        _stt_from_bytes,
                        audio_content,
                        audio_file.filename or "audio",
                        audio_file.content_type or "audio/wav"
                    )
                    upload_task = asyncio.to_thread(
                        _upload_from_bytes,
                        audio_content,
                        audio_file.filename or "audio",
                        audio_file.content_type or "audio/wav"
                    )
                    
                    # Wait for both to complete
                    stt_response, user_audio_url = await asyncio.gather(
                        stt_task,
                        upload_task
                    )
                    
                    user_message_text = stt_response.text
                    is_audio = True
                except Exception as e:
                    logger.error(f"Error converting audio to text: {e}")
                    raise HTTPException(status_code=400, detail=f"Lỗi khi chuyển đổi audio sang text: {str(e)}")
                
            if not user_message_text:
                raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống")
            
            # Prepare user message (don't commit yet - will commit with agent message)
            user_message = SpeakingChatMessage(
                session_id=session_id,
                role="user",
                content=user_message_text,
                is_audio=is_audio,
                audio_url=user_audio_url,
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
            
            # Check conversation status and get response data from single state query
            conversation_ended = state.get("conversation_ended", False) if isinstance(state, dict) else False
            if conversation_ended:
                session.status = "completed"
            
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
                ai_gender=session.ai_gender,
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
            
            if state.get("conversation_ended"):
                session.status = "completed"
                db.commit()
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
            ai_gender=session.ai_gender,
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