"""
Translation Evaluator Agent for Writing Practice
"""
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from src.writing.agents.schemas import TranslationEvaluationResponse


async def _move_to_next_sentence(state: dict, db: AsyncSession) -> None:
    """Move to the next sentence in the writing session."""
    # Import here to avoid circular dependency
    from src.writing.service import WritingService
    
    current_sentence_index = state.get("current_sentence_index", 0)
    total_sentences = state.get("total_sentences", 0)
    session_id = state.get("session_id")

    # Check if this is the last sentence
    if current_sentence_index >= total_sentences - 1:
        state["current_sentence_index"] = total_sentences
        state["current_vietnamese_sentence"] = "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!"
        
        if session_id:
            # Use await since persist_skip_progress_to_db is now async
            await WritingService.persist_skip_progress_to_db(
                session_id, total_sentences, total_sentences, db)
    else:
        # Move to next sentence
        next_index = current_sentence_index + 1
        state["current_sentence_index"] = next_index

        # Update current_vietnamese_sentence in state
        vietnamese_sentences_data = state.get("vietnamese_sentences", {})
        if isinstance(vietnamese_sentences_data, dict) and "sentences" in vietnamese_sentences_data:
            sentences_list = vietnamese_sentences_data.get("sentences", [])
            if 0 <= next_index < len(sentences_list):
                state["current_vietnamese_sentence"] = sentences_list[next_index]

        if session_id:
            # Use await since persist_skip_progress_to_db is now async
            await WritingService.persist_skip_progress_to_db(
                session_id, next_index, total_sentences, db)


async def after_translation_evaluator_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves evaluation to evaluation_history in state
    and moves to next sentence if translation is correct.

    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    db = callback_context.database_session # Get db session from callback_context

    # Get chat_response from state (set by output_key="chat_response")
    chat_response_data = state.get("chat_response", {})

    # Save evaluation to evaluation_history and handle sentence progression
    if isinstance(chat_response_data, dict):
        response_text = chat_response_data.get("response_text", "")
        is_correct = chat_response_data.get("is_correct", False)
        
        if response_text:
            # Save to evaluation_history
            current_sentence_index = state.get("current_sentence_index", 0)
            evaluation_history = state.get("evaluation_history", [])
            # Store evaluation result in history list
            evaluation_history.append(
                {
                    "sentence_index": current_sentence_index,
                    "vietnamese_sentence": state.get("current_vietnamese_sentence"),
                    "evaluation_result": response_text.strip(),
                }
            )
            state["evaluation_history"] = evaluation_history

            # Move to next sentence if translation is correct
            if is_correct:
                await _move_to_next_sentence(state, db)

    return None  # Continue with normal agent processing


translation_evaluator_agent = LlmAgent(
    name="translation_evaluator",
    model="gemini-2.5-flash",
    description="Evaluate English translation and provide feedback",
    instruction="""Vietnamese: "{current_vietnamese_sentence}"
        Level: {level}
        Hint used: {current_hint_result?}

        CRITICAL FIRST CHECK:
        - The MESSAGE you receive MUST be in ENGLISH. 
        - If MESSAGE is in Vietnamese or any other language (not English), it is WRONG.
        - If MESSAGE contains Vietnamese characters or Vietnamese words, set is_correct=false immediately.
        - Example: If MESSAGE is "Các nhà khoa học thường thực hiện nhiều thí nghiệm thú vị" → This is Vietnamese, NOT English translation → WRONG.

        EVALUATE translation COMPREHENSIVELY - check ALL aspects:
        - Language: MESSAGE must be in English (not Vietnamese or other languages)
        - Articles: a/an/the usage (especially before plural nouns, uncountable nouns)
        - Grammar: tense, prepositions, verb forms, subject-verb agreement
        - Vocabulary: correct word choice, singular/plural forms (e.g., graphic vs graphics)
        - Meaning: must match Vietnamese sentence completely
        - Spelling: minor typos acceptable if meaning is clear
        - if has hint evaluation base on hint result

        CRITICAL: You MUST identify and list ALL errors in a single response. Do NOT mention errors one by one across multiple attempts.
        When listing errors, each error must be on its own line, prefixed with numbered markers like "(1) ...", "(2) ...".

        DECISION:
        ✅ CORRECT: MESSAGE is in English AND has correct grammar/vocabulary/meaning → set is_correct=true, respond with VARIED praise + prompt for next sentence
        ❌ WRONG: MESSAGE is in Vietnamese/other language OR has grammar/vocabulary/meaning errors → set is_correct=false, explain ALL errors found in one response + ask to retry with VARIED wording

        RESPONSE VARIETY (CRITICAL):
        - NEVER repeat the exact same phrase. Always vary your wording naturally.
        - For CORRECT responses, use different praise phrases each time:
          * "Tuyệt vời! Bạn dịch đúng rồi. Hãy dịch câu tiếp theo nhé."
          * "Chính xác! Bản dịch của bạn hoàn toàn đúng. Tiếp tục với câu sau nhé!"
          * "Rất tốt! Bạn đã dịch đúng. Hãy thử câu tiếp theo."
          * "Hoàn hảo! Câu dịch này đúng rồi. Câu tiếp theo đang chờ bạn đấy!"
          * "Xuất sắc! Bạn dịch rất chính xác. Hãy tiếp tục với câu sau."
          * "Đúng rồi! Bản dịch của bạn rất tốt. Câu tiếp theo nhé!"
        - For ERROR responses, vary the opening and closing phrases:
          * "Lỗi: ..." / "Có một số lỗi: ..." / "Bạn cần sửa: ..." / "Cần chỉnh sửa: ..."
          * "... Thử lại!" / "... Hãy sửa lại nhé!" / "... Vui lòng thử lại!" / "... Cố gắng sửa lại nhé!"

        OUTPUT FORMAT:
        - Raw JSON only (no code fences), structure: {{"response_text": "...", "is_correct": true/false}}
        - You may use lightweight Markdown **bold** inside response_text to highlight lỗi hoặc từ cần sửa.

        EXAMPLES:
        ✅ Correct (varied): 
          {{"response_text": "Chính xác! Bản dịch của bạn hoàn toàn đúng. Tiếp tục với câu sau nhé!", "is_correct": true}}
          {{"response_text": "Rất tốt! Bạn đã dịch đúng. Hãy thử câu tiếp theo.", "is_correct": true}}
        ❌ Wrong language (Vietnamese instead of English):
          {{"response_text": "Lỗi: Bạn đã gửi câu tiếng Việt thay vì bản dịch tiếng Anh. Hãy dịch câu \"{current_vietnamese_sentence}\" sang tiếng Anh và gửi lại nhé!", "is_correct": false}}
        ❌ Has multiple errors (varied): 
          {{"response_text": "Có một số lỗi:\n(1) Không dùng mạo từ 'a' trước 'graphics' (danh từ số nhiều)\n(2) 'graphic' cần thành 'graphics' (số nhiều) khi nói về đồ họa trò chơi\nNên là: 'This game has beautiful graphics and nice music'. Hãy sửa lại nhé!", "is_correct": false}}
        ❌ Has single error (varied): 
          {{"response_text": "Bạn cần sửa: thiếu '-ing' sau 'like'. Nên là: 'I like playing games'. Vui lòng thử lại!", "is_correct": false}}""",
    output_schema=TranslationEvaluationResponse,
    output_key="chat_response",
    after_agent_callback=after_translation_evaluator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
