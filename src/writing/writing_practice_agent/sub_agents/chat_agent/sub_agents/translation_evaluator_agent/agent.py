"""
Translation Evaluator Agent for Writing Practice
"""
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


def save_evaluation_result(
    evaluation_result: str,
    accuracy_score: float,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Save evaluation result to session state.
    
    Args:
        evaluation_result: The evaluation result text from agent (description of evaluation)
        accuracy_score: Accuracy score (0-100) for this translation
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message
    """
    current_sentence_index = tool_context.state.get("current_sentence_index", 0)
    evaluation_history = tool_context.state.get("evaluation_history", [])
    evaluation_history.append(
        {
            "sentence_index": current_sentence_index,
            "evaluation_result": evaluation_result,
            "accuracy_score": accuracy_score,
        }
    )
    tool_context.state["evaluation_history"] = evaluation_history

    return {
        "action": "save_evaluation",
        "sentence_index": current_sentence_index,
        "accuracy_score": accuracy_score,
        "message": f"Saved evaluation for sentence {current_sentence_index + 1}",
    }


def get_next_sentence(tool_context: ToolContext) -> Dict[str, Any]:
    """Move to the next sentence in the writing session.
    
    Args:
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message with next sentence information
    """
    from src.writing.service import persist_skip_progress_to_db
    
    current_index = tool_context.state.get("current_sentence_index", 0)
    total_sentences = tool_context.state.get("total_sentences", 0)
    session_id = tool_context.state.get("session_id")

    if current_index >= total_sentences - 1:
        tool_context.state["current_sentence_index"] = total_sentences
        if session_id:
            persisted = persist_skip_progress_to_db(
                session_id=session_id,
                next_index=total_sentences,
                total_sentences=total_sentences,
            )
            if not persisted:
                print(f"Could not persist completion for session {session_id}")
        return {
            "action": "session_complete",
            "message": "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!",
            "current_index": total_sentences,
            "total_sentences": total_sentences,
        }

    next_index = current_index + 1
    tool_context.state["current_sentence_index"] = next_index
    
    # Update current_vietnamese_sentence in state
    vietnamese_sentences_data = tool_context.state.get("vietnamese_sentences", {})
    if isinstance(vietnamese_sentences_data, dict) and "sentences" in vietnamese_sentences_data:
        sentences_list = vietnamese_sentences_data.get("sentences", [])
        if 0 <= next_index < len(sentences_list):
            tool_context.state["current_vietnamese_sentence"] = sentences_list[next_index]
    
    if session_id:
        persisted = persist_skip_progress_to_db(
            session_id=session_id,
            next_index=next_index,
            total_sentences=total_sentences,
        )
        if not persisted:
            print(f"Could not persist next sentence progress for session {session_id}")

    return {
        "action": "next_sentence",
        "current_index": next_index,
        "total_sentences": total_sentences,
        "message": f"Chuyển sang câu {next_index + 1} trong tổng số {total_sentences} câu",
    }


translation_evaluator_agent = Agent(
    name="translation_evaluator",
    model="gemini-2.0-flash",
    description="Evaluate user's English translation, save result and move to next sentence if score ≥90%",
    instruction=f"""
    You are an AI that evaluates English translations from learners.

    CURRENT VIETNAMESE SENTENCE: "{{current_vietnamese_sentence}}"
    DIFFICULTY LEVEL: {{level}}
    HINT (if available): {{current_hint_result?}}

    TASK:
    Evaluate the learner's English translation against the Vietnamese sentence, determine accuracy (0-100%), and decide whether to proceed to the next sentence.

    REQUIRED PROCESS:
    1. Analyze the translation against the Vietnamese sentence
    2. Evaluate: meaning, grammar, vocabulary
    3. Determine accuracy score (0-100%)
    4. Create evaluation description
    5. Call save_evaluation_result(evaluation_result, accuracy_score)
    6. If score ≥ 90%:
       - Start with brief praise (1 sentence)
       - Call get_next_sentence()
       - Ask to translate the next sentence (don't specify which sentence)
    7. If score < 90%:
       - Point out specific errors (1-3 main issues)
       - Ask to retry the current sentence
       - Do NOT call get_next_sentence

    EVALUATION CRITERIA (CEFR reference):
    {get_cefr_definitions_string()}

    EVALUATION DETAILS:
    - Meaning: Match with Vietnamese sentence (main idea, accurate information)
    - Grammar: Tenses, articles, prepositions, singular/plural, verb structures
    - Vocabulary: Context-appropriate words; accept reasonable synonyms
    - Minor spelling errors: ALLOWED and don't prevent ≥90% if overall is correct

    PRAISE EXAMPLES (when ≥90%, choose one):
    - "Rất tốt, bản dịch của bạn khá tự nhiên!"
    - "Tuyệt vời, bạn đã truyền tải đúng ý chính!"
    - "Làm tốt lắm, ngữ pháp nhìn chung ổn định!"

    IMPORTANT:
    - MUST call save_evaluation_result() to save evaluation
    - If ≥90%, MUST call get_next_sentence() to advance
    - When ≥90%, only ask to translate next sentence (don't specify which)
    - When <90%, point out specific errors and ask to retry
    - Evaluate objectively and fairly
    - Allow minor spelling errors if meaning and grammar are correct
    - If hint is available (current_hint_result), consider it when evaluating to provide more appropriate feedback
    """,
    tools=[save_evaluation_result, get_next_sentence],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

