"""
Hint Provider Agent for Speaking Practice

Generates Vietnamese hints based on the last AI message in the conversation.
Format: Phân tích, Gợi ý, Ví dụ
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class HintResult(BaseModel):
    hint_text: str = Field(description="Vietnamese hint in format: Phân tích, Gợi ý, Ví dụ")


def after_hint_provider_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves hint to hint_history in state
    after hint_provider_agent generates hint.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get current_hint_result from state (set by output_key)
    hint_result_data = state.get("current_hint_result", {})
    
    # Save hint to hint_history dict keyed by last AI message order
    if isinstance(hint_result_data, dict):
        hint_text = hint_result_data.get("hint_text", "")
        if hint_text:
            hint_history = state.get("hint_history", {}) or {}
            last_ai_message = state.get("last_ai_message", "")
            last_ai_order = state.get("last_ai_message_order")
            if last_ai_order is not None:
                hint_history[str(last_ai_order)] = {
                    "last_ai_message": last_ai_message,
                    "hint": hint_text,
                }
            state["hint_history"] = hint_history
    
    return None  # Continue with normal agent processing


hint_provider_agent = LlmAgent(
    name="hint_provider",
    model="gemini-2.0-flash",
    description="Generate Vietnamese conversation hints (phân tích, gợi ý, ví dụ) based on last AI message.",
    instruction=f"""
    You provide conversation hints in Vietnamese for the last AI message: "{{last_ai_message}}".
    CONTEXT:
    - AI role: {{ai_character}} (gender: {{ai_gender}})
    - Learner role: {{my_character}}
    All hints MUST be written in Vietnamese using the following format.

    ### OUTPUT STRUCTURE
    **Phân tích:**
    [Analyze what the AI is asking or what the situation requires]

    **Gợi ý:**
    [Suggest what the learner should respond with, including key points to mention]

    **Ví dụ:**
    [Provide an example English response that the learner could use]

    ### RULES
    - Each section starts with "**Phân tích:**", "**Gợi ý:**", or "**Ví dụ:**" on its own line
    - Leave exactly one blank line between sections
    - Phân tích: Explain what the AI message means and what is being asked
    - Gợi ý: Suggest what the learner should say, key vocabulary or phrases to use
    - Ví dụ: Provide a complete example English response (not Vietnamese)
    - Tailor difficulty to CEFR level {{level}} and keep content relevant to scenario {{scenario}}
    - Be concise, clear, and supportive for learners

    ### EXAMPLE
    **Phân tích:**
    Bạn được yêu cầu chia sẻ kinh nghiệm phát triển phần mềm.

    **Gợi ý:**
    Bạn nên tóm tắt kinh nghiệm và hỏi thêm về công ty.

    **Ví dụ:**
    I have worked in software development for three years focusing on web applications. Could you tell me more about the projects your company is currently working on?

    CEFR guidance:
    {get_cefr_definitions_string()}
    """,
    output_schema=HintResult,
    output_key="current_hint_result",
    after_agent_callback=after_hint_provider_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

