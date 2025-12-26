from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_, func
import time
import json
import logging
from datetime import datetime, timezone
from src.reading.models import ReadingSession, ReadingGenre, ReadingLevel

from src.reading.schemas import (
    ReadingSessionCreate, ReadingSessionResponse, ReadingSessionSummary,
    ReadingSessionDetail, ReadingSessionFilter, AnswerSubmission,
    AnswerFeedback, QuizGenerationRequest, QuizResponse,
    DiscussionGenerationRequest, DiscussionResponse
)
from src.reading.agents.text_generation_agent.agent import text_generation_agent
from src.reading.agents.text_analysis_agent.agent import text_analysis_agent
from src.reading.agents.quiz_generation_agent.agent import quiz_generation_agent
from src.reading.agents.discussion_generation_agent.agent import discussion_generation_agent
from src.reading.agents.analyze_discussion_answer_agent.agent import analyze_discussion_answer_agent
from src.reading.exceptions import (
    ReadingSessionNotFoundException, TextGenerationFailedException,
    TextAnalysisFailedException, QuizGenerationFailedException
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import get_database_url, get_sync_database_url
from src.utils.agent_utils import call_agent_with_logging
from src.constants.cefr import CEFRLevel
from src.users.service import UsersService # Import UsersService

NO_AI_RESPONSE_ERROR = "No response from AI agent"
DEFAULT_FEEDBACK = "Đánh giá tự động dựa trên nội dung tóm tắt."
APP_NAME = "ReadingPractice"

class ReadingService:
    def __init__(self):
        # Use application DB config so ADK session tables live in the same PostgreSQL database
        # DatabaseSessionService needs sync URL, not async
        self.session_service = DatabaseSessionService(db_url=get_sync_database_url())
        self.logger = logging.getLogger(__name__)
        self.users_service = UsersService() # Initialize UsersService

        self.text_generation_runner = Runner(
            agent=text_generation_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.text_analysis_runner = Runner(
            agent=text_analysis_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.quiz_generation_runner = Runner(
            agent=quiz_generation_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.discussion_generation_runner = Runner(
            agent=discussion_generation_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.analyze_discussion_answer_runner = Runner(
            agent=analyze_discussion_answer_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
    
    def _build_agent_query(self, source: str, message: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """
        Build standardized query string for reading_practice with source metadata.
        
        Args:
            source: Origin of the action (e.g., generate_text, analyze_text, generate_quiz, etc.)
            message: The natural language message or parameters
        
        Returns:
            Formatted string consumed by reading_practice:
                SOURCE:<source>\nMESSAGE:<message>
        """
        return f"SOURCE:{source}\nMESSAGE:{message}"
    
    async def create_reading_session(self, user_id: int, session_data: ReadingSessionCreate, db: AsyncSession) -> ReadingSessionResponse:
        """
        Creates a new reading session for a user.

        This method handles both custom text input and AI-generated text based on session parameters.
        It initializes an ADK agent session, generates or analyzes text, and persists the session to the database.

        Args:
            user_id: The ID of the user creating the session.
            session_data: The data for creating the reading session, including custom text or generation parameters.
            db: The asynchronous database session.

        Returns:
            A `ReadingSessionResponse` object representing the newly created reading session.

        Raises:
            TextAnalysisFailedException: If AI text analysis fails for custom content.
            TextGenerationFailedException: If AI text generation fails for non-custom content.
        """
        try:
            is_custom = bool(session_data.custom_text)
            content = session_data.custom_text or ""
            requested_level = session_data.level or ReadingLevel.B1
            requested_genre = session_data.genre or ReadingGenre.ARTICLE
            topic = session_data.topic or "General"
            word_count = self._count_words(content) if content else 0
            
            # NOTE:
            # We create the DB session row inside the same transaction as the AI generation.
            # Use flush() instead of commit() so that if the agent fails, a rollback will
            # completely remove this row (no \"ghost\" sessions with word_count=0).
            db_session = ReadingSession(
                user_id=user_id,
                level=requested_level.value,
                genre=requested_genre.value,
                topic=topic,
                content=content,
                word_count=word_count,
                is_custom=is_custom,
            )
            
            db.add(db_session)
            # Flush to get primary key (id) without committing the transaction yet
            await db.flush()
            await db.refresh(db_session)
            
            agent_session_id = str(db_session.id)
            base_state = {
                "session_id": db_session.id,
                "content": content,
                "level": requested_level.value,
                "genre": requested_genre.value,
                "topic": topic,
                "word_count": word_count,
                "is_custom": is_custom,
                "target_word_count": session_data.word_count or self._get_default_word_count(requested_level),
            }
            
            user_evaluation_history = await self.users_service.get_user_evaluation_history(user_id, db)
            
            # Add user_evaluation_history to base_state
            base_state["user_evaluation_history"] = user_evaluation_history

            try:
                await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=agent_session_id,
                    state=base_state
                )
            except Exception:
                self.logger.warning(
                    "Unable to initialize reading agent session %s",
                    agent_session_id,
                    exc_info=True
                )
            
            if is_custom:
                try:
                    message = "Analyze the reading text available in state (key: content) and update analysis_result."
                    await call_agent_with_logging(
                        runner=self.text_analysis_runner,
                        user_id=str(user_id),
                        session_id=agent_session_id,
                        query=self._build_agent_query(source="analyze_text", message=message, payload={"content": content}),
                        logger=self.logger,
                        agent_name=text_analysis_agent.name
                    )
                    agent_session = await self.session_service.get_session(
                        app_name=APP_NAME,
                        user_id=str(user_id),
                        session_id=agent_session_id
                    )
                    analysis_result = (
                        agent_session.state.get("analysis_result", {})
                        if agent_session and agent_session.state
                        else {}
                    )
                except Exception:
                    self.logger.warning(
                        "Unable to fetch analysis_result for session %s",
                        agent_session_id,
                        exc_info=True
                    )
                    analysis_result = {}
                if not analysis_result:
                    raise TextAnalysisFailedException("AI text analysis returned no data.")
                
                level = analysis_result.get("level", requested_level.value)
                genre = analysis_result.get("genre", requested_genre.value)
                topic = analysis_result.get("topic", topic)
                word_count = self._count_words(content)
            else:
                try:
                    message = "Generate the reading text using the parameters stored in state."
                    await call_agent_with_logging(
                        runner=self.text_generation_runner,
                        user_id=str(user_id),
                        session_id=agent_session_id,
                        query=self._build_agent_query(source="generate_text", message=message, payload=base_state),
                        logger=self.logger,
                        agent_name=text_generation_agent.name
                    )
                    agent_session = await self.session_service.get_session(
                        app_name=APP_NAME,
                        user_id=str(user_id),
                        session_id=agent_session_id
                    )
                    generation_result = (
                        agent_session.state.get("text_generation_result", {})
                        if agent_session and agent_session.state
                        else {}
                    )
                except Exception:
                    self.logger.warning(
                        "Unable to fetch text_generation_result for session %s",
                        agent_session_id,
                        exc_info=True
                    )
                    generation_result = {}
                
                content = generation_result.get("content", "") if isinstance(generation_result, dict) else ""
                if not content:
                    raise TextGenerationFailedException("AI text generation returned no content.")
                
                level = requested_level.value
                genre = requested_genre.value
                topic = session_data.topic or "General"
                word_count = self._count_words(content)
            
            db_session.content = content
            db_session.level = level
            db_session.genre = genre
            db_session.topic = topic
            db_session.word_count = word_count
            db_session.is_custom = is_custom

            # Only commit AFTER AI generation / analysis has succeeded and
            # we have valid content + word_count. This ensures we never persist
            # a reading session with word_count=0 due to agent errors.
            await db.commit()
            
            return ReadingSessionResponse(
                id=db_session.id,
                content=db_session.content,
                word_count=db_session.word_count,
                level=ReadingLevel(db_session.level),
                genre=ReadingGenre(db_session.genre),
                topic=db_session.topic,
                is_custom=db_session.is_custom
            )
            
        except Exception as e:
            await db.rollback()
            raise TextGenerationFailedException(f"Failed to create reading session: {str(e)}")
    
    async def get_reading_sessions(self, user_id: int, filters: ReadingSessionFilter, pagination: PaginationParams, db: AsyncSession) -> PaginatedResponse[ReadingSessionSummary]:
        """
        Retrieves a paginated list of reading sessions for a user, with optional filters.

        Args:
            user_id: The ID of the user.
            filters: `ReadingSessionFilter` object to apply filters by level, genre, or custom status.
            pagination: `PaginationParams` for controlling page number and size.
            db: The asynchronous database session.

        Returns:
            A `PaginatedResponse` containing a list of `ReadingSessionSummary` objects.
        """
        # Build query conditions
        conditions = [ReadingSession.user_id == user_id]
        if filters.level:
            conditions.append(ReadingSession.level == filters.level.value)
        if filters.genre:
            conditions.append(ReadingSession.genre == filters.genre.value)
        if filters.is_custom is not None:
            conditions.append(ReadingSession.is_custom == filters.is_custom)
        
        # Get total count
        count_result = await db.execute(
            select(func.count(ReadingSession.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        result = await db.execute(
            select(ReadingSession).where(and_(*conditions))
            .order_by(desc(ReadingSession.created_at))
            .offset(offset).limit(pagination.size)
        )
        sessions = result.scalars().all()
        
        # Convert to response
        session_summaries = [
            ReadingSessionSummary(
                id=session.id,
                level=ReadingLevel(session.level),
                genre=ReadingGenre(session.genre),
                topic=session.topic,
                word_count=session.word_count,
                is_custom=session.is_custom
            )
            for session in sessions
        ]
        
        return paginate(session_summaries, total, pagination.page, pagination.size)
    
    async def get_reading_session_detail(self, session_id: int, user_id: int, db: AsyncSession) -> ReadingSessionDetail:
        """
        Retrieves the detailed information of a specific reading session for a user.

        Args:
            session_id: The ID of the reading session.
            user_id: The ID of the user who owns the session.
            db: The asynchronous database session.

        Returns:
            A `ReadingSessionDetail` object containing the session's full content and metadata.

        Raises:
            ReadingSessionNotFoundException: If the session with the given ID and user ID is not found.
        """
        result = await db.execute(
            select(ReadingSession).where(
                and_(
                    ReadingSession.id == session_id,
                    ReadingSession.user_id == user_id
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        return ReadingSessionDetail(
            id=session.id,
            content=session.content,
            level=ReadingLevel(session.level),
            genre=ReadingGenre(session.genre),
            topic=session.topic,
            word_count=session.word_count,
            is_custom=session.is_custom
        )
    
    async def evaluate_answer(self, session_id: int, user_id: int, answer_data: AnswerSubmission, db: AsyncSession) -> AnswerFeedback:
        """
        Evaluates a user's answer to a discussion question for a given reading session.

        This method uses an ADK agent to analyze the answer based on the reading content and question.

        Args:
            session_id: The ID of the reading session.
            user_id: The ID of the user submitting the answer.
            answer_data: `AnswerSubmission` containing the question and the user's answer.
            db: The asynchronous database session.

        Returns:
            An `AnswerFeedback` object with a score and feedback for the submitted answer.

        Raises:
            ReadingSessionNotFoundException: If the session is not found for the user.
            Exception: If the reading agent session state is missing or evaluation fails.
        """
        result = await db.execute(
            select(ReadingSession).where(
                and_(
                    ReadingSession.id == session_id,
                    ReadingSession.user_id == user_id
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=agent_session_id
            )
        except Exception:
            agent_session = None
        
        if not agent_session or not agent_session.state:
            raise Exception("Reading agent session state is missing. Please recreate the reading session.")
        
        try:
            message = (
                "Evaluate the user's discussion answer. Use the reading content in state and the details below:\n\n"
                f"Question: {answer_data.question}\n"
                f"Answer: {answer_data.answer}"
            )
            query = self._build_agent_query(source="analyze_discussion_answer", message=message)
            
            await call_agent_with_logging(
                runner=self.analyze_discussion_answer_runner,
                user_id=str(user_id),
                session_id=agent_session_id,
                query=query,
                logger=self.logger,
                agent_name=analyze_discussion_answer_agent.name
            )
            
            try:
                agent_session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=agent_session_id
                )
                evaluation_result = (
                    agent_session.state.get("synthesis_result", {})
                    if agent_session and agent_session.state
                    else {}
                )
            except Exception:
                evaluation_result = {}
            
            if not evaluation_result:
                return AnswerFeedback(score=75, feedback=DEFAULT_FEEDBACK)
            
            score = evaluation_result.get("score", 75)
            feedback = evaluation_result.get("feedback", DEFAULT_FEEDBACK)
            
            return AnswerFeedback(score=score, feedback=feedback)
            
        except Exception as e:
            raise Exception(f"Failed to evaluate answer: {str(e)}")
    
    async def generate_quiz(self, session_id: int, user_id: int, quiz_request: QuizGenerationRequest, db: AsyncSession) -> QuizResponse:
        """Generates a quiz for a reading session using an ADK agent."""
        result = await db.execute(
            select(ReadingSession).where(
                and_(
                    ReadingSession.id == session_id,
                    ReadingSession.user_id == user_id
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=agent_session_id
            )
        except Exception as e:
            self.logger.warning(f"Error retrieving agent session for quiz generation: {e}", exc_info=True)
            raise Exception("Reading agent session state is missing. Please recreate the reading session.")
        
        if not agent_session or not agent_session.state:
            raise Exception("Reading agent session state is missing. Please recreate the reading session.")
        
        try:
            message = f"Generate a quiz with {quiz_request.number_of_questions} questions. Each question must be provided in BOTH English and Vietnamese."
            query = self._build_agent_query(source="generate_quiz", message=message)
            
            await call_agent_with_logging(
                runner=self.quiz_generation_runner,
                user_id=str(user_id),
                session_id=agent_session_id,
                query=query,
                logger=self.logger,
                agent_name=quiz_generation_agent.name
            )
            
            try:
                agent_session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=agent_session_id
                )
                quiz_payload = (
                    agent_session.state.get("quiz_result", {})
                    if agent_session and agent_session.state
                    else {}
                )
            except Exception as e:
                self.logger.warning(
                    f"Unable to fetch quiz_result for session {agent_session_id}: {e}",
                    exc_info=True
                )
                quiz_payload = {}
            
            questions = quiz_payload.get("questions", []) if isinstance(quiz_payload, dict) else []
            return QuizResponse(questions=questions)
            
        except Exception as e:
            raise QuizGenerationFailedException(f"Failed to generate quiz: {str(e)}")
    
    async def delete_reading_session(self, session_id: int, user_id: int, db: AsyncSession) -> bool:
        """
        Soft deletes a reading session by setting its `deleted_at` timestamp.

        Args:
            session_id: The ID of the reading session to delete.
            user_id: The ID of the user who owns the session.
            db: The asynchronous database session.

        Returns:
            `True` if the session was found and soft-deleted, `False` otherwise.
        """
        result = await db.execute(
            select(ReadingSession).where(
                and_(
                    ReadingSession.id == session_id,
                    ReadingSession.user_id == user_id,
                    ReadingSession.deleted_at.is_(None)
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        # Soft delete by setting deleted_at timestamp
        session.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        
        return True
    
    # Private helper methods
    async def generate_discussion(self, session_id: int, user_id: int, discussion_request: DiscussionGenerationRequest, db: AsyncSession) -> DiscussionResponse:
        """
        Generates discussion questions for a reading session using an ADK agent.

        Args:
            session_id: The ID of the reading session.
            user_id: The ID of the user who owns the session.
            discussion_request: `DiscussionGenerationRequest` specifying the number of questions.
            db: The asynchronous database session.

        Returns:
            A `DiscussionResponse` object containing the generated discussion questions.

        Raises:
            ReadingSessionNotFoundException: If the session is not found for the user.
            Exception: If the reading agent session state is missing or discussion generation fails.
        """
        result = await db.execute(
            select(ReadingSession).where(
                and_(
                    ReadingSession.id == session_id,
                    ReadingSession.user_id == user_id
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=agent_session_id
            )
        except Exception as e:
            self.logger.warning(f"Error retrieving agent session for discussion generation: {e}", exc_info=True)
            raise Exception("Reading agent session state is missing. Please recreate the reading session.")
        
        if not agent_session or not agent_session.state:
            raise Exception("Reading agent session state is missing. Please recreate the reading session.")
        
        try:
            message = f"Generate {discussion_request.number_of_questions} discussion questions. Provide each question in BOTH English and Vietnamese."
            query = self._build_agent_query(source="generate_discussion", message=message)
            
            await call_agent_with_logging(
                runner=self.discussion_generation_runner,
                user_id=str(user_id),
                session_id=agent_session_id,
                query=query,
                logger=self.logger,
                agent_name=discussion_generation_agent.name
            )
            
            try:
                agent_session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=agent_session_id
                )
                discussion_payload = (
                    agent_session.state.get("discussion_result", {})
                    if agent_session and agent_session.state
                    else {}
                )
            except Exception as e:
                self.logger.warning(
                    f"Unable to fetch discussion_result for session {agent_session_id}: {e}",
                    exc_info=True
                )
                discussion_payload = {}
            
            questions = discussion_payload.get("questions", []) if isinstance(discussion_payload, dict) else []
            return DiscussionResponse(questions=questions)
            
        except Exception as e:
            raise Exception(f"Failed to generate discussion: {str(e)}")
    
    def _count_words(self, text: str) -> int:
        """
        Counts the number of words in a given text string.
        
        Args:
            text: The input text string.
            
        Returns:
            The number of words in the text.
        """
        import re
        # Remove extra whitespace and split by whitespace
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
