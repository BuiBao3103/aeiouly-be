"""Service layer for Chatbot module"""
from typing import Optional
import logging
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import settings, get_database_url, get_sync_database_url
from src.utils.agent_utils import call_agent_with_logging, build_agent_query
from src.chatbot.exceptions import ChatbotAgentException, ChatbotSessionNotFoundException
from src.chatbot.agents.chat_agent.agent import chat_agent
from src.database import AsyncSessionLocal
from src.speaking.models import SpeakingSession
from src.writing.models import WritingSession
from src.reading.models import ReadingSession
from src.listening.models import ListeningSession, ListenLesson
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

# Logger for chatbot service
logger = logging.getLogger(__name__)

# Constants
APP_NAME = "Chatbot"
MAX_CONVERSATION_HISTORY_MESSAGES = 20  # Limit conversation history to last 20 messages


class ChatbotService:
    """Service for chatbot interactions"""
    
    def __init__(self):
        """Initialize ChatbotService with ADK runner and DB-backed session service"""
        try:
            # Use DatabaseSessionService so chatbot conversations are persisted in PostgreSQL
            # DatabaseSessionService needs sync URL, not async
            self.session_service = DatabaseSessionService(db_url=get_sync_database_url())
            
            # Create runner for chatbot agent
            self.runner = Runner(
                agent=chat_agent,
                app_name=APP_NAME,
                session_service=self.session_service,
            )
            
            logger.info("ChatbotService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChatbotService: {e}", exc_info=True)
            raise ChatbotAgentException("Không thể khởi tạo chatbot service")
    
    async def send_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Send a message to the chatbot and get response.
        
        Conversation history is automatically managed in session state.
        Frontend does NOT need to send conversation history; it is stored and updated
        internally based on conversation_id and callbacks.
        
        Args:
            user_id: User identifier
            message: User's message
            conversation_id: Optional conversation/session id (do người dùng cung cấp)
            
        Returns:
            Tuple (response text, conversation_id)
        """
        try:
            from src.utils.agent_utils import update_session_state, get_agent_state, extract_agent_response_text
            
            # Determine session_id
            if conversation_id:
                # User provided an explicit conversation/session id → require it to exist
                session_id = str(conversation_id)
                existing_session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )
                if not existing_session:
                    # If the specified session does not exist → 404
                    raise ChatbotSessionNotFoundException(
                        detail=f"Không tìm thấy phiên chat với id '{conversation_id}'"
                    )
                # Ensure user_id present in state
                existing_state = existing_session.state or {}
                if "user_id" not in existing_state:
                    await update_session_state(
                        session_service=self.session_service,
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                        state_delta={"user_id": user_id},
                        author="system",
                        invocation_id_prefix="set_user_id",
                        logger=logger,
                    )
            else:
                # No conversation_id provided → create a new session with generated id
                import time

                generated_id = f"{user_id}-{int(time.time() * 1000)}"
                session_id = generated_id
                await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    state={
                        "conversation_history": [],
                        "user_id": user_id,
                    },
                )
            
            # Build query for agent
            query = build_agent_query(
                source="user_message",
                message=message,
            )
            
            # Call agent with logging and get final text directly
            response_text = await call_agent_with_logging(
                runner=self.runner,
                user_id=user_id,
                session_id=str(session_id),
                query=query,
                logger=logger,
                agent_name=chat_agent.name,
            )
            
            if not response_text:
                raise ChatbotAgentException("Chatbot không tạo được phản hồi")
            
            # Trả về cả câu trả lời và conversation_id để frontend dùng cho lần sau
            return response_text, str(session_id)
            
        except ChatbotSessionNotFoundException:
            # Giữ nguyên 404, để router trả về đúng cho client
            raise
        except ChatbotAgentException:
            # Các lỗi do agent (LLM, tool, ...) sẽ giữ status 502
            raise
        except Exception as e:
            logger.error(f"Error sending message to chatbot: {type(e).__name__}: {str(e)}", exc_info=True)
            raise ChatbotAgentException(f"Lỗi khi xử lý tin nhắn: {str(e)}")


    @staticmethod
    async def get_user_learning_sessions_data(user_id: int, limit: int = 20) -> dict:
        """
        Lấy danh sách phiên học (speaking, reading, writing, listening) của người dùng.

        Args:
            user_id: User id (int)
            limit: Số lượng tối đa mỗi loại phiên

        Returns:
            dict chứa danh sách phiên học theo từng loại
        """
        async with AsyncSessionLocal() as db:
            try:
                speaking_list = await ChatbotService._get_speaking_sessions(db, user_id, limit)
                writing_list = await ChatbotService._get_writing_sessions(db, user_id, limit)
                reading_list = await ChatbotService._get_reading_sessions(db, user_id, limit)
                listening_list = await ChatbotService._get_listening_sessions(db, user_id, limit)

                return {
                    "speaking_sessions": speaking_list,
                    "reading_sessions": reading_list,
                    "writing_sessions": writing_list,
                    "listening_sessions": listening_list,
                    "total_speaking": len(speaking_list),
                    "total_reading": len(reading_list),
                    "total_writing": len(writing_list),
                    "total_listening": len(listening_list),
                    "total_sessions": len(speaking_list) + len(reading_list) + len(writing_list) + len(listening_list),
                }
            except Exception as e:
                logger.error(f"Error getting user learning sessions: {e}", exc_info=True)
                return {
                    "error": f"Lỗi khi lấy danh sách phiên học: {str(e)}",
                    "speaking_sessions": [],
                    "reading_sessions": [],
                    "writing_sessions": [],
                    "listening_sessions": [],
                }

    @staticmethod
    async def _get_speaking_sessions(db: AsyncSession, user_id: int, limit: int) -> list[dict]:
        result = await db.execute(
            select(SpeakingSession)
            .where(SpeakingSession.user_id == user_id)
            .order_by(desc(SpeakingSession.created_at))
            .limit(limit)
        )
        speaking_sessions = result.scalars().all()
        return [
            {
                "id": session.id,
                "type": "speaking",
                "my_character": session.my_character,
                "ai_character": session.ai_character,
                "scenario": session.scenario,
                "level": session.level,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }
            for session in speaking_sessions
        ]

    @staticmethod
    async def _get_writing_sessions(db: AsyncSession, user_id: int, limit: int) -> list[dict]:
        result = await db.execute(
            select(WritingSession)
            .where(WritingSession.user_id == user_id)
            .order_by(desc(WritingSession.created_at))
            .limit(limit)
        )
        writing_sessions = result.scalars().all()
        return [
            {
                "id": session.id,
                "type": "writing",
                "topic": session.topic,
                "level": session.level.value if hasattr(session.level, "value") else str(session.level),
                "total_sentences": session.total_sentences,
                "current_sentence_index": session.current_sentence_index,
                "status": session.status.value if hasattr(session.status, "value") else str(session.status),
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }
            for session in writing_sessions
        ]

    @staticmethod
    async def _get_reading_sessions(db: AsyncSession, user_id: int, limit: int) -> list[dict]:
        result = await db.execute(
            select(ReadingSession)
            .where(ReadingSession.user_id == user_id)
            .order_by(desc(ReadingSession.created_at))
            .limit(limit)
        )
        reading_sessions = result.scalars().all()
        return [
            {
                "id": session.id,
                "type": "reading",
                "topic": session.topic,
                "level": session.level,
                "genre": session.genre,
                "word_count": session.word_count,
                "is_custom": session.is_custom,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }
            for session in reading_sessions
        ]

    @staticmethod
    async def _get_listening_sessions(db: AsyncSession, user_id: int, limit: int) -> list[dict]:
        result = await db.execute(
            select(ListeningSession)
            .where(ListeningSession.user_id == user_id)
            .order_by(desc(ListeningSession.created_at))
            .limit(limit)
        )
        listening_sessions = result.scalars().all()
        result: list[dict] = []
        for session in listening_sessions:
            lesson: ListenLesson | None = session.lesson  # type: ignore[attr-defined]
            result.append(
                {
                    "id": session.id,
                    "type": "listening",
                    "lesson_id": session.lesson_id,
                    "lesson_title": getattr(lesson, "title", None),
                    "level": getattr(lesson, "level", None),
                    "status": session.status,
                    "attempts": session.attempts,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                }
            )
        return result

