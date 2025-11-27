"""
Service layer for Writing Practice module
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.writing.models import WritingSession, WritingChatMessage, SessionStatus, CEFRLevel
from src.writing.schemas import (
    WritingSessionCreate, 
    WritingSessionResponse, 
    WritingSessionListResponse,
    ChatMessageCreate, 
    ChatMessageResponse, 
    HintResponse, 
    FinalEvaluationResponse
)
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from datetime import datetime
import json
from src.config import get_database_url
from src.database import SessionLocal
from src.utils.agent_utils import call_agent_with_logging
import logging
import random
from fastapi import HTTPException

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện viết"

# Logger for writing service
logger = logging.getLogger(__name__)


def persist_skip_progress_to_db(session_id: int, next_index: int, total_sentences: int) -> bool:
    """
    Persist skip progress into the database so API and agent stay in sync.

    Args:
        session_id: Writing session ID
        next_index: The next sentence index after skipping
        total_sentences: Total number of sentences for the session

    Returns:
        True if the session was found and updated, False otherwise.
    """
    db = SessionLocal()
    try:
        session = db.query(WritingSession).filter(WritingSession.id == session_id).first()
        if not session:
            return False

        session.current_sentence_index = min(next_index, total_sentences)
        if next_index >= total_sentences:
            session.status = SessionStatus.COMPLETED

        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error(
            "Error persisting skip progress for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        return False
    finally:
        db.close()

class WritingService:
    def __init__(self):
        # Use application DB config so ADK session tables live in the same PostgreSQL database
        self.session_service = DatabaseSessionService(db_url=get_database_url())
        
        # Initialize runner with writing_practice (coordinator)
        from src.writing.writing_practice_agent.agent import writing_practice  # Local import to avoid circular dependency
        self.runner = Runner(
            agent=writing_practice,
            app_name="WritingPractice",
            session_service=self.session_service
        )

    @staticmethod
    def persist_skip_progress_to_db(session_id: int, next_index: int, total_sentences: int) -> bool:
        """
        Persist skip progress into the database so API and agent stay in sync.

        Args:
            session_id: Writing session ID
            next_index: The next sentence index after skipping
            total_sentences: Total number of sentences for the session

        Returns:
            True if the session was found and updated, False otherwise.
        """
        db = SessionLocal()
        try:
            session = db.query(WritingSession).filter(WritingSession.id == session_id).first()
            if not session:
                return False

            session.current_sentence_index = min(next_index, total_sentences)
            if next_index >= total_sentences:
                session.status = SessionStatus.COMPLETED

            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.error(
                "Error persisting skip progress for session %s: %s",
                session_id,
                exc,
                exc_info=True,
            )
            return False
        finally:
            db.close()
    
    def _build_agent_query(self, source: str, message: str) -> str:
        """
        Build standardized query string for writing_practice with source metadata.
        
        Args:
            source: Origin of the action (e.g., chat_input, hint_button, generate_button, final_evaluation_button)
            message: The natural language message or trigger phrase
        
        Returns:
            Formatted string consumed by writing_practice:
                SOURCE:<source>\nMESSAGE:<message>
        """
        return f"SOURCE:{source}\nMESSAGE:{message}"
    
    async def create_writing_session(
        self, 
        user_id: int, 
        session_data: WritingSessionCreate, 
        db: Session
    ) -> WritingSessionResponse:
        """Create a new writing practice session"""
        try:
            # Create database session
            db_session = WritingSession(
                user_id=user_id,
                topic=session_data.topic,
                level=session_data.level,
                total_sentences=session_data.total_sentences,
                vietnamese_sentences=[],  # Will be generated by agent
                status=SessionStatus.ACTIVE
            )
            
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            # Initialize agent session
            # Note: vietnamese_sentences will be created by agent's output_key when it runs
            await self.session_service.create_session(
                app_name="WritingPractice",
                user_id=str(user_id),
                session_id=str(db_session.id),
                state={
                    "session_id": db_session.id,
                    "topic": session_data.topic,
                    "level": session_data.level.value,
                    "total_sentences": session_data.total_sentences,
                    "current_sentence_index": 0,
                    "evaluation_history": [],
                    "hint_history": {},
                }
            )
            
            # Generate Vietnamese text using writing_practice (will call text_generator tool)
            generated_text = None
            sentences = None
            # Run agent to generate text with logging
            try:
                # Query for writing_practice to call text_generator tool
                # Using trigger phrase that matches writing_practice instruction
                query = self._build_agent_query(
                    source="generate_button",
                    message="tạo văn bản"
                )
                
                # call_agent_with_logging returns final_response_text (string), NOT the structured dict
                # The structured output (dict) is automatically stored in state by ADK via output_key
                # We don't need the response text, only the structured output in state
                await call_agent_with_logging(
                    runner=self.runner,
                    user_id=str(user_id),
                    session_id=str(db_session.id),
                    query=query,
                    logger=logger
                )
                
                # Get structured output from agent session state (ADK stores it automatically)
                # Note: We read from state, NOT from response_text (which is just a string)
                try:
                    agent_session = await self.session_service.get_session(
                        app_name="WritingPractice",
                        user_id=str(user_id),
                        session_id=str(db_session.id)
                    )
                    
                    # Agent has output_key="vietnamese_sentences", so ADK automatically creates this key
                    # and stores the dict {full_text: "...", sentences: [...]} in state after agent runs
                    # The after_agent_callback automatically updates current_vietnamese_sentence
                    # We keep vietnamese_sentences as-is in state (no normalization needed)
                    vietnamese_sentences_data = agent_session.state.get("vietnamese_sentences", {})
                    if not isinstance(vietnamese_sentences_data, dict) or not vietnamese_sentences_data:
                        raise ValueError("AI text generation failed: No structured output from agent")
                    generated_text = vietnamese_sentences_data.get("full_text", "")
                    sentences = vietnamese_sentences_data.get("sentences", [])
                    
                    # Get current_vietnamese_sentence from state (set by after_agent_callback)
                    current_sentence = agent_session.state.get("current_vietnamese_sentence")

                except Exception as e:
                    print(f"Error getting structured output: {e}")
                    raise ValueError(f"AI text generation failed: {str(e)}")

            except Exception as agent_error:
                print(f"Agent error: {agent_error}")
                import traceback
                traceback.print_exc()
                # Raise error instead of using fallback
                raise ValueError(f"AI text generation failed: {str(agent_error)}")
            
            # Validate that we have sentences
            if not sentences or not isinstance(sentences, list) or len(sentences) == 0:
                raise ValueError("AI text generation failed: No sentences generated")
            
            if not generated_text:
                raise ValueError("AI text generation failed: No text generated")
            
            # Update database with generated sentences
            db_session.vietnamese_sentences = sentences
            db.commit()
            
            # create first assistant message (randomized prompt)
            prompt_templates = [
                "Hãy dịch câu tiếng Việt này sang tiếng Anh: {sentence}",
                "Dịch sang tiếng Anh câu sau: {sentence}",
                "Bạn hãy viết bản dịch tiếng Anh cho câu: {sentence}",
                "Hãy thử dịch câu này sang tiếng Anh: {sentence}",
            ]
            assistant_prompt = random.choice(prompt_templates).format(sentence=current_sentence)
            assistant_message = WritingChatMessage(
                session_id=db_session.id,
                role="assistant",
                content=assistant_prompt,
                sentence_index=0
            )
            db.add(assistant_message)
            db.commit()

            return WritingSessionResponse(
                id=db_session.id,
                user_id=db_session.user_id,
                topic=db_session.topic,
                level=db_session.level,
                total_sentences=db_session.total_sentences,
                current_sentence_index=db_session.current_sentence_index,
                status=db_session.status,
                vietnamese_text=generated_text,
                vietnamese_sentences=sentences,
                current_sentence=current_sentence,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo phiên luyện viết: {str(e)}")
    
    async def get_writing_session(self, session_id: int, user_id: int, db: Session) -> Optional[WritingSessionResponse]:
        """Get a specific writing session"""
        session = db.query(WritingSession).filter(
            WritingSession.id == session_id,
            WritingSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        # Get data from session state if available, otherwise use fallback
        try:
            agent_session = await self.session_service.get_session(
                app_name="WritingPractice",
                user_id=str(user_id),
                session_id=str(session_id)
            )
            
            state = agent_session.state or {}
            
            # Get sentences from state
            vietnamese_sentences_data = state.get("vietnamese_sentences")
            if isinstance(vietnamese_sentences_data, dict):
                vietnamese_sentences = vietnamese_sentences_data.get("sentences", [])
                full_text = vietnamese_sentences_data.get("full_text", "")
            elif isinstance(vietnamese_sentences_data, list):
                vietnamese_sentences = vietnamese_sentences_data
                full_text = " ".join(vietnamese_sentences) if vietnamese_sentences else ""
            else:
                # Fallback: use from database
                vietnamese_sentences = self._parse_sentences_from_db(session.vietnamese_sentences)
                full_text = " ".join(vietnamese_sentences) if vietnamese_sentences else ""
            
            # Get current sentence directly from state
            current_sentence = state.get("current_vietnamese_sentence")
            if not current_sentence and vietnamese_sentences:
                # Fallback: get from sentences array
                current_sentence = self._get_sentence_by_index(vietnamese_sentences, session.current_sentence_index)
                
        except Exception as e:
            print(f"Error getting data from state: {e}")
            # Fallback: use from database
            vietnamese_sentences = self._parse_sentences_from_db(session.vietnamese_sentences)
            full_text = " ".join(vietnamese_sentences) if vietnamese_sentences else ""
            current_sentence = self._get_sentence_by_index(vietnamese_sentences, session.current_sentence_index)
        
        return WritingSessionResponse(
            id=session.id,
            user_id=session.user_id,
            topic=session.topic,
            level=session.level,
            total_sentences=session.total_sentences,
            current_sentence_index=session.current_sentence_index,
            status=session.status,
            vietnamese_text=full_text,
            vietnamese_sentences=vietnamese_sentences,
            current_sentence=current_sentence,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def get_user_writing_sessions(self, user_id: int, db: Session) -> List[WritingSessionListResponse]:
        """Get all writing sessions for a user"""
        sessions = db.query(WritingSession).filter(
            WritingSession.user_id == user_id
        ).order_by(desc(WritingSession.created_at)).all()
        
        return [
            WritingSessionListResponse(
                id=session.id,
                topic=session.topic,
                level=session.level,
                total_sentences=session.total_sentences,
                current_sentence_index=session.current_sentence_index,
                status=session.status,
                created_at=session.created_at
            )
            for session in sessions
        ]
    
    def delete_writing_session(self, session_id: int, user_id: int, db: Session) -> bool:
        """Delete a writing session"""
        session = db.query(WritingSession).filter(
            WritingSession.id == session_id,
            WritingSession.user_id == user_id
        ).first()
        
        if not session:
            return False
            
        db.delete(session)
        db.commit()
        return True
    
    def complete_writing_session(self, session_id: int, user_id: int, db: Session) -> bool:
        """Complete a writing session"""
        session = db.query(WritingSession).filter(
            WritingSession.id == session_id,
            WritingSession.user_id == user_id
        ).first()
        
        if not session:
            return False
            
        session.status = SessionStatus.COMPLETED
        db.commit()
        return True
    
    async def send_chat_message(
        self, 
        session_id: int, 
        user_id: int, 
        message_data: ChatMessageCreate, 
        db: Session
    ) -> ChatMessageResponse:
        """Send a chat message and get agent response"""
        try:
            # Get session
            session = db.query(WritingSession).filter(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # Save user message
            user_message = WritingChatMessage(
                session_id=session_id,
                role="user",
                content=message_data.content,
                sentence_index=session.current_sentence_index
            )
            db.add(user_message)
            db.commit()
            
            # Note: current_vietnamese_sentence is managed by callbacks/tools
            # We don't need to manually update it here (that would be the WRONG way)
            # The get_next_sentence tool automatically updates it when moving to next sentence
            
            # Query for writing_practice to route to appropriate tool/subagent
            # If it's a translation, it will route to translation_evaluator_agent
            # If it's a question, it will route to guidance_agent
            query = self._build_agent_query(
                source="chat_input",
                message=message_data.content
            )
            
            # Get agent response with logging (writing_practice will route appropriately)
            agent_response = await call_agent_with_logging(
                runner=self.runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=query,
                logger=logger
            )
            db.refresh(session)
            # Save agent response
            agent_message = WritingChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_response,
                sentence_index=session.current_sentence_index
            )
            db.add(agent_message)
            
            # Update sentence index will be handled by agent tools
            
            db.commit()
            
            # Update session if needed
            db.refresh(session)
            
            return ChatMessageResponse(
                id=agent_message.id,
                session_id=agent_message.session_id,
                role=agent_message.role,
                content=agent_message.content,
                sentence_index=agent_message.sentence_index,
                status=session.status,
                created_at=agent_message.created_at
            )
            
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error sending chat message: {str(e)}")
    
    def get_chat_history(self, session_id: int, user_id: int, db: Session) -> List[ChatMessageResponse]:
        """Get chat history for a session"""
        # Verify session belongs to user
        session = db.query(WritingSession).filter(
            WritingSession.id == session_id,
            WritingSession.user_id == user_id
        ).first()
        
        if not session:
            return []
        
        messages = db.query(WritingChatMessage).filter(
            WritingChatMessage.session_id == session_id
        ).order_by(WritingChatMessage.created_at).all()
        
        return [
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                sentence_index=msg.sentence_index,
                status=session.status,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    
    async def get_translation_hint(self, session_id: int, user_id: int, db: Session) -> HintResponse:
        """Get translation hint for current sentence"""
        try:
            # Get session
            session = db.query(WritingSession).filter(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # Get agent session (should already exist)
            agent_session = await self.session_service.get_session(
                app_name="WritingPractice",
                user_id=str(user_id),
                session_id=str(session_id)
            )
            
            state = agent_session.state or {}
            hint_history = state.get("hint_history", {})
            current_sentence_index = state.get("current_sentence_index", session.current_sentence_index)
            
            # Get current Vietnamese sentence directly from state
            current_sentence = state.get("current_vietnamese_sentence")
            
            # Fallback: get from database if not in state
            if not current_sentence:
                db_sentences = self._parse_sentences_from_db(session.vietnamese_sentences)
                current_sentence = self._get_sentence_by_index(db_sentences, current_sentence_index)
            
            if not current_sentence:
                raise HTTPException(status_code=400, detail="Không có câu hiện tại để gợi ý")
            
            # Note: We don't update state here - that should be done via callbacks/tools
            # If current_vietnamese_sentence is missing, it will be set by the callback
            
            # Check if hint already exists in history
            cached_hint = hint_history.get(str(current_sentence_index))
            if cached_hint and isinstance(cached_hint, str):
                return HintResponse(
                    hint=cached_hint,
                    sentence_index=current_sentence_index
                )
            
            # Get hint from writing_practice (will call hint_provider tool)
            # Using trigger phrase that matches writing_practice instruction
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
            # Agent has output_key="current_hint_result", so ADK automatically stores it in state
            # The after_agent_callback automatically saves it to hint_history
            try:
                agent_session_after = await self.session_service.get_session(
                    app_name="WritingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id)
                )
                
                state_after = agent_session_after.state or {}
                
                # First try: get from hint_history (saved by callback)
                hint_history_after = state_after.get("hint_history", {})
                final_hint = hint_history_after.get(str(current_sentence_index))
                
                if not final_hint:
                    # Try with int key as fallback
                    final_hint = hint_history_after.get(current_sentence_index)
                
                # Second try: get directly from current_hint_result (output_key)
                if not final_hint:
                    hint_result_data = state_after.get("current_hint_result", {})
                    if isinstance(hint_result_data, dict):
                        final_hint = hint_result_data.get("hint_text", "")
                
                # Third try: use response text as fallback
                if not final_hint:
                    final_hint = hint_response or ""
            except Exception as state_error:
                logger.error(f"Error reading state after agent run: {state_error}")
                final_hint = hint_response or ""
            
            if not isinstance(final_hint, str) or not final_hint.strip():
                logger.error(f"Invalid hint: type={type(final_hint)}, value={final_hint}")
                raise HTTPException(status_code=502, detail="Không có gợi ý hợp lệ được tạo bởi AI")

            return HintResponse(
                hint=final_hint,
                sentence_index=current_sentence_index
            )
            
        except HTTPException:
            raise
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Error in get_translation_hint: {type(e).__name__}: {e}", exc_info=True)
            # Map common ADK error to 404
            msg = str(e) if e else "Unknown error"
            if "Session not found" in msg:
                raise HTTPException(status_code=404, detail="Không tìm thấy phiên làm việc của agent")
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy gợi ý: {msg}")
    
    async def get_final_evaluation(self, session_id: int, user_id: int, db: Session) -> FinalEvaluationResponse:
        """Get final evaluation for completed session"""
        try:
            # Get session
            session = db.query(WritingSession).filter(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            # Get final evaluation from writing_practice (will call final_evaluator tool)
            # Using trigger phrase that matches writing_practice instruction
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
                    app_name="WritingPractice",
                    user_id=str(user_id),
                    session_id=str(session_id)
                )
                
                # Extract structured evaluation from session state
                final_eval = agent_session.state.get("final_evaluation", {})
                
                if final_eval:
                    overall = float(final_eval.get("overall_score", 0))
                    accuracy = float(final_eval.get("accuracy_score", 0))
                    fluency = float(final_eval.get("fluency_score", 0))
                    vocabulary = float(final_eval.get("vocabulary_score", 0))
                    grammar = float(final_eval.get("grammar_score", 0))
                    feedback = str(final_eval.get("feedback", ""))
                    suggestions = final_eval.get("suggestions", [])
                    if not isinstance(suggestions, list):
                        suggestions = []
                else:
                    # Fallback if no structured output
                    overall = 0.0
                    accuracy = 0.0
                    fluency = 0.0
                    vocabulary = 0.0
                    grammar = 0.0
                    feedback = evaluation_response
                    suggestions = []
                    
            except Exception as e:
                print(f"Error getting structured output: {e}")
                # Fallback to zeros
                overall = 0.0
                accuracy = 0.0
                fluency = 0.0
                vocabulary = 0.0
                grammar = 0.0
                feedback = evaluation_response
                suggestions = []

            return FinalEvaluationResponse(
                session_id=session_id,
                total_sentences=session.total_sentences,
                completed_sentences=session.current_sentence_index,
                overall_score=overall,
                accuracy_score=accuracy,
                fluency_score=fluency,
                vocabulary_score=vocabulary,
                grammar_score=grammar,
                feedback=feedback,
                suggestions=suggestions,
                completed_at=datetime.now()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy đánh giá: {str(e)}")
    
    
    def _parse_sentences_from_db(self, db_sentences) -> List[str]:
        """Parse sentences from database (handles both list and JSON string for backward compatibility)"""
        if not db_sentences:
            return []
        
        # If it's already a list (ARRAY type), return it
        if isinstance(db_sentences, list):
            return db_sentences
        
        # If it's a string (JSON string from old format), parse it
        if isinstance(db_sentences, str):
            try:
                parsed = json.loads(db_sentences)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        
        return []
    
    def _get_sentences_from_db(self, session: WritingSession) -> List[str]:
        """Get sentences array from database session"""
        return self._parse_sentences_from_db(session.vietnamese_sentences)
    
    def _get_sentence_by_index(self, sentences: List[str], index: int) -> Optional[str]:
        """
        Get sentence at specific index from sentences array.
        
        Args:
            sentences: List of sentences
            index: Sentence index
            
        Returns:
            Sentence at index, or None if index is out of range
        """
        if sentences and isinstance(sentences, list) and 0 <= index < len(sentences):
            return sentences[index]
        return None
    
    async def skip_current_sentence(self, session_id: int, user_id: int, db: Session) -> ChatMessageResponse:
        """Skip current sentence via agent tool and return a chat-style assistant response."""
        try:
            session = db.query(WritingSession).filter(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MSG)
            
            if session.status == SessionStatus.COMPLETED:
                raise HTTPException(status_code=400, detail="Phiên luyện viết đã hoàn thành")
            
            query = self._build_agent_query(
                source="skip_button",
                message="Skip current sentence"
            )
            
            try:
                agent_reply = await call_agent_with_logging(
                    runner=self.runner,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    query=query,
                    logger=logger
                )
            except Exception as agent_error:
                logger.error("Agent skip error: %s", agent_error, exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Lỗi khi bỏ qua câu qua agent: {agent_error}"
                )
            
            db.refresh(session)
            final_text = agent_reply or "Đã bỏ qua câu hiện tại, hãy tiếp tục dịch câu tiếp theo nhé."
            
            assistant_message = WritingChatMessage(
                session_id=session_id,
                role="assistant",
                content=final_text,
                sentence_index=session.current_sentence_index
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            
            return ChatMessageResponse(
                id=assistant_message.id,
                session_id=assistant_message.session_id,
                role=assistant_message.role,
                content=assistant_message.content,
                sentence_index=assistant_message.sentence_index,
                status=session.status,
                created_at=assistant_message.created_at
            )
        
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi bỏ qua câu: {str(e)}")
    
