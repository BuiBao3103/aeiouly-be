"""
Service layer for Listening module
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from src.listening.models import ListenLesson, Sentence, ListeningSession, SessionStatus, CEFRLevel
from src.listening.schemas import (
    LessonCreate, LessonUpload, LessonUpdate, LessonResponse, LessonDetailResponse,
    SessionCreate, SessionResponse, SessionDetailResponse,
    ProgressSubmit, ProgressStats, SessionCompleteResponse,
    LessonFilter
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from src.listening.utils import SRTParser, TextNormalizer, sanitize_subtitle_text, is_non_speech_subtitle
from src.listening.exceptions import (
    LessonNotFoundException, LessonCreationFailedException,
    SessionNotFoundException, SessionAlreadyCompletedException,
    InvalidSRTContentException, TranslationFailedException,
    DifficultyAnalysisFailedException, SessionCreationFailedException,
    ProgressUpdateFailedException, SessionCompletionFailedException
)
from src.listening.agents.translation_agent import translation_agent
from src.listening.agents.difficulty_agent import difficulty_agent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from src.config import get_database_url
import asyncio
from datetime import datetime, timezone

class ListeningService:
    def __init__(self):
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        # Configuration for batch processing
        self.MAX_SENTENCES_PER_BATCH = 50  # Giới hạn 5 câu/batch để có tối đa 10 batch
        self.MAX_RETRIES = 2  # Số lần retry khi có lỗi
    
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

    async def create_lesson(self, lesson_data: LessonUpload, db: Session) -> LessonResponse:
        """Create a new listening lesson with SRT parsing and translation"""
        try:
            # Parse SRT content
            srt_parser = SRTParser()
            subtitles = srt_parser.parse_srt_content(lesson_data.srt_content)
            
            if not subtitles:
                raise InvalidSRTContentException("Không thể parse được nội dung SRT")
            
            # Determine difficulty level using AI agent
            difficulty_level = await self._determine_difficulty(
                lesson_data.lesson_data.title, 
                lesson_data.srt_content
            )
            
            # Create lesson
            db_lesson = ListenLesson(
                title=lesson_data.lesson_data.title,
                youtube_url=lesson_data.lesson_data.youtube_url,
                level=difficulty_level,
                total_sentences=len(subtitles)
            )
            db.add(db_lesson)
            db.commit()
            db.refresh(db_lesson)
            
            # Normalize and filter subtitles
            original_count = len(subtitles)
            for s in subtitles:
                s.text = sanitize_subtitle_text(s.text)
            subtitles = [s for s in subtitles if not is_non_speech_subtitle(s.text)]
            filtered_count = len(subtitles)
            if filtered_count != original_count:
                print(f"Filtered non-speech subtitles: removed {original_count - filtered_count} items")

            # Translate sentences in batches to avoid token limits
            all_translations = []
            all_confidences = []  # Store confidences for each sentence
            
            # Split sentences into batches
            sentence_texts = [sub.text for sub in subtitles]
            for i in range(0, len(sentence_texts), self.MAX_SENTENCES_PER_BATCH):
                batch = sentence_texts[i:i + self.MAX_SENTENCES_PER_BATCH]
                batch_num = i//self.MAX_SENTENCES_PER_BATCH + 1
                print(f"Translating batch {batch_num}: {len(batch)} sentences")
                
                try:
                    # Pass difficulty level to translation
                    batch_translations, batch_confidences = await self._translate_all_sentences(batch, db_lesson.id, difficulty_level)
                    all_translations.extend(batch_translations)
                    # Store confidence for each sentence in this batch
                    all_confidences.extend(batch_confidences)
                    print(f"Batch {batch_num} completed. Total translations so far: {len(all_translations)}. Confidences: {batch_confidences}")
                except Exception as e:
                    print(f"Error in batch {batch_num}: {e}")
                    # Fallback: create placeholder translations for this batch
                    fallback_translations = [f"[Translation for: {sentence}]" for sentence in batch]
                    all_translations.extend(fallback_translations)
                    # Low confidence for fallback
                    fallback_confidences = [0.3] * len(fallback_translations)
                    all_confidences.extend(fallback_confidences)
                    print(f"Using fallback translations for batch {batch_num}")
            
            # Create sentences with translation
            sentences = []
            for i, subtitle in enumerate(subtitles):
                # Normalize text
                normalized_text = TextNormalizer.normalize(subtitle.text)
                # Alternatives removed
                
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
                    normalized_text=normalized_text,
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
    
    async def _determine_difficulty(self, title: str, srt_content: str) -> str:
        """Determine difficulty level using AI agent"""
        try:
            
            runner = Runner(
                agent=difficulty_agent,
                app_name="ListeningPractice",
                session_service=self.session_service
            )
            
            # Create session for difficulty analysis
            import time
            import uuid
            session_id = f"difficulty_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Check if session already exists, if so, use it
            try:
                await self.session_service.create_session(
                    app_name="ListeningPractice",
                    user_id="system",
                    session_id=session_id
                )
            except Exception:
                # Session already exists, that's fine
                pass
            
            # Create content for the agent
            content = types.Content(
                role="user", 
                parts=[types.Part(text=f"Analyze difficulty for lesson: '{title}'\n\nSRT Content:\n{srt_content[:2000]}...")]
            )
            
            # Run difficulty analysis
            difficulty_result = None
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    # The agent should return structured output
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        difficulty_result = json.loads(response_text)
                        break
                    except json.JSONDecodeError:
                        # If not JSON, try to extract level from text
                        if "level" in response_text.lower():
                            # Simple extraction - look for A1, A2, B1, etc.
                            import re
                            level_match = re.search(r'\b(A[12]|B[12]|C[12])\b', response_text)
                            if level_match:
                                difficulty_result = {"level": level_match.group(1)}
                                break
            
            if difficulty_result and isinstance(difficulty_result, dict):
                level = difficulty_result.get("level", "B1")  # Default to B1
                # Validate level
                if level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
                    return level
                else:
                    return "B1"  # Fallback
            else:
                return "B1"  # Fallback
                
        except Exception as e:
            print(f"Difficulty analysis error: {e}")
            raise DifficultyAnalysisFailedException(f"Lỗi khi phân tích độ khó: {str(e)}")
    
    async def _translate_all_sentences(self, english_sentences: List[str], lesson_id: int, difficulty_level: str = "intermediate") -> tuple[List[str], List[float]]:
        """Translate multiple English sentences to Vietnamese using AI agent in one call"""
        try:
            runner = Runner(
                agent=translation_agent,
                app_name="ListeningPractice",
                session_service=self.session_service
            )
            
            # Create session for translation
            import time
            import uuid
            session_id = f"batch_translation_{lesson_id}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Check if session already exists, if so, use it
            try:
                await self.session_service.create_session(
                    app_name="ListeningPractice",
                    user_id="system",
                    session_id=session_id
                )
            except Exception:
                # Session already exists, that's fine
                pass
            
            # Create content for batch translation with difficulty level
            sentences_text = "\n".join([f"{i+1}. {sentence}" for i, sentence in enumerate(english_sentences)])
            
            # Map difficulty levels to Vietnamese descriptions
            difficulty_descriptions = {
                "beginner": "trình độ cơ bản (A1-A2)",
                "intermediate": "trình độ trung cấp (B1-B2)", 
                "advanced": "trình độ nâng cao (C1-C2)"
            }
            
            level_desc = difficulty_descriptions.get(difficulty_level, "trình độ trung cấp")
            
            content = types.Content(
                role="user", 
                parts=[types.Part(text=f"""Dịch các câu tiếng Anh sau sang tiếng Việt với trình độ {level_desc}:

