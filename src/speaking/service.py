"""Service layer for Speaking module"""
import os
import tempfile
import sys
from fastapi import UploadFile
import mutagen
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
from src.utils.agent_utils import call_agent_with_logging
import logging
from fastapi import HTTPException
from datetime import datetime


# Logger for speaking service
logger = logging.getLogger(__name__)

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện nói"
DEFAULT_GREETING = "Hello! Let's start our conversation."

class SpeakingService:
    """Service for speaking practice and speech-to-text conversion"""
    
    # Target format: always convert to WAV with LINEAR16 encoding at 16000 Hz
    TARGET_SAMPLE_RATE = 16000
    TARGET_ENCODING = speech.RecognitionConfig.AudioEncoding.LINEAR16
    
    # Supported input formats (will be converted to WAV)
    SUPPORTED_INPUT_FORMATS = ['.webm', '.ogg', '.opus', '.wav', '.mp3', '.m4a', '.flac', '.aac', '.mpeg']
    
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

    def _get_file_extension(self, audio_file: UploadFile) -> str:
        """Get file extension from filename or content type"""
        filename = audio_file.filename or ""
        content_type = audio_file.content_type or ""
        
        # Try to get extension from filename
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in self.SUPPORTED_INPUT_FORMATS:
                return ext
        
        # Try to get from content type
        content_type_map = {
            'audio/webm': '.webm',
            'audio/ogg': '.ogg',
            'audio/opus': '.opus',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/x-wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/mp4': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/flac': '.flac',
            'audio/aac': '.aac',
            'audio/aacp': '.aac',
        }
        
        for mime_type, ext in content_type_map.items():
            if mime_type in content_type.lower():
                return ext
        
        raise SpeechToTextException(
            f"Định dạng file không được hỗ trợ. "
            f"Chỉ chấp nhận: {', '.join(self.SUPPORTED_INPUT_FORMATS)}"
        )
    
    def _convert_to_wav(self, input_file_path: str, output_file_path: str) -> str:
        """
        Convert audio file to WAV format (LINEAR16, 16000 Hz, mono)
        Returns: output_file_path
        """
        try:
            # Load audio file using pydub
            audio = AudioSegment.from_file(input_file_path)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to target sample rate if different
            if audio.frame_rate != self.TARGET_SAMPLE_RATE:
                audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
            
            # Export as WAV (LINEAR16 PCM)
            audio.export(
                output_file_path,
                format="wav",
                parameters=["-acodec", "pcm_s16le"]  # 16-bit PCM
            )
            
            return output_file_path
        except Exception as e:
            raise SpeechToTextException(f"Không thể chuyển đổi file âm thanh sang WAV: {str(e)}")
    
    def _validate_audio_file(self, audio_file: UploadFile) -> tuple[str, str]:
        """
        Validate audio file and save to temp file
        Returns: (temp_file_path, file_extension)
        """
        # Get and validate file extension
        file_ext = self._get_file_extension(audio_file)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        try:
            audio_file.file.seek(0)
            content = audio_file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        finally:
            temp_file.close()
        
        # Check file size (max 10MB)
        file_size = os.path.getsize(temp_file_path)
        if file_size > 10 * 1024 * 1024:
            os.unlink(temp_file_path)
            raise SpeechToTextException("Kích thước file không được vượt quá 10MB")
        
        # Check duration (max 60 seconds)
        try:
            audio_info = mutagen.File(temp_file_path)
            if audio_info and hasattr(audio_info.info, 'length'):
                if audio_info.info.length > 60:
                    os.unlink(temp_file_path)
                    raise SpeechToTextException("Độ dài file âm thanh không được vượt quá 60 giây")
        except Exception as e:
            # If we can't read duration, continue anyway (let Google API handle it)
            print(f"Warning: Could not validate duration: {e}")
        
        return temp_file_path, file_ext
    
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
        input_file_path, file_ext = self._validate_audio_file(audio_file)
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
                self._convert_to_wav(input_file_path, wav_file_path)
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
    
    def _build_agent_query(self, source: str, message: str) -> str:
        """
        Build standardized query string for speaking_practice with source metadata.
        
        Args:
            source: Origin of the action (e.g., chat_input, hint_button)
            message: The natural language message or trigger phrase
        
        Returns:
            Formatted string consumed by speaking_practice:
                SOURCE:<source>\nMESSAGE:<message>
        """
        return f"SOURCE:{source}\nMESSAGE:{message}"
    
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
                    "scenario": session_data.scenario,
                    "level": session_data.level.value,
                    "chat_history": [],
                    "hint_history": [],
                    "conversation_ended": False
                }
            )
            
            # Generate initial AI greeting - Agent starts the conversation
            query = self._build_agent_query(
                source="chat_input",
                message="[START_CONVERSATION]"
            )
            
            try:
                initial_response = await call_agent_with_logging(
                    runner=self.runner,
                    user_id=str(user_id),
                    session_id=str(db_session.id),
                    query=query,
                    logger=logger
                )
                
                # Get response from conversation_response in state
                try:
                    agent_session = await self.session_service.get_session(
                        app_name="SpeakingPractice",
                        user_id=str(user_id),
                        session_id=str(db_session.id)
                    )
                    state = agent_session.state or {}
                    conversation_data = state.get("conversation_response", {})
                    if isinstance(conversation_data, dict):
                        greeting_text = conversation_data.get("response_text", "")
                    else:
                        greeting_text = initial_response or DEFAULT_GREETING
                except Exception:
                    greeting_text = initial_response or DEFAULT_GREETING
                
                # Save initial AI message
                ai_message = SpeakingChatMessage(
                    session_id=db_session.id,
                    role="assistant",
                    content=greeting_text,
                    is_audio=False
                )
                db.add(ai_message)
                db.commit()
                
            except Exception as agent_error:
                logger.error(f"Error generating initial greeting: {agent_error}")
                # Use fallback greeting
                ai_message = SpeakingChatMessage(
                    session_id=db_session.id,
                    role="assistant",
                    content=DEFAULT_GREETING,
                    is_audio=False
                )
                db.add(ai_message)
                db.commit()
            
            return SpeakingSessionResponse(
                id=db_session.id,
                user_id=db_session.user_id,
                my_character=db_session.my_character,
                ai_character=db_session.ai_character,
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
            
            if audio_file:
                # Convert audio to text
                if not self.client:
                    raise HTTPException(status_code=500, detail="Speech-to-text service chưa được khởi tạo")
                
                try:
                    stt_response = self.speech_to_text(audio_file, language_code="en-US")
                    user_message_text = stt_response.text
                    is_audio = True
                except Exception as e:
                    logger.error(f"Error converting audio to text: {e}")
                    raise HTTPException(status_code=400, detail=f"Lỗi khi chuyển đổi audio sang text: {str(e)}")
            
            if not user_message_text:
                raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống")
            
            # Save user message
            user_message = SpeakingChatMessage(
                session_id=session_id,
                role="user",
                content=user_message_text,
                is_audio=is_audio
            )
            db.add(user_message)
            db.commit()
            
            # Note: chat_history and user_message will be updated by agent callbacks
            
            # Query for speaking_practice to route to conversation agent
            query = self._build_agent_query(
                source="chat_input",
                message=user_message_text
            )
            
            # Get agent response with logging
            await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=query,
                logger=logger
            )
            
            # Get updated state to check if conversation ended and get response
            try:
                agent_session = await self.session_service.get_session(
                    app_name="SpeakingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id)
                )
                state = agent_session.state or {}
                
                if state.get("conversation_ended", False):
                    session.status = "completed"
                    db.commit()
                
                # Get response from conversation_response (output_key)
                conversation_data = state.get("conversation_response", {})
                if isinstance(conversation_data, dict):
                    agent_response = conversation_data.get("response_text", "")
                else:
                    agent_response = ""
                
                # Get last AI message from chat_history (set by callback)
                chat_history = state.get("chat_history", [])
                last_ai_msg = None
                for msg in reversed(chat_history):
                    if msg.get("role") == "assistant":
                        last_ai_msg = msg.get("content", "")
                        break
                
                if last_ai_msg:
                    # Use message from chat_history if available
                    if not agent_response:
                        agent_response = last_ai_msg
            except Exception as e:
                logger.warning(f"Could not get state after agent response: {e}")
                agent_response = ""
            
            db.refresh(session)
            
            # Save agent response
            agent_message = SpeakingChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_response or "I'm sorry, I didn't understand that.",
                is_audio=False
            )
            db.add(agent_message)
            db.commit()
            
            return ChatMessageResponse(
                id=agent_message.id,
                session_id=agent_message.session_id,
                role=agent_message.role,
                content=agent_message.content,
                is_audio=agent_message.is_audio,
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
                is_audio=msg.is_audio,
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
            agent_session = await self.session_service.get_session(
                app_name="SpeakingPractice",
                user_id=str(user_id),
                session_id=str(session_id)
            )
            
            state = agent_session.state or {}
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
            query = self._build_agent_query(
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
                agent_session_after = await self.session_service.get_session(
                    app_name="SpeakingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id)
                )
                
                state_after = agent_session_after.state or {}
                
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
            
            # Get final evaluation from speaking_practice (will call final_evaluator tool)
            # Using trigger phrase that matches speaking_practice instruction
            evaluation_response = await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=self._build_agent_query(
                    source="final_evaluation_button",
                    message="đánh giá cuối"
                ),
                logger=logger
            )
            
            # Get structured output from agent session state
            try:
                # Get the structured output from the agent's session state
                agent_session = await self.session_service.get_session(
                    app_name="SpeakingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id)
                )
                
                # Extract structured evaluation from session state
                final_eval = agent_session.state.get("final_evaluation", {})
                
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