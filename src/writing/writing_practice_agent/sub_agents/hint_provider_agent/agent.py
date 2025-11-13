"""
Hint Provider Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class HintResult(BaseModel):
    hint_text: str = Field(description="Vietnamese Markdown hint (vocabulary + grammar) using '- ' list syntax per line")


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
    
    # Get hint_result from state (set by output_key)
    hint_result_data = state.get("hint_result", {})
    
    # Save hint to hint_history
    if isinstance(hint_result_data, dict):
        hint_text = hint_result_data.get("hint_text", "")
        if hint_text:
            current_sentence_index = state.get("current_sentence_index", 0)
            hint_history = state.get("hint_history", {})
            # Store hint text in history dict with sentence_index as key
            hint_history[str(current_sentence_index)] = hint_text
            state["hint_history"] = hint_history
    
    return None  # Continue with normal agent processing


hint_provider_agent = LlmAgent(
    name="hint_provider",
    model="gemini-2.0-flash",
    description="Generate Vietnamese translation hints (vocabulary + grammar) for the current sentence.",
    instruction=f"""
    You provide concise translation hints in Vietnamese for sentence "{{current_vietnamese_sentence}}".
    All hints MUST be written in Vietnamese using Markdown lists (no HTML).

    ### OUTPUT STRUCTURE (IN VIETNAMESE)
    **Từ vựng:**
    - `từ vựng 1` → English meaning
    - `từ vựng 2` → English meaning

    **Ngữ pháp:**
    - Short grammar reminder in Vietnamese

    ### RULES
    - Every bullet begins with "- " and occupies its own line.
    - Leave exactly one blank line between the vocabulary and grammar sections.
    - Do NOT use HTML tags (<br>, <strong>, etc.).
    - Tailor difficulty to CEFR level {{level}} and keep content relevant to topic {{topic}}.
    - Stay concise, actionable, and supportive.

    ### EXAMPLE (FOR REFERENCE ONLY)
    **Từ vựng:**
    - `đi chợ` → go to the market
    - `vội vàng` → in a hurry

    **Ngữ pháp:**
    - Nhắc dùng thì hiện tại đơn cho thói quen hằng ngày.

    CEFR guidance:
    {get_cefr_definitions_string()}
    """,
    output_schema=HintResult,
    output_key="hint_result",
    after_agent_callback=after_hint_provider_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)