{sentences_text}""")]
            )
            
            # Run translation
            translation_result = None
            print(f"Starting batch translation for {len(english_sentences)} sentences")
            print(f"Sentences to translate: {english_sentences}")
            
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                print(f"Translation agent event: {event}")
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    print(f"Agent response text: {response_text}")
                    
                    try:
                        import json
                        translation_result = json.loads(response_text)
                        print(f"Parsed JSON result: {translation_result}")
                        # Extract translations and confidence from structured output
                        if isinstance(translation_result, dict):
                            # Preferred new format: { "items": [{"translation": str, "confidence_score": float}, ...] }
                            if "items" in translation_result and isinstance(translation_result["items"], list):
                                items = translation_result["items"]
                                translations = []
                                confidence_scores = []
                                for item in items:
                                    if isinstance(item, dict):
                                        translations.append(item.get("translation", ""))
                                        confidence_scores.append(float(item.get("confidence_score", 0.9)))
                                return translations[:len(english_sentences)], confidence_scores[:len(english_sentences)]
                            # Backward compatibility: translations + confidence_scores arrays
                            if "translations" in translation_result:
                                translations = translation_result["translations"]
                                confidence_scores = translation_result.get("confidence_scores", [0.9] * len(translations))
                                return translations[:len(english_sentences)], confidence_scores[:len(english_sentences)]
                        break
                    except json.JSONDecodeError:
                        print("Not JSON format, trying line-by-line parsing")
                        # If not JSON, try to parse line by line
                        lines = response_text.split('\n')
                        translations = []
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Remove numbering if present (1. 2. etc.)
                                if line[0].isdigit() and '. ' in line:
                                    line = line.split('. ', 1)[1]
                                # Remove any remaining numbering patterns
                                if line[0].isdigit() and ')' in line:
                                    line = line.split(')', 1)[1].strip()
                                # Skip empty lines or lines that are just numbers
                                if line and not line.isdigit():
                                    translations.append(line)
                        
                        print(f"Parsed {len(translations)} translations from {len(english_sentences)} sentences")
                        print(f"Translations: {translations}")
                        
                        if translations and len(translations) >= len(english_sentences):
                            confidence_scores = [0.8] * len(english_sentences)  # Default confidence for each sentence
                            return translations[:len(english_sentences)], confidence_scores
                        elif translations:
                            # If we have fewer translations than sentences, pad with placeholders
                            while len(translations) < len(english_sentences):
                                translations.append(f"[Translation for: {english_sentences[len(translations)]}]")
                            confidence_scores = [0.8] * len(english_sentences)  # Default confidence for each sentence
                            return translations[:len(english_sentences)], confidence_scores
                        break
            
            # Try to get structured output from session state
            try:
                agent_session = await self.session_service.get_session(
                    app_name="ListeningPractice",
                    user_id="system",
                    session_id=session_id
                )
                print(f"Agent session state: {agent_session.state}")
                
                # Look for structured output in session state
                if 'translation_result' in agent_session.state:
                    structured_result = agent_session.state['translation_result']
                    print(f"Found structured result: {structured_result}")
                    
                    if isinstance(structured_result, dict):
                        # Preferred new format via session state
                        if 'items' in structured_result and isinstance(structured_result['items'], list):
                            items = structured_result['items']
                            translations = [it.get('translation', '') for it in items if isinstance(it, dict)]
                            confidence_scores = [float(it.get('confidence_score', 0.9)) for it in items if isinstance(it, dict)]
                            print(f"Using structured translations (items): {translations}")
                            return translations[:len(english_sentences)], confidence_scores[:len(english_sentences)]
                        if 'translations' in structured_result:
                            translations = structured_result['translations']
                            print(f"Using structured translations: {translations}")
                            confidence_scores = [0.9] * len(english_sentences)  # High confidence for structured output
                            return translations[:len(english_sentences)], confidence_scores
                        elif 'translation' in structured_result:
                            # Single translation, create individual ones
                            single_translation = structured_result['translation']
                            translations = [f"{single_translation} (câu {i+1})" for i in range(len(english_sentences))]
                            print(f"Using single translation for all: {translations}")
                            confidence_scores = [0.7] * len(english_sentences)  # Medium confidence for single translation
                            return translations, confidence_scores
                
            except Exception as e:
                print(f"Error getting session state: {e}")
            
            if translation_result and isinstance(translation_result, dict):
                # Handle structured response
                if 'items' in translation_result and isinstance(translation_result['items'], list):
                    items = translation_result['items']
                    translations = [it.get('translation', '') for it in items if isinstance(it, dict)]
                    confidence_scores = [float(it.get('confidence_score', 0.9)) for it in items if isinstance(it, dict)]
                    return translations[:len(english_sentences)], confidence_scores[:len(english_sentences)]
                if 'translations' in translation_result:
                    confidence_scores = [0.9] * len(english_sentences)  # High confidence for structured output
                    return translation_result['translations'][:len(english_sentences)], confidence_scores
                elif 'translation' in translation_result:
                    # If only one translation, create individual translations
                    return [f"{translation_result['translation']} (câu {i+1})" for i in range(len(english_sentences))], 0.7  # Medium confidence for single translation
            
            if translation_result and isinstance(translation_result, dict):
                # Handle structured response
                if 'items' in translation_result and isinstance(translation_result['items'], list):
                    items = translation_result['items']
                    translations = [it.get('translation', '') for it in items if isinstance(it, dict)]
                    confidence_scores = [float(it.get('confidence_score', 0.9)) for it in items if isinstance(it, dict)]
                    return translations[:len(english_sentences)], confidence_scores[:len(english_sentences)]
                if 'translations' in translation_result:
                    confidence_scores = [0.9] * len(english_sentences)  # High confidence for structured output
                    return translation_result['translations'][:len(english_sentences)], confidence_scores
                elif 'translation' in translation_result:
                    # If only one translation, create individual translations
                    return [f"{translation_result['translation']} (câu {i+1})" for i in range(len(english_sentences))], 0.7  # Medium confidence for single translation
            
            # Fallback: return placeholder translations
            print(f"Using fallback translations for {len(english_sentences)} sentences")
            return [f"[Translation for: {sentence}]" for sentence in english_sentences], 0.5  # Low confidence for fallback
                
        except Exception as e:
            print(f"Batch translation error: {e}")
            # Return placeholder translations on error
            return [f"[Translation for: {sentence}]" for sentence in english_sentences], 0.3  # Very low confidence for error

    async def _translate_sentence(self, english_text: str, lesson_id: int) -> str:
        """Translate English sentence to Vietnamese using AI agent"""
        try:
            
            runner = Runner(
                agent=translation_agent,
                app_name="ListeningPractice",
                session_service=self.session_service
            )
            
            # Create session for translation
            import time
            import uuid
            session_id = f"translation_{lesson_id}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Check if session already exists, if so, use it
            try:
                await self.session_service.create_session(
                    app_name="ListeningPractice",
                    user_id="system",
                    session_id=session_id
                )
            except Exception:
                # Session already exists, that's fine
                pass
            
            # Create content for the agent
            content = types.Content(
                role="user", 
                parts=[types.Part(text=f"Translate this English sentence to Vietnamese: '{english_text}'")]
            )
            
            # Run translation
            translation_result = None
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    # The agent should return structured output
                    response_text = event.content.parts[0].text.strip()
                    try:
                        import json
                        translation_result = json.loads(response_text)
                        break
                    except json.JSONDecodeError:
                        # If not JSON, use the text directly as translation
                        translation_result = {"translation": response_text}
                        break
            
            if translation_result and isinstance(translation_result, dict):
                return translation_result.get("translation", english_text)
            else:
                return english_text  # Fallback
                
        except Exception as e:
            print(f"Translation error: {e}")
            raise TranslationFailedException(f"Lỗi khi dịch câu: {str(e)}")
    
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
        """Delete a listening lesson"""
        lesson = db.query(ListenLesson).filter(ListenLesson.id == lesson_id).first()
        if not lesson:
            raise LessonNotFoundException()
        
        # Delete related sentences first (cascade should handle this)
        db.delete(lesson)
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
                "normalized_text": sentence.normalized_text,
                # alternatives removed
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
        """Create a new listening session"""
        # Check if lesson exists
        lesson = db.query(ListenLesson).filter(ListenLesson.id == session_data.lesson_id).first()
        if not lesson:
            raise ValueError("Lesson not found")
        
        # Create session
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
                    "normalized_text": sentence.normalized_text,
                    # alternatives removed
                }
        
        return SessionDetailResponse(
            id=session.id,
            user_id=session.user_id,
            lesson_id=session.lesson_id,
            current_sentence_index=session.current_sentence_index,
            status=session.status,
            lesson=lesson_response,
            current_sentence=current_sentence,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def submit_progress(self, session_id: int, user_id: int, progress: ProgressSubmit, db: Session) -> ProgressStats:
        """Submit progress for current sentence and move to next"""
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
        
        # Update session progress
        session.current_sentence_index += 1
        
        # Check if completed
        lesson = db.query(ListenLesson).filter(ListenLesson.id == session.lesson_id).first()
        if session.current_sentence_index >= lesson.total_sentences:
            session.status = "completed"
        
        db.commit()
        
        # Calculate stats (simplified for now)
        total_sentences = lesson.total_sentences
        completed_sentences = session.current_sentence_index
        accuracy = 85.0  # Placeholder - would need to track actual results
        avg_time = 15.0  # Placeholder
        
        return ProgressStats(
            total_sentences=total_sentences,
            completed_sentences=completed_sentences,
            correct_answers=int(completed_sentences * accuracy / 100),
            total_attempts=completed_sentences,
            total_hints_used=0,  # Placeholder
            total_time_spent=completed_sentences * avg_time,
            accuracy=accuracy,
            average_time_per_sentence=avg_time
        )
