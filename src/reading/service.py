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
    ReadingSessionDetail, ReadingSessionFilter, SummarySubmission,
    SummaryFeedback, QuizGenerationRequest, QuizResponse,
    DiscussionGenerationRequest, DiscussionResponse
)
from src.reading.agents.text_generation_agent.agent import text_generation_agent
from src.reading.agents.text_analysis_agent.agent import text_analysis_agent
from src.reading.agents.subagents.summary_evaluator.agent import summary_evaluation_agent
from src.reading.agents.quiz_generation_agent.agent import quiz_generation_agent
from src.reading.agents.discussion_generation_agent.agent import discussion_generation_agent
from src.reading.agents.reading_coordinator.agent import reading_coordinator_agent
from src.reading.exceptions import (
    ReadingSessionNotFoundException, TextGenerationFailedException,
    TextAnalysisFailedException, SummaryEvaluationFailedException,
    QuizGenerationFailedException
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import get_database_url
from src.utils.agent_utils import call_agent_with_logging

# Constants
NO_AI_RESPONSE_ERROR = "No response from AI agent"
DEFAULT_FEEDBACK = "Đánh giá tự động dựa trên nội dung tóm tắt."

class ReadingService:
    def __init__(self):
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        self.logger = logging.getLogger(__name__)
    
    async def create_reading_session(self, user_id: int, session_data: ReadingSessionCreate, db: Session) -> ReadingSessionResponse:
        """Create a new reading session"""
        try:
            if session_data.custom_text:
                # Custom text - analyze with AI
                analysis_result = await self._analyze_custom_text(session_data.custom_text)
                
                content = session_data.custom_text
                
                # Handle both dict and object responses
                if isinstance(analysis_result, dict):
                    level = ReadingLevel(analysis_result.get("level", "B1"))
                    genre = ReadingGenre(analysis_result.get("genre", "Bài báo"))
                    topic = analysis_result.get("topic", "General")
                else:
                    level = ReadingLevel(analysis_result.level)
                    genre = ReadingGenre(analysis_result.genre)
                    topic = analysis_result.topic
                
                # Count words in service
                word_count = self._count_words(content)
                
                is_custom = True
                
            else:
                # AI generation - generate text
                if not session_data.level or not session_data.genre:
                    raise ValueError("Level and genre are required for AI generation")
                
                generation_result = await self._generate_reading_text(
                    level=session_data.level,
                    genre=session_data.genre,
                    topic=session_data.topic or "General",
                    word_count=session_data.word_count
                )
                
                # Agent now returns plain text content only
                content = generation_result or ""
                level = session_data.level
                genre = session_data.genre
                topic = session_data.topic or "General"
                
                word_count = self._count_words(content)
                is_custom = False
            
            # Create session in database
            db_session = ReadingSession(
                user_id=user_id,
                level=level.value,
                genre=genre.value,
                topic=topic,
                content=content,
                word_count=word_count,
                is_custom=is_custom,
            )
            
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
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
    
    async def evaluate_summary(self, session_id: int, user_id: int, summary_data: SummarySubmission, db: Session) -> SummaryFeedback:
        """Evaluate Vietnamese summary"""
        # Get session
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        try:
            # Evaluate summary with coordinator
            evaluation_result = await self._evaluate_summary_with_coordinator(session.content, summary_data.summary)
            
            # Handle both dict and object responses
            if isinstance(evaluation_result, dict):
                score = evaluation_result.get("score", 75)
                feedback = evaluation_result.get("feedback", DEFAULT_FEEDBACK)
            else:
                score = evaluation_result.score
                feedback = evaluation_result.feedback
            
            return SummaryFeedback(
                score=score,
                feedback=feedback
            )
            
        except Exception as e:
            raise SummaryEvaluationFailedException(f"Failed to evaluate summary: {str(e)}")
    
    async def _evaluate_summary_with_coordinator(self, original_text: str, summary_text: str) -> Any:
        """Evaluate summary using coordinator agent"""
        try:
            runner = Runner(
                agent=reading_coordinator_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"coordinator_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass  # Session might already exist
            
            query = f"""
            Evaluate this summary:
            
            Original text: {original_text}
            Summary: {summary_text}
            
            Please determine if the summary is in Vietnamese or English and provide appropriate evaluation.
            """
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                return {"score": 75, "feedback": DEFAULT_FEEDBACK}
            
            try:
                # Try to parse as JSON first
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to text response
                return {"score": 75, "feedback": response_text}
            
        except Exception as e:
            raise SummaryEvaluationFailedException(f"Coordinator evaluation failed: {str(e)}")
    
    async def generate_quiz(self, session_id: int, user_id: int, quiz_request: QuizGenerationRequest, db: Session) -> QuizResponse:
        """Generate quiz from reading session"""
        # Get session
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        try:
            # Generate quiz with AI
            quiz_result = await self._generate_quiz(session.content, quiz_request.number_of_questions, quiz_request.question_language)
            
            # Handle both dict and object responses
            if isinstance(quiz_result, dict):
                questions = quiz_result.get("questions", [])
            else:
                questions = quiz_result.questions
            
            return QuizResponse(
                questions=questions
            )
            
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
    async def _generate_reading_text(self, level: ReadingLevel, genre: ReadingGenre, topic: str, word_count: Optional[int] = None) -> Any:
        """Generate reading text using AI agent"""
        try:
            runner = Runner(
                agent=text_generation_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"text_gen_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass  # Session might already exist
            
            # Use provided word_count or default based on level
            target_word_count = word_count if word_count is not None else self._get_default_word_count(level)
            
            query = f"""
            Generate an English reading text with the following requirements:
            - Level: {level.value}
            - Genre: {genre.value}
            - Topic: {topic}
            - Target word count: {target_word_count} (approximate ±10%)
            - Use vocabulary and grammar appropriate to the level
            
            IMPORTANT:
            - Return ONLY the reading content as plain text.
            - Do NOT return JSON or any extra fields.
            - No title or metadata; content only.
            """
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                raise TextGenerationFailedException(NO_AI_RESPONSE_ERROR)
            
            # Return plain text directly
            return response_text
            
        except Exception as e:
            raise TextGenerationFailedException(f"AI text generation failed: {str(e)}")
    
    async def _analyze_custom_text(self, text: str) -> Any:
        """Analyze custom text using AI agent"""
        try:
            runner = Runner(
                agent=text_analysis_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"text_analysis_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass
            
            query = f"Analyze this reading text:\n\n{text}"
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                raise TextAnalysisFailedException(NO_AI_RESPONSE_ERROR)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, try to extract from text
                return {"level": "B1", "genre": "Bài báo", "topic": "General", "word_count": len(text.split())}
            
        except Exception as e:
            raise TextAnalysisFailedException(f"AI text analysis failed: {str(e)}")
    
    async def _evaluate_summary(self, original_text: str, vietnamese_summary: str) -> Any:
        """Evaluate summary using AI agent"""
        try:
            runner = Runner(
                agent=summary_evaluation_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"summary_eval_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass
            
            query = f"""
            Original text:
            {original_text}
            
            Vietnamese summary to evaluate:
            {vietnamese_summary}
            """
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                raise SummaryEvaluationFailedException(NO_AI_RESPONSE_ERROR)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, try to extract from text
                return {"score": 75, "feedback": "Đánh giá tự động dựa trên nội dung tóm tắt."}
            
        except Exception as e:
            raise SummaryEvaluationFailedException(f"AI summary evaluation failed: {str(e)}")
    
    async def _generate_quiz(self, content: str, number_of_questions: int, question_language: str = "vietnamese") -> Any:
        """Generate quiz using AI agent"""
        try:
            runner = Runner(
                agent=quiz_generation_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"quiz_gen_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass
            
            query = f"""
            Generate a quiz with {number_of_questions} questions from this reading text.
            Question language: {question_language}
            
            Reading text:
            {content}
            """
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                raise QuizGenerationFailedException(NO_AI_RESPONSE_ERROR)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, create fallback quiz
                return {"questions": []}
            
        except Exception as e:
            raise QuizGenerationFailedException(f"AI quiz generation failed: {str(e)}")
    
    async def generate_discussion(self, session_id: int, user_id: int, discussion_request: DiscussionGenerationRequest, db: Session) -> DiscussionResponse:
        """Generate discussion questions from reading session"""
        # Get session
        session = db.query(ReadingSession).filter(
            and_(
                ReadingSession.id == session_id,
                ReadingSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise ReadingSessionNotFoundException()
        
        try:
            # Generate discussion with AI
            discussion_result = await self._generate_discussion(session.content, discussion_request.number_of_questions)
            
            # Handle both dict and object responses
            if isinstance(discussion_result, dict):
                questions = discussion_result.get("questions", [])
            else:
                questions = discussion_result.questions
            
            return DiscussionResponse(
                questions=questions
            )
            
        except Exception as e:
            raise Exception(f"Failed to generate discussion: {str(e)}")
    
    async def _generate_discussion(self, content: str, number_of_questions: int) -> Any:
        """Generate discussion questions using AI agent"""
        try:
            runner = Runner(
                agent=discussion_generation_agent,
                app_name="ReadingPractice",
                session_service=self.session_service
            )
            session_id = f"discussion_gen_{int(time.time())}"
            
            try:
                await self.session_service.create_session(
                    app_name="ReadingPractice",
                    user_id="system",
                    session_id=session_id,
                    state={}
                )
            except Exception:
                pass
            
            query = f"""
            Generate {number_of_questions} discussion questions from this reading text.
            Each question must be provided in BOTH English and Vietnamese.
            
            Reading text:
            {content}
            """
            
            response_text = await call_agent_with_logging(
                runner=runner,
                user_id="system",
                session_id=session_id,
                query=query,
                logger=self.logger
            )
            
            if not response_text:
                raise Exception(NO_AI_RESPONSE_ERROR)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, create fallback
                return {"questions": []}
            
        except Exception as e:
            raise Exception(f"AI discussion generation failed: {str(e)}")
    
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
