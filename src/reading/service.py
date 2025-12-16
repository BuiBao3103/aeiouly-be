from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import time
import json
import logging
from datetime import datetime, timezone

from src.constants.cefr import CEFRLevel
from src.reading.models import ReadingSession, ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel
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
from src.config import get_database_url
from src.utils.agent_utils import call_agent_with_logging

# Constants
NO_AI_RESPONSE_ERROR = "No response from AI agent"
DEFAULT_FEEDBACK = "Đánh giá tự động dựa trên nội dung tóm tắt."
APP_NAME = "ReadingPractice"

class ReadingService:
    def __init__(self):
        # Use application DB config so ADK session tables live in the same PostgreSQL database
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        self.logger = logging.getLogger(__name__)
        
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
    
    def _build_agent_query(self, source: str, message: str) -> str:
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
    
    async def create_reading_session(self, user_id: int, session_data: ReadingSessionCreate, db: Session) -> ReadingSessionResponse:
        """Create a new reading session"""
        try:
            is_custom = bool(session_data.custom_text)
            content = session_data.custom_text or ""
            requested_level = session_data.level or ReadingLevel.B1
            requested_genre = session_data.genre or ReadingGenre.ARTICLE
            topic = session_data.topic or "General"
            word_count = self._count_words(content) if content else 0
            
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
            db.commit()
            db.refresh(db_session)
            
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
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
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
                        query=self._build_agent_query(source="analyze_text", message=message),
                        logger=self.logger,
                        agent_name=text_analysis_agent.name
                    )
                    agent_session = await self.session_service.get_session(
                        app_name="ReadingPractice",
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
                        query=self._build_agent_query(source="generate_text", message=message),
                        logger=self.logger,
                        agent_name=text_generation_agent.name
                    )
                    agent_session = await self.session_service.get_session(
                        app_name="ReadingPractice",
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
            db.commit()
            
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
            db.rollback()
            raise TextGenerationFailedException(f"Failed to create reading session: {str(e)}")
    
    def get_reading_sessions(self, user_id: int, filters: ReadingSessionFilter, pagination: PaginationParams, db: Session) -> PaginatedResponse[ReadingSessionSummary]:
        """Get paginated list of reading sessions"""
        query = db.query(ReadingSession).filter(ReadingSession.user_id == user_id)
        
        # Apply filters
        if filters.level:
            query = query.filter(ReadingSession.level == filters.level.value)
        if filters.genre:
            query = query.filter(ReadingSession.genre == filters.genre.value)
        if filters.is_custom is not None:
            query = query.filter(ReadingSession.is_custom == filters.is_custom)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        sessions = query.order_by(desc(ReadingSession.created_at)).offset(offset).limit(pagination.size).all()
        
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
    
    def get_reading_session_detail(self, session_id: int, user_id: int, db: Session) -> ReadingSessionDetail:
        """Get reading session detail"""
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
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
    
    async def evaluate_answer(self, session_id: int, user_id: int, answer_data: AnswerSubmission, db: Session) -> AnswerFeedback:
        """Evaluate discussion answer (Vietnamese or English)"""
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name="ReadingPractice",
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
                    app_name="ReadingPractice",
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
    
    async def generate_quiz(self, session_id: int, user_id: int, quiz_request: QuizGenerationRequest, db: Session) -> QuizResponse:
        """Generate quiz from reading session"""
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name="ReadingPractice",
                user_id=str(user_id),
                session_id=agent_session_id
            )
        except Exception:
            agent_session = None
        
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
                    app_name="ReadingPractice",
                    user_id=str(user_id),
                    session_id=agent_session_id
                )
                quiz_payload = (
                    agent_session.state.get("quiz_result", {})
                    if agent_session and agent_session.state
                    else {}
                )
            except Exception:
                self.logger.warning(
                    "Unable to fetch quiz_result for session %s",
                    agent_session_id,
                    exc_info=True
                )
                quiz_payload = {}
            
            questions = quiz_payload.get("questions", []) if isinstance(quiz_payload, dict) else []
            return QuizResponse(questions=questions)
            
        except Exception as e:
            raise QuizGenerationFailedException(f"Failed to generate quiz: {str(e)}")
    
    def delete_reading_session(self, session_id: int, user_id: int, db: Session) -> bool:
        """Soft delete a reading session"""
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id,
                ReadingSession.deleted_at.is_(None)
            )
        ).first()
        
        if not session:
            return False
        
        # Soft delete by setting deleted_at timestamp
        session.deleted_at = datetime.now(timezone.utc)
        db.commit()
        
        return True
    
    # Private helper methods
    async def generate_discussion(self, session_id: int, user_id: int, discussion_request: DiscussionGenerationRequest, db: Session) -> DiscussionResponse:
        """Generate discussion questions from reading session"""
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        agent_session_id = str(session_id)
        try:
            agent_session = await self.session_service.get_session(
                app_name="ReadingPractice",
                user_id=str(user_id),
                session_id=agent_session_id
            )
        except Exception:
            agent_session = None
        
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
                    app_name="ReadingPractice",
                    user_id=str(user_id),
                    session_id=agent_session_id
                )
                discussion_payload = (
                    agent_session.state.get("discussion_result", {})
                    if agent_session and agent_session.state
                    else {}
                )
            except Exception:
                self.logger.warning(
                    "Unable to fetch discussion_result for session %s",
                    agent_session_id,
                    exc_info=True
                )
                discussion_payload = {}
            
            questions = discussion_payload.get("questions", []) if isinstance(discussion_payload, dict) else []
            return DiscussionResponse(questions=questions)
            
        except Exception as e:
            raise Exception(f"Failed to generate discussion: {str(e)}")
    
    def _count_words(self, text: str) -> int:
        """Count words in text"""
        import re
        # Remove extra whitespace and split by whitespace
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
    
    def _get_default_word_count(self, level: ReadingLevel) -> int:
        """Get default word count based on level"""
        # Simple default word counts
        word_counts = {
            ReadingLevel.A1: 150,
            ReadingLevel.A2: 250,
            ReadingLevel.B1: 400,
            ReadingLevel.B2: 500,
            ReadingLevel.C1: 650,
            ReadingLevel.C2: 800
        }
        return word_counts.get(level, 400)
