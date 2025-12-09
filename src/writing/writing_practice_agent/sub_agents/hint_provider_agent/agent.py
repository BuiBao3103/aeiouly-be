"""
Hint Provider Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string
from ...schemas import HintResult



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
    model="gemini-2.5-flash-lite",
    description="Generate Vietnamese translation hints (vocabulary + grammar) for the current sentence.",
    instruction=f"""
    You provide concise translation hints in Vietnamese for the sentence "{{current_vietnamese_sentence}}".
    All hints MUST be written in Vietnamese using Markdown format.

    ### OUTPUT STRUCTURE
    **Từ vựng:**
    - `vocabulary 1` → English meaning
    - `vocabulary 2` → English meaning
    - *(Add enough items so tổng cộng 4-6 từ/cụm từ phủ đều động từ, danh từ, tính từ quan trọng của câu)*

    **Ngữ pháp:**
    - Grammar guidance: Suggest what English grammar structures to use

    ### RULES
    - Provide 4-6 vocabulary bullets total (ưu tiên động từ, danh từ, tính từ then trạng từ nếu hữu ích).
    - Each bullet point starts with "- " and occupies its own line.
    - Leave exactly one blank line between the vocabulary and grammar sections.
    - Grammar section: Focus on WHAT ENGLISH GRAMMAR STRUCTURES to use. Suggest the English grammar patterns, tenses, or structures needed to translate the sentence correctly.
    - Use markdown to format grammar examples, e.g., **to + verb**, **will + verb**.
    - Do NOT explain Vietnamese grammar structures. Only suggest English grammar to use.
    - Tailor difficulty to CEFR level {{level}} and keep content relevant to topic {{topic}}.
    - Be concise, clear, and supportive for learners.

    ### EXAMPLE
    **Từ vựng:**
    - `đi chợ` → go to the market
    - `vội vàng` → in a hurry

    **Ngữ pháp:**
    - Dùng cấu trúc **to + verb** hoặc **in order to + verb** để diễn tả mục đích.
    - Dùng thì tương lai đơn **will + verb** hoặc **be going to + verb** để diễn tả hành động tương lai.
    - Dùng cấu trúc **don't be too + adj** để đưa ra lời khuyên không nên làm gì quá mức.

    CEFR guidance:
    {get_cefr_definitions_string()}
    """,
    output_schema=HintResult,
    output_key="current_hint_result",
    after_agent_callback=after_hint_provider_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)