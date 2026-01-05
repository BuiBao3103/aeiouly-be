"""
Service layer for Writing Practice module
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from src.writing.models import WritingSession, WritingChatMessage, SessionStatus, CEFRLevel
from src.users.models import User
from src.writing.schemas import (
    WritingSessionCreate,
    WritingSessionResponse,
    WritingSessionListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    HintResponse,
    FinalEvaluationResponse
)
from src.database import AsyncSessionLocal

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from datetime import datetime
import json
from src.config import get_database_url, get_sync_database_url
from src.utils.agent_utils import call_agent_with_logging, build_agent_query, get_agent_state, update_session_state
import logging
from src.users.service import UsersService
import random
from fastapi import HTTPException
from src.writing.agents.chat_agent.agent import chat_agent
from src.writing.agents.hint_provider_agent.agent import hint_provider_agent
from src.writing.agents.final_evaluator_agent.agent import final_evaluator_agent
from src.writing.agents.text_generator_agent.agent import text_generator_agent
# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện viết"
APP_NAME = "WritingPractice"
# Logger for writing service
logger = logging.getLogger(__name__)


class WritingService:
    def __init__(self):
        self.session_service = DatabaseSessionService(
            db_url=get_sync_database_url())

        self.users_service = UsersService()

        self.chat_runner = Runner(
            agent=chat_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.text_generator_runner = Runner(
            agent=text_generator_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.hint_provider_runner = Runner(
            agent=hint_provider_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        self.final_evaluator_runner = Runner(
            agent=final_evaluator_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )


    async def persist_skip_progress_to_db(self, session_id: int, next_index: int) -> bool:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WritingSession).where(WritingSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                return False

            total_sentences = session.total_sentences
            session.current_sentence_index = min(next_index, total_sentences)

            if next_index >= total_sentences:
                session.status = SessionStatus.COMPLETED

            await db.commit()
            return True

    async def create_writing_session(
        self,
        user_id: int,
        session_data: WritingSessionCreate,
        db: AsyncSession
    ) -> WritingSessionResponse:
        """Create a new writing practice session"""
        # Get user's evaluation history
        evaluation_history = await self.users_service.get_user_evaluation_history(user_id, db)

        try:
            # Tạo session object NHƯNG CHƯA COMMIT
            db_session = WritingSession(
                user_id=user_id,
                topic=session_data.topic,
                level=session_data.level,
                total_sentences=session_data.total_sentences,
                vietnamese_sentences=[],
                status=SessionStatus.ACTIVE
            )
            db.add(db_session)
            
            # FLUSH để có ID nhưng chưa commit transaction
            await db.flush()
            session_id = db_session.id

            # Initialize agent session
            await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(session_id),
                state={
                    "session_id": session_id,
                    "topic": session_data.topic,
                    "level": session_data.level.value,
                    "total_sentences": session_data.total_sentences,
                    "current_sentence_index": 0,
                    "current_vietnamese_sentence": "",
                    "user_evaluation_history": evaluation_history,
                    "evaluation_history": [],
                    "hint_history": {},
                }
            )

            # Generate Vietnamese text using writing_practice
            try:
                query = build_agent_query(source="generate_button", message="")

                await call_agent_with_logging(
                    runner=self.text_generator_runner,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    query=query,
                    logger=logger,
                    agent_name=text_generator_agent.name
                )

                # Get structured output from agent session state
                agent_session = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=str(session_id)
                )

                vietnamese_sentences_data = agent_session.state.get("vietnamese_sentences", {})
                if not isinstance(vietnamese_sentences_data, dict) or not vietnamese_sentences_data:
                    raise ValueError("AI text generation failed: No structured output from agent")
                
                generated_text = vietnamese_sentences_data.get("full_text", "")
                sentences = vietnamese_sentences_data.get("sentences", [])
                current_sentence = agent_session.state.get("current_vietnamese_sentence")

            except Exception as agent_error:
                logger.error(f"Agent error: {agent_error}", exc_info=True)
                raise ValueError(f"AI text generation failed: {str(agent_error)}")

            # Validate that we have sentences
            if not sentences or not isinstance(sentences, list) or len(sentences) == 0:
                raise ValueError("AI text generation failed: No sentences generated")

            if not generated_text:
                raise ValueError("AI text generation failed: No text generated")

            # EXPIRE object để tránh lỗi greenlet khi cập nhật
            db.expire(db_session)
            
            # Query lại để có fresh instance
            db_session = await db.get(WritingSession, session_id)
            if not db_session:
                raise ValueError(f"Session {session_id} not found")
            
            # Update with generated sentences
            db_session.vietnamese_sentences = sentences

            # Create first assistant message
            prompt_templates = [
                "Hãy dịch câu tiếng Việt này sang tiếng Anh: {sentence}",
                "Dịch sang tiếng Anh câu sau: {sentence}",
                "Bạn hãy viết bản dịch tiếng Anh cho câu: {sentence}",
                "Hãy thử dịch câu này sang tiếng Anh: {sentence}",
            ]
            assistant_prompt = random.choice(prompt_templates).format(sentence=current_sentence)
            assistant_message = WritingChatMessage(
                session_id=session_id,
                role="assistant",
                content=assistant_prompt,
                sentence_index=0
            )
            db.add(assistant_message)
            
            # COMMIT DUY NHẤT 1 LẦN Ở CUỐI - nếu có lỗi thì rollback toàn bộ
            await db.commit()
            await db.refresh(db_session)

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
            # Rollback sẽ xóa toàn bộ: session + message
            await db.rollback()
            logger.error(f"Failed to create writing session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Lỗi khi tạo phiên luyện viết: {str(e)}"
            )
    async def get_writing_session(self, session_id: int, user_id: int, db: AsyncSession) -> Optional[WritingSessionResponse]:
        """Get a specific writing session"""
        result = await db.execute(
            select(WritingSession).where(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Get data from session state if available, otherwise use fallback
        try:
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(session_id)
            )

            state = agent_session.state or {}

            # Get sentences from state
            vietnamese_sentences_data = state.get("vietnamese_sentences")
            if isinstance(vietnamese_sentences_data, dict):
                vietnamese_sentences = vietnamese_sentences_data.get(
                    "sentences", [])
                full_text = vietnamese_sentences_data.get("full_text", "")
            elif isinstance(vietnamese_sentences_data, list):
                vietnamese_sentences = vietnamese_sentences_data
                full_text = " ".join(
                    vietnamese_sentences) if vietnamese_sentences else ""
            else:
                # Fallback: use from database
                vietnamese_sentences = self._parse_sentences_from_db(
                    session.vietnamese_sentences)
                full_text = " ".join(
                    vietnamese_sentences) if vietnamese_sentences else ""

            # Get current sentence directly from state
            current_sentence = state.get("current_vietnamese_sentence")
            if not current_sentence and vietnamese_sentences:
                # Fallback: get from sentences array
                current_sentence = self._get_sentence_by_index(
                    vietnamese_sentences, session.current_sentence_index)

        except Exception as e:
            print(f"Error getting data from state: {e}")
            # Fallback: use from database
            vietnamese_sentences = self._parse_sentences_from_db(
                session.vietnamese_sentences)
            full_text = " ".join(
                vietnamese_sentences) if vietnamese_sentences else ""
            current_sentence = self._get_sentence_by_index(
                vietnamese_sentences, session.current_sentence_index)

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

    async def get_user_writing_sessions(self, user_id: int, db: AsyncSession) -> List[WritingSessionListResponse]:
        """Get all writing sessions for a user"""
        result = await db.execute(
            select(WritingSession).where(
                WritingSession.user_id == user_id
            ).order_by(desc(WritingSession.created_at))
        )
        sessions = result.scalars().all()

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

    async def delete_writing_session(self, session_id: int, user_id: int, db: AsyncSession) -> bool:
        """Delete a writing session"""
        result = await db.execute(
            select(WritingSession).where(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return False

        await db.delete(session)
        await db.commit()
        return True

    async def complete_writing_session(self, session_id: int, user_id: int, db: AsyncSession) -> bool:
        """Complete a writing session"""
        result = await db.execute(
            select(WritingSession).where(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return False

        session.status = SessionStatus.COMPLETED
        await db.commit()
        return True

    async def send_chat_message(
        self,
        session_id: int,
        user_id: int,
        message_data: ChatMessageCreate,
        db: AsyncSession
    ) -> ChatMessageResponse:
        """Send a chat message and get agent response"""
        try:
            # Get session
            result = await db.execute(
                select(WritingSession).where(
                    WritingSession.id == session_id,
                    WritingSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=404, detail=SESSION_NOT_FOUND_MSG)

            # Save user message
            user_message = WritingChatMessage(
                session_id=session_id,
                role="user",
                content=message_data.content,
                sentence_index=session.current_sentence_index
            )
            db.add(user_message)
            await db.commit()

            # Note: current_vietnamese_sentence is managed by callbacks/tools
            # We don't need to manually update it here (that would be the WRONG way)
            # The get_next_sentence tool automatically updates it when moving to next sentence

            # Query for writing_practice to route to appropriate tool/subagent
            # If it's a translation, it will route to translation_evaluator_agent
            # If it's a question, it will route to guidance_agent

            # Get agent response with logging (chat_agent will route to translation_evaluator or guidance)
            await call_agent_with_logging(
                runner=self.chat_runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=build_agent_query(
                    source="chat_input",
                    message=message_data.content
                ),
                logger=logger,
                agent_name=chat_agent.name
            )

            # Get response from state (using chat_response key)
            state = await get_agent_state(
                session_service=self.session_service,
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(session_id),
            )

            chat_response_data = state.get(
                "chat_response", {}) if isinstance(state, dict) else {}

            if not isinstance(chat_response_data, dict):
                raise HTTPException(
                    status_code=500, detail="Agent không trả về dữ liệu hợp lệ")

            agent_response = (chat_response_data.get(
                "response_text") or "").strip()
            if not agent_response:
                raise HTTPException(
                    status_code=500, detail="Agent không tạo được phản hồi")

            await db.refresh(session)
            # Save agent response
            agent_message = WritingChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_response,
                sentence_index=session.current_sentence_index
            )
            db.add(agent_message)

            # Update sentence index will be handled by agent tools

            await db.commit()

            # Update session if needed
            await db.refresh(session)

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
            await db.rollback()
            raise ValueError(f"Error sending chat message: {str(e)}")

    async def get_chat_history(self, session_id: int, user_id: int, db: AsyncSession) -> List[ChatMessageResponse]:
        """Get chat history for a session"""
        # Verify session belongs to user
        result = await db.execute(
            select(WritingSession).where(
                WritingSession.id == session_id,
                WritingSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return []

        result = await db.execute(
            select(WritingChatMessage).where(
                WritingChatMessage.session_id == session_id
            ).order_by(WritingChatMessage.created_at)
        )
        messages = result.scalars().all()

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

    async def get_translation_hint(self, session_id: int, user_id: int, db: AsyncSession) -> HintResponse:
        """Get translation hint for current sentence"""
        try:
            # Get session
            result = await db.execute(
                select(WritingSession).where(
                    WritingSession.id == session_id,
                    WritingSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=404, detail=SESSION_NOT_FOUND_MSG)

            # Get agent session (should already exist)
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(session_id)
            )

            state = agent_session.state or {}
            hint_history = state.get("hint_history", {})
            current_sentence_index = state.get(
                "current_sentence_index", session.current_sentence_index)

            # Get current Vietnamese sentence directly from state
            current_sentence = state.get("current_vietnamese_sentence")

            # Fallback: get from database if not in state
            if not current_sentence:
                db_sentences = self._parse_sentences_from_db(
                    session.vietnamese_sentences)
                current_sentence = self._get_sentence_by_index(
                    db_sentences, current_sentence_index)

            if not current_sentence:
                raise HTTPException(
                    status_code=400, detail="Không có câu hiện tại để gợi ý")

            # Note: We don't update state here - that should be done via callbacks/tools
            # If current_vietnamese_sentence is missing, it will be set by the callback

            # Check if hint already exists in history
            cached_hint = hint_history.get(str(current_sentence_index))
            if cached_hint and isinstance(cached_hint, str):
                return HintResponse(
                    hint=cached_hint,
                    sentence_index=current_sentence_index
                )

            # Get hint directly from hint_provider_agent
            try:
                hint_response = await call_agent_with_logging(
                    runner=self.hint_provider_runner,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    query=build_agent_query(source="hint_button", message=""),
                    logger=logger,
                    agent_name=hint_provider_agent.name
                )
            except Exception as agent_error:
                logger.error(f"Error calling hint agent: {agent_error}")
                raise HTTPException(
                    status_code=500, detail=f"Lỗi khi gọi agent tạo gợi ý: {str(agent_error)}")

            # Read hint from state after agent finishes
            # Agent has output_key="current_hint_result", so ADK automatically stores it in state
            # The after_agent_callback automatically saves it to hint_history
            try:
                agent_session_after = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=str(session_id)
                )

                state_after = agent_session_after.state or {}

                # First try: get from hint_history (saved by callback)
                hint_history_after = state_after.get("hint_history", {})
                final_hint = hint_history_after.get(
                    str(current_sentence_index))

                if not final_hint:
                    # Try with int key as fallback
                    final_hint = hint_history_after.get(current_sentence_index)

                # Second try: get directly from current_hint_result (output_key)
                if not final_hint:
                    hint_result_data = state_after.get(
                        "current_hint_result", {})
                    if isinstance(hint_result_data, dict):
                        final_hint = hint_result_data.get("hint_text", "")

                # Third try: use response text as fallback
                if not final_hint:
                    final_hint = hint_response or ""
            except Exception as state_error:
                logger.error(
                    f"Error reading state after agent run: {state_error}")
                final_hint = hint_response or ""

            if not isinstance(final_hint, str) or not final_hint.strip():
                logger.error(
                    f"Invalid hint: type={type(final_hint)}, value={final_hint}")
                raise HTTPException(
                    status_code=502, detail="Không có gợi ý hợp lệ được tạo bởi AI")

            return HintResponse(
                hint=final_hint,
                sentence_index=current_sentence_index
            )

        except HTTPException:
            raise
        except Exception as e:
            # Log the full error for debugging
            logger.error(
                f"Error in get_translation_hint: {type(e).__name__}: {e}", exc_info=True)
            # Map common ADK error to 404
            msg = str(e) if e else "Unknown error"
            if "Session not found" in msg:
                raise HTTPException(
                    status_code=404, detail="Không tìm thấy phiên làm việc của agent")
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi lấy gợi ý: {msg}")

    async def get_final_evaluation(self, session_id: int, user_id: int, db: AsyncSession) -> FinalEvaluationResponse:
        """Get final evaluation for completed session"""
        try:
            # Get session
            result = await db.execute(
                select(WritingSession).where(
                    WritingSession.id == session_id,
                    WritingSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=404, detail=SESSION_NOT_FOUND_MSG)

            # Get final evaluation directly from final_evaluator_agent
            evaluation_response = await call_agent_with_logging(
                runner=self.final_evaluator_runner,
                user_id=str(user_id),
                session_id=str(session_id),
                query=build_agent_query(
                    source="final_evaluation_button", message=""),
                logger=logger,
                agent_name=final_evaluator_agent.name
            )

            # Get structured output from agent session state
            try:
                # Get the structured output from the agent's session state
                agent_session = await self.session_service.get_session(
                    app_name=APP_NAME,
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

                # Update user's evaluation history via UsersService
                await self.users_service.update_evaluation_history(
                    user_id=user_id, 
                    new_evaluation=final_eval, 
                    db=db
                )

            except Exception as e:
                print(f"Error getting structured output or updating user history: {e}")
                logger.error(f"Error processing final evaluation for user {user_id}, session {session_id}: {e}", exc_info=True)
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
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi lấy đánh giá: {str(e)}")

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

    async def skip_current_sentence(self, session_id: int, user_id: int, db: AsyncSession) -> ChatMessageResponse:
        """Skip current sentence and move to next one, updating state directly."""
        try:
            result = await db.execute(
                select(WritingSession).where(
                    WritingSession.id == session_id,
                    WritingSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(
                    status_code=404, detail=SESSION_NOT_FOUND_MSG)

            if session.status == SessionStatus.COMPLETED:
                raise HTTPException(
                    status_code=400, detail="Phiên luyện viết đã hoàn thành")

            # Get current state
            agent_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(session_id)
            )
            state = agent_session.state or {}
            
            current_index = state.get("current_sentence_index", session.current_sentence_index)
            total_sentences = state.get("total_sentences", session.total_sentences)
            vietnamese_sentences_data = state.get("vietnamese_sentences", {})
            
            # Check if this is the last sentence
            if current_index >= total_sentences - 1:
                # Session complete
                next_index = total_sentences
                message = "Đã bỏ qua câu cuối cùng. Phiên học kết thúc! Bạn có thể xem phần đánh giá tổng kết khi sẵn sàng."
                
                # Update state
                state["current_sentence_index"] = total_sentences
                state["current_vietnamese_sentence"] = "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!"
                
                # Update database
                session.current_sentence_index = total_sentences
                session.status = SessionStatus.COMPLETED
                await db.commit()

                await self.persist_skip_progress_to_db(
                    session_id, total_sentences
                )
                
                # Update agent state
                await update_session_state(
                    session_service=self.session_service,
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    state_delta={
                        "current_sentence_index": total_sentences,
                        "current_vietnamese_sentence": "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!"
                    },
                    author="system",
                    invocation_id_prefix="skip_sentence",
                    logger=logger
                )
            else:
                # Move to next sentence
                next_index = current_index + 1
                
                # Get next sentence
                sentences = vietnamese_sentences_data.get("sentences", []) if isinstance(vietnamese_sentences_data, dict) else []
                if not sentences:
                    # Fallback to database
                    sentences = self._parse_sentences_from_db(session.vietnamese_sentences)
                
                next_sentence = sentences[next_index] if next_index < len(sentences) else None
                
                # Generate translation request message
                if next_sentence:
                    templates = [
                        f"Hãy dịch câu sau: \"{next_sentence}\"",
                        f"Dịch câu này sang tiếng Anh: \"{next_sentence}\"",
                        f"Hãy thử dịch câu: \"{next_sentence}\"",
                        f"Câu tiếp theo cần dịch là: \"{next_sentence}\"",
                        f"Hãy dịch câu \"{next_sentence}\" sang tiếng Anh nhé!",
                        f"Dịch câu này: \"{next_sentence}\"",
                        f"Hãy dịch câu \"{next_sentence}\"",
                        f"Dịch câu sau sang tiếng Anh: \"{next_sentence}\"",
                        f"Câu tiếp theo: \"{next_sentence}\". Hãy dịch nó nhé!",
                    ]
                    message = random.choice(templates)
                else:
                    message = "Hãy dịch câu tiếp theo."
                
                # Update database
                session.current_sentence_index = next_index
                await db.commit()
                
                # Update agent state
                state_delta = {
                    "current_sentence_index": next_index
                }
                if next_sentence:
                    state_delta["current_vietnamese_sentence"] = next_sentence
                
                await update_session_state(
                    session_service=self.session_service,
                    app_name=APP_NAME,
                    user_id=str(user_id),
                    session_id=str(session_id),
                    state_delta=state_delta,
                    author="system",
                    invocation_id_prefix="skip_sentence",
                    logger=logger
                )
            
            # Create assistant message
            assistant_message = WritingChatMessage(
                session_id=session_id,
                role="assistant",
                content=message,
                sentence_index=next_index
            )
            db.add(assistant_message)
            await db.commit()
            await db.refresh(assistant_message)

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
            await db.rollback()
            logger.error(f"Error skipping sentence: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi bỏ qua câu: {str(e)}")
