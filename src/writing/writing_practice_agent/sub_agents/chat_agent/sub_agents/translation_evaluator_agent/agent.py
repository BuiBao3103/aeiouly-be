"""
Translation Evaluator Agent for Writing Practice
"""
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from src.constants.cefr import get_cefr_definitions_string


class EvaluationOutput(BaseModel):
    evaluation_text: str = Field(description="Learner-facing evaluation feedback")


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


def after_translation_evaluator_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves evaluation to evaluation_history in state
    after translation_evaluator_agent generates evaluation.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get evaluation_output from state (set by output_key)
    evaluation_data = state.get("evaluation_output", {})
    
    # Save evaluation to evaluation_history
    if isinstance(evaluation_data, dict):
        evaluation_text = evaluation_data.get("evaluation_text", "")
        if evaluation_text:
            current_sentence_index = state.get("current_sentence_index", 0)
            evaluation_history = state.get("evaluation_history", [])
            # Store evaluation result in history list
            evaluation_history.append(
                {
                    "sentence_index": current_sentence_index,
                    "vietnamese_sentence": state.get("current_vietnamese_sentence"),
                    "evaluation_result": evaluation_text.strip(),
                }
            )
            state["evaluation_history"] = evaluation_history
    
    return None  # Continue with normal agent processing


translation_evaluator_agent = LlmAgent(
    name="translation_evaluator",
    model="gemini-2.5-flash",
    description="Evaluate user's English translation, save result and move to next sentence if correct or only has minor spelling errors",
    instruction="""
    You are a Translation Evaluator Agent. Evaluate the learner's English translation against the Vietnamese sentence: "{current_vietnamese_sentence}".
    
    Given the translation, respond ONLY with a JSON object containing the evaluation feedback. Format: {{"evaluation_text": "your_feedback_here"}}
    
    Response language: Vietnamese
    Level: "{level}"
    Hint: "{current_hint_result?}"

    PROCESS:
    1. Evaluate meaning, grammar, and vocabulary
    2. If translation is correct OR only has minor spelling errors:
       - Call get_next_sentence() tool FIRST
       - Then respond ONLY with JSON: {{"evaluation_text": "Brief praise in Vietnamese + ask to translate next sentence"}}
    3. If translation has significant errors (grammar, vocabulary, meaning):
       - Do NOT call get_next_sentence()
       - Respond ONLY with JSON: {{"evaluation_text": "Point out 1-3 main errors in Vietnamese + ask to retry"}}

    EVALUATION CRITERIA:
    - Meaning: Match main idea and accurate information
    - Grammar: Tenses, articles, prepositions, verb structures
    - Vocabulary: Context-appropriate words; accept synonyms
    - Minor spelling errors are acceptable and do not prevent moving to next sentence

    OUTPUT REQUIREMENTS:
    - Your ENTIRE response must be ONLY a JSON object conforming to the output schema
    - NO plain text, NO explanations, NO headers, NO markdown formatting
    - The JSON object must contain exactly one field: "evaluation_text" (string)
    - Example format: {{"evaluation_text": "Bản dịch của bạn rất tốt! Hãy dịch câu tiếp theo."}}
    """,
    tools=[get_next_sentence],
    output_schema=EvaluationOutput,
    output_key="evaluation_output",
    after_agent_callback=after_translation_evaluator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

