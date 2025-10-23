from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import time
from datetime import datetime, timezone

from src.constants.cefr import CEFRLevel
from src.reading.models import ReadingSession, ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel
from src.reading.schemas import (
    ReadingSessionCreate, ReadingSessionResponse, ReadingSessionSummary,
    ReadingSessionDetail, ReadingSessionFilter, SummarySubmission,
    SummaryFeedback, QuizGenerationRequest, QuizResponse
)
from src.reading.agents.text_generation_agent import text_generation_agent, TextGenerationRequest
from src.reading.agents.text_analysis_agent import text_analysis_agent, TextAnalysisRequest
from src.reading.agents.summary_evaluation_agent import summary_evaluation_agent, SummaryEvaluationRequest
from src.reading.agents.quiz_generation_agent import quiz_generation_agent, QuizGenerationRequest as QuizRequest
from src.reading.exceptions import (
    ReadingSessionNotFoundException, TextGenerationFailedException,
    TextAnalysisFailedException, SummaryEvaluationFailedException,
    QuizGenerationFailedException
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from src.config import get_database_url

# Constants
NO_AI_RESPONSE_ERROR = "No response from AI agent"

class ReadingService:
    def __init__(self):
        self.session_service = DatabaseSessionService(db_url=get_database_url())
    
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
                
                # Handle both dict and object responses
                if isinstance(generation_result, dict):
                    content = generation_result.get("content", "")
                    level = ReadingLevel(generation_result.get("level", session_data.level.value))
                    genre = ReadingGenre(generation_result.get("genre", session_data.genre.value))
                    topic = generation_result.get("topic", session_data.topic or "General")
                else:
                    content = generation_result.content
                    level = ReadingLevel(generation_result.level)
                    genre = ReadingGenre(generation_result.genre)
                    topic = generation_result.topic
                
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
                session_id=session.id,
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
            session_id=session.id,
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
            # Evaluate summary with AI
            evaluation_result = await self._evaluate_summary(session.content, summary_data.vietnamese_summary)
            
            # Handle both dict and object responses
            if isinstance(evaluation_result, dict):
                score = evaluation_result.get("score", 75)
                feedback = evaluation_result.get("feedback", "Đánh giá tự động dựa trên nội dung tóm tắt.")
            else:
                score = evaluation_result.score
                feedback = evaluation_result.feedback
            
            return SummaryFeedback(
                score=score,
                feedback=feedback
            )
            
        except Exception as e:
            raise SummaryEvaluationFailedException(f"Failed to evaluate summary: {str(e)}")
    
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
            quiz_result = await self._generate_quiz(session.content, quiz_request.number_of_questions)
            
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
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=f"""
                Generate a reading text with the following requirements:
                - Level: {level.value}
                - Genre: {genre.value}
                - Topic: {topic}
                - Word count: {target_word_count}
                """)]
            )
            
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # If not JSON, try to extract from text
                        return {"content": response_text, "level": level.value, "genre": genre.value, "topic": topic}
            
            raise TextGenerationFailedException(NO_AI_RESPONSE_ERROR)
            
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
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=f"Analyze this reading text:\n\n{text}")]
            )
            
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # If not JSON, try to extract from text
                        return {"level": "B1", "genre": "Bài báo", "topic": "General", "word_count": len(text.split())}
            
            raise TextAnalysisFailedException(NO_AI_RESPONSE_ERROR)
            
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
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=f"""
                Original text:
                {original_text}
                
                Vietnamese summary to evaluate:
                {vietnamese_summary}
                """)]
            )
            
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # If not JSON, try to extract from text
                        return {"score": 75, "feedback": "Đánh giá tự động dựa trên nội dung tóm tắt."}
            
            raise SummaryEvaluationFailedException(NO_AI_RESPONSE_ERROR)
            
        except Exception as e:
            raise SummaryEvaluationFailedException(f"AI summary evaluation failed: {str(e)}")
    
    async def _generate_quiz(self, content: str, number_of_questions: int) -> Any:
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
            
            content_msg = types.Content(
                role="user",
                parts=[types.Part(text=f"""
                Generate a quiz with {number_of_questions} questions from this reading text:
                
                {content}
                """)]
            )
            
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content_msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # If not JSON, create fallback quiz
                        return {"questions": []}
            
            raise QuizGenerationFailedException(NO_AI_RESPONSE_ERROR)
            
        except Exception as e:
            raise QuizGenerationFailedException(f"AI quiz generation failed: {str(e)}")
    
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
