"""
Service layer for Listening module
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from src.constants.cefr import CEFRLevel
from src.listening.models import ListenLesson, Sentence, ListeningSession, SessionStatus
from src.listening.schemas import (
    LessonCreate, LessonUpload, LessonUpdate, LessonResponse, LessonDetailResponse,
    SessionCreate, SessionResponse, SessionDetailResponse, SessionNextResponse,
    ProgressSubmit, ProgressStats, SessionCompleteResponse,
    LessonFilter, UserSessionResponse
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from src.listening.utils import SRTParser, sanitize_subtitle_text, is_non_speech_subtitle
from src.listening.exceptions import (
    LessonNotFoundException, LessonCreationFailedException,
    SessionNotFoundException, SessionAlreadyCompletedException,
    InvalidSRTContentException,
    DifficultyAnalysisFailedException, SessionCreationFailedException,
    ProgressUpdateFailedException, SessionCompletionFailedException
)
from src.listening.listening_lesson_agent.agent import listening_lesson_agent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import get_database_url
import asyncio
from datetime import datetime, timezone
import logging
import json
from src.utils.agent_utils import call_agent_with_logging

class ListeningService:
    def __init__(self):
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        self.runner = Runner(
            agent=listening_lesson_agent,
            app_name="ListeningLesson",
            session_service=self.session_service,
        )
        self.agent_user_id = "system"
        # Configuration for batch processing
        self.MAX_SENTENCES_PER_BATCH = 50  # Giới hạn 5 câu/batch để có tối đa 10 batch
        self.MAX_RETRIES = 2  # Số lần retry khi có lỗi
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def _is_non_speech_subtitle(text: str) -> bool:
        """Return True if the subtitle line is a non-speech sound/annotation like (Silence)."""
        if not text:
            return True
        stripped = text.strip()
        # Only consider short parenthesized annotations as non-speech
        if stripped.startswith("(") and stripped.endswith(")"):
            inner = stripped[1:-1].strip().lower()
            non_speech_tokens = {
                "silence",
                "laughter",
                "applause",
                "music",
                "crowd cheering",
                "cheering",
                "clapping",
                "gasps",
                "sighs",
                "chuckles",
            }
            return inner in non_speech_tokens
        return False

    def _build_agent_query(self, source: str, message: str) -> str:
        return f"SOURCE:{source}\nMESSAGE:{message}"

    async def _call_listening_agent(self, session_id: str, source: str, message: str) -> str:
        query = self._build_agent_query(source, message)
        return await call_agent_with_logging(
            runner=self.runner,
            user_id=self.agent_user_id,
            session_id=str(session_id),
            query=query,
            logger=self.logger,
            agent_name="listening_lesson"
        )

    async def _get_state_value(self, session_id: str, key: str):
        try:
            agent_session = await self.session_service.get_session(
                app_name="ListeningLesson",
                user_id=self.agent_user_id,
                session_id=str(session_id),
            )
            state = agent_session.state or {}
            return state.get(key)
        except Exception:
            self.logger.debug("Unable to fetch agent session state", exc_info=True)
            return None

    def _coerce_cefr_level(self, level_str: Optional[str]) -> CEFRLevel:
        try:
            if level_str:
                return CEFRLevel(level_str)
        except ValueError:
            pass
        return CEFRLevel.B1

    def _parse_translation_items(
        self, result: Optional[dict], english_sentences: List[str]
    ) -> Optional[tuple[List[str], List[float]]]:
        if not isinstance(result, dict):
            return None
        if "items" in result and isinstance(result["items"], list):
            translations = []
            confidences = []
            for item in result["items"]:
                if isinstance(item, dict):
                    translations.append(item.get("translation", ""))
                    confidences.append(float(item.get("confidence_score", 0.9)))
            return translations, confidences
        if "translations" in result:
            translations = result["translations"]
            confidences = result.get("confidence_scores", [0.9] * len(translations))
            return translations, confidences
        if "translation" in result:
            translations = [
                f"{result['translation']} (câu {i + 1})" for i in range(len(english_sentences))
            ]
            confidences = [0.7] * len(english_sentences)
            return translations, confidences
        return None

    def _parse_line_translations(self, response_text: str) -> Optional[tuple[List[str], List[float]]]:
        if not response_text:
            return None
        lines = [line.strip() for line in response_text.splitlines() if line.strip()]
        if not lines:
            return None
        translations = []
        for line in lines:
            if line[0].isdigit() and ". " in line:
                line = line.split(". ", 1)[1]
            translations.append(line)
        if not translations:
            return None
        confidences = [0.8] * len(translations)
        return translations, confidences

    async def create_lesson(self, lesson_data: LessonUpload, db: Session) -> LessonResponse:
        """Create a new listening lesson with SRT parsing and translation"""
        try:
            # Parse SRT content
            srt_parser = SRTParser()
            subtitles = srt_parser.parse_srt_content(lesson_data.srt_content)
            
            if not subtitles:
                raise InvalidSRTContentException("Không thể parse được nội dung SRT")
            
            # Create lesson early to obtain ID for agent session (temporary level)
            db_lesson = ListenLesson(
                title=lesson_data.lesson_data.title,
                youtube_url=lesson_data.lesson_data.youtube_url,
                level=CEFRLevel.B1.value,
                total_sentences=len(subtitles),
            )
            db.add(db_lesson)
            db.commit()
            db.refresh(db_lesson)

            lesson_session_id = str(db_lesson.id)
            # Create agent session for this lesson
            await self.session_service.create_session(
                app_name="ListeningLesson",
                user_id=self.agent_user_id,
                session_id=lesson_session_id,
                state={
                    "lesson_id": db_lesson.id,
                    "title": db_lesson.title,
                    "youtube_url": db_lesson.youtube_url,
                },
            )

            # Determine difficulty level using AI agent coordinator
            difficulty_level = await self._determine_difficulty(
                lesson_session_id,
                db_lesson.title,
                lesson_data.srt_content,
            )
            db_lesson.level = difficulty_level
            db.commit()
            
            # Normalize and filter subtitles
            original_count = len(subtitles)
            for s in subtitles:
                s.text = sanitize_subtitle_text(s.text)
            subtitles = [s for s in subtitles if not is_non_speech_subtitle(s.text)]
            filtered_count = len(subtitles)
            if filtered_count != original_count:
                self.logger.debug(f"Filtered non-speech subtitles: removed {original_count - filtered_count} items")

            # Translate sentences in batches to avoid token limits
            all_translations = []
            all_confidences = []  # Store confidences for each sentence
            
            # Split sentences into batches
            sentence_texts = [sub.text for sub in subtitles]
            for i in range(0, len(sentence_texts), self.MAX_SENTENCES_PER_BATCH):
                batch = sentence_texts[i:i + self.MAX_SENTENCES_PER_BATCH]
                batch_num = i//self.MAX_SENTENCES_PER_BATCH + 1
                self.logger.info(f"Translating batch {batch_num}: {len(batch)} sentences")
                
                try:
                    # Pass difficulty level to translation
                    batch_translations, batch_confidences = await self._translate_all_sentences(
                        lesson_id=db_lesson.id,
                        english_sentences=batch,
                        difficulty_level=difficulty_level,
                    )
                    all_translations.extend(batch_translations)
                    # Store confidence for each sentence in this batch
                    all_confidences.extend(batch_confidences)
                    self.logger.debug(f"Batch {batch_num} completed. Total translations so far: {len(all_translations)}. Confidences: {batch_confidences}")
                except Exception as e:
                    self.logger.warning(f"Error in batch {batch_num}: {e}")
                    # Fallback: create placeholder translations for this batch
                    fallback_translations = [f"[Translation for: {sentence}]" for sentence in batch]
                    all_translations.extend(fallback_translations)
                    # Low confidence for fallback
                    fallback_confidences = [0.3] * len(fallback_translations)
                    all_confidences.extend(fallback_confidences)
                    self.logger.warning(f"Using fallback translations for batch {batch_num}")
            
            # Create sentences with translation
            sentences = []
            for i, subtitle in enumerate(subtitles):
                # Get translation from batch result
                translation = all_translations[i] if i < len(all_translations) else f"[Translation for: {subtitle.text}]"
                
                # Get confidence for this sentence from accumulated confidences
                sentence_confidence = all_confidences[i] if i < len(all_confidences) else 0.8
                
                sentence = Sentence(
                    lesson_id=db_lesson.id,
                    index=i,
                    text=subtitle.text,
                    translation=translation,
                    start_time=subtitle.start_time,
                    end_time=subtitle.end_time,
                    confidence=sentence_confidence
                )
                sentences.append(sentence)
            
            db.add_all(sentences)
            db.commit()
            
            # Update lesson's updated_at timestamp
            db_lesson.updated_at = datetime.now(timezone.utc)
            # Also ensure total_sentences matches filtered list
            db_lesson.total_sentences = len(subtitles)
            db.commit()
            
            return LessonResponse(
                id=db_lesson.id,
                title=db_lesson.title,
                youtube_url=db_lesson.youtube_url,
                level=db_lesson.level,
                total_sentences=db_lesson.total_sentences,
                created_at=db_lesson.created_at,
                updated_at=db_lesson.updated_at
            )
            
        except Exception as e:
            db.rollback()
            raise LessonCreationFailedException(f"Lỗi khi tạo bài học: {str(e)}")
    
    async def _determine_difficulty(self, lesson_session_id: str, title: str, srt_content: str) -> str:
        """Determine difficulty level using the listening_lesson coordinator."""
        try:
            payload = (
                f"Lesson title: {title}\n\n"
                f"SRT Content Sample (trimmed to 2000 chars):\n{srt_content[:2000]}"
            )
            response_text = await self._call_listening_agent(
                session_id=lesson_session_id,
                source="determine_level",
                message=payload,
            )

            difficulty_result = await self._get_state_value(lesson_session_id, "determine_level_result")
            if not difficulty_result and response_text:
                try:
                    difficulty_result = json.loads(response_text)
                except Exception:
                    difficulty_result = None

            level_str = None
            if isinstance(difficulty_result, dict):
                level_str = difficulty_result.get("level")
            cefr_level = self._coerce_cefr_level(level_str)
            return cefr_level.value
        except Exception as e:
            self.logger.error(f"Difficulty analysis error: {e}")
            raise DifficultyAnalysisFailedException(f"Lỗi khi phân tích độ khó: {str(e)}")
    
    async def _translate_all_sentences(
        self,
        lesson_id: int,
        english_sentences: List[str],
        difficulty_level: str = "B1",
    ) -> tuple[List[str], List[float]]:
        """Translate multiple English sentences to Vietnamese using the coordinator agent."""
        try:
            sentences_text = "\n".join(
                [f"{i + 1}. {sentence}" for i, sentence in enumerate(english_sentences)]
            )
            payload = (
                f"Lesson ID: {lesson_id}\n"
                f"CEFR Level: {difficulty_level}\n"
                f"Dịch các câu tiếng Anh sau sang tiếng Việt:\n\n"
                f"{sentences_text}"
            )

            response_text = await self._call_listening_agent(
                session_id=str(lesson_id),
                source="translate_sentences",
                message=payload,
            )

            translation_result = await self._get_state_value(lesson_id, "translation_result")
            if not translation_result and response_text:
                try:
                    translation_result = json.loads(response_text)
                except Exception:
                    translation_result = None

            parsed = self._parse_translation_items(translation_result, english_sentences)
            if not parsed:
                parsed = self._parse_line_translations(response_text)

            if parsed:
                translations, confidence_scores = parsed
                # Ensure lengths
                if len(translations) < len(english_sentences):
                    translations += [
                        f"[Translation for: {sentence}]"
                        for sentence in english_sentences[len(translations) :]
                    ]
                if len(confidence_scores) < len(english_sentences):
                    confidence_scores += [0.6] * (len(english_sentences) - len(confidence_scores))
                return translations[: len(english_sentences)], confidence_scores[: len(english_sentences)]

            self.logger.warning(
                "Using fallback translations for %s sentences (no structured output)", len(english_sentences)
            )
            return (
                [f"[Translation for: {sentence}]" for sentence in english_sentences],
                [0.5] * len(english_sentences),
            )
        except Exception as e:
            self.logger.error(f"Batch translation error: {e}")
            return (
                [f"[Translation for: {sentence}]" for sentence in english_sentences],
                [0.3] * len(english_sentences),
            )
    
    def get_lessons(self, filters: LessonFilter, pagination: PaginationParams, db: Session) -> PaginatedResponse:
        """Get paginated list of lessons with filters"""
        query = db.query(ListenLesson)
        
        # Apply filters
        if filters.level:
            query = query.filter(ListenLesson.level == filters.level)
        
        # Tags filtering removed - tags column no longer exists
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    ListenLesson.title.ilike(search_term),
                    ListenLesson.youtube_url.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        lessons = query.order_by(desc(ListenLesson.created_at)).offset(offset).limit(pagination.size).all()
        
        # Convert to response
        lesson_responses = [
            LessonResponse(
                id=lesson.id,
                title=lesson.title,
                youtube_url=lesson.youtube_url,
                level=lesson.level,
                total_sentences=lesson.total_sentences,
                created_at=lesson.created_at,
                updated_at=lesson.updated_at
            )
            for lesson in lessons
        ]
        
        return paginate(lesson_responses, total, pagination.page, pagination.size)
    
    def update_lesson(self, lesson_id: int, lesson_data: LessonUpdate, db: Session) -> LessonResponse:
        """Update a listening lesson"""
        lesson = db.query(ListenLesson).filter(ListenLesson.id == lesson_id).first()
        if not lesson:
            raise LessonNotFoundException()
        
        # Update fields if provided
        if lesson_data.title is not None:
            lesson.title = lesson_data.title
        if lesson_data.youtube_url is not None:
            lesson.youtube_url = lesson_data.youtube_url
        if lesson_data.level is not None:
            lesson.level = lesson_data.level
        # Tags update removed - tags column no longer exists
        
        db.commit()
        db.refresh(lesson)
        
        return LessonResponse(
            id=lesson.id,
            title=lesson.title,
            youtube_url=lesson.youtube_url,
            level=lesson.level,
            total_sentences=lesson.total_sentences,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at
        )
    
    def delete_lesson(self, lesson_id: int, db: Session) -> bool:
        """Soft delete a listening lesson"""
        lesson = db.query(ListenLesson).filter(ListenLesson.id == lesson_id).first()
        if not lesson:
            raise LessonNotFoundException()
        
        # Soft delete the lesson (sets deleted_at timestamp)
        lesson.deleted_at = datetime.now(timezone.utc)
        db.commit()
        return True
    
    def get_lesson_detail(self, lesson_id: int, db: Session) -> Optional[LessonDetailResponse]:
        """Get lesson detail with all sentences"""
        lesson = db.query(ListenLesson).filter(ListenLesson.id == lesson_id).first()
        if not lesson:
            return None
        
        sentences = db.query(Sentence).filter(
            Sentence.lesson_id == lesson_id
        ).order_by(Sentence.index).all()
        
        sentence_responses = [
            {
                "id": sentence.id,
                "lesson_id": sentence.lesson_id,
                "index": sentence.index,
                "text": sentence.text,
                "translation": sentence.translation,
                "start_time": sentence.start_time,
                "end_time": sentence.end_time,
            }
            for sentence in sentences
        ]
        
        return LessonDetailResponse(
            id=lesson.id,
            title=lesson.title,
            youtube_url=lesson.youtube_url,
            level=lesson.level,
            total_sentences=lesson.total_sentences,
            sentences=sentence_responses,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at
        )
    
    def create_session(self, user_id: int, session_data: SessionCreate, db: Session) -> SessionResponse:
        """Create a new listening session or return existing active session"""
        # Check if lesson exists
        lesson = db.query(ListenLesson).filter(ListenLesson.id == session_data.lesson_id).first()
        if not lesson:
            raise ValueError("Lesson not found")
        
        # Check if user already has a session for this lesson (active or completed)
        existing_session = db.query(ListeningSession).filter(
            and_(
                ListeningSession.user_id == user_id,
                ListeningSession.lesson_id == session_data.lesson_id
            )
        ).first()
        
        if existing_session:
            if existing_session.status == "completed":
                # Reset completed session to active and start from beginning
                existing_session.status = "active"
                existing_session.current_sentence_index = 0
                existing_session.attempts += 1  # Increment attempts counter
                db.commit()
                db.refresh(existing_session)
                
                return SessionResponse(
                    id=existing_session.id,
                    user_id=existing_session.user_id,
                    lesson_id=existing_session.lesson_id,
                    current_sentence_index=existing_session.current_sentence_index,
                    status=existing_session.status,
                    attempts=existing_session.attempts,
                    created_at=existing_session.created_at,
                    updated_at=existing_session.updated_at
                )
            else:
                # Return existing active session
                return SessionResponse(
                    id=existing_session.id,
                    user_id=existing_session.user_id,
                    lesson_id=existing_session.lesson_id,
                    current_sentence_index=existing_session.current_sentence_index,
                    status=existing_session.status,
                    attempts=existing_session.attempts,
                    created_at=existing_session.created_at,
                    updated_at=existing_session.updated_at
                )
        
        # Create new session if none exists
        db_session = ListeningSession(
            user_id=user_id,
            lesson_id=session_data.lesson_id,
            current_sentence_index=0,
            status="active"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return SessionResponse(
            id=db_session.id,
            user_id=db_session.user_id,
            lesson_id=db_session.lesson_id,
            current_sentence_index=db_session.current_sentence_index,
            status=db_session.status,
            attempts=db_session.attempts,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at
        )
    
    def get_session(self, session_id: int, user_id: int, db: Session) -> SessionDetailResponse:
        """Get session detail with lesson info"""
        session = db.query(ListeningSession).filter(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise SessionNotFoundException()
        
        # Get lesson info
        lesson = db.query(ListenLesson).filter(ListenLesson.id == session.lesson_id).first()
        lesson_response = LessonResponse(
            id=lesson.id,
            title=lesson.title,
            youtube_url=lesson.youtube_url,
            level=lesson.level,
            total_sentences=lesson.total_sentences,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at
        )
        
        # Get current sentence
        current_sentence = None
        if session.current_sentence_index < lesson.total_sentences:
            sentence = db.query(Sentence).filter(
                and_(
                    Sentence.lesson_id == session.lesson_id,
                    Sentence.index == session.current_sentence_index
                )
            ).first()
            
            if sentence:
                current_sentence = {
                    "id": sentence.id,
                    "lesson_id": sentence.lesson_id,
                    "index": sentence.index,
                    "text": sentence.text,
                    "translation": sentence.translation,
                    "start_time": sentence.start_time,
                    "end_time": sentence.end_time,
                }
        
        return SessionDetailResponse(
            id=session.id,
            user_id=session.user_id,
            lesson_id=session.lesson_id,
            current_sentence_index=session.current_sentence_index,
            status=session.status,
            attempts=session.attempts,
            lesson=lesson_response,
            current_sentence=current_sentence,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def get_next_sentence(self, session_id: int, user_id: int, db: Session) -> SessionNextResponse:
        """Move to next sentence and return session detail with current sentence"""
        session = db.query(ListeningSession).filter(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        ).first()
        
        if not session:
            raise SessionNotFoundException()
        
        if session.status == "completed":
            raise SessionAlreadyCompletedException()
        
        # Increment current sentence index
        session.current_sentence_index += 1
        
        # Get lesson info
        lesson = db.query(ListenLesson).filter(ListenLesson.id == session.lesson_id).first()
        lesson_response = LessonResponse(
            id=lesson.id,
            title=lesson.title,
            youtube_url=lesson.youtube_url,
            level=lesson.level,
            total_sentences=lesson.total_sentences,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at
        )
        
        # Check if completed (reached end of lesson)
        if session.current_sentence_index >= lesson.total_sentences:
            session.status = "completed"
            current_sentence = None  # No more sentences
        else:
            # Get current sentence
            sentence = db.query(Sentence).filter(
                and_(
                    Sentence.lesson_id == session.lesson_id,
                    Sentence.index == session.current_sentence_index
                )
            ).first()
            
            current_sentence = {
                "id": sentence.id,
                "lesson_id": sentence.lesson_id,
                "index": sentence.index,
                "text": sentence.text,
                "translation": sentence.translation,
                "start_time": sentence.start_time,
                "end_time": sentence.end_time,
            } if sentence else None
        
        db.commit()
        
        return SessionNextResponse(
            id=session.id,
            user_id=session.user_id,
            lesson_id=session.lesson_id,
            current_sentence_index=session.current_sentence_index,
            status=session.status,
            attempts=session.attempts,
            lesson=lesson_response,
            current_sentence=current_sentence,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def get_user_sessions(self, user_id: int, pagination: PaginationParams, db: Session) -> PaginatedResponse[UserSessionResponse]:
        """Get all active sessions for a user with pagination"""
        # Base query for user's active sessions
        query = db.query(ListeningSession).filter(
            and_(
                ListeningSession.user_id == user_id,
            )
        )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        sessions = query.order_by(desc(ListeningSession.created_at)).offset(offset).limit(pagination.size).all()
        
        user_sessions = []
        for session in sessions:
            # Get lesson info
            lesson = db.query(ListenLesson).filter(ListenLesson.id == session.lesson_id).first()
            lesson_response = LessonResponse(
                id=lesson.id,
                title=lesson.title,
                youtube_url=lesson.youtube_url,
                level=lesson.level,
                total_sentences=lesson.total_sentences,
                created_at=lesson.created_at,
                updated_at=lesson.updated_at
            )
            
            user_sessions.append(UserSessionResponse(
                id=session.id,
                lesson_id=session.lesson_id,
                current_sentence_index=session.current_sentence_index,
                status=session.status,
                attempts=session.attempts,
                lesson=lesson_response,
                created_at=session.created_at,
                updated_at=session.updated_at
            ))
        
        return paginate(user_sessions, total, pagination.page, pagination.size)
