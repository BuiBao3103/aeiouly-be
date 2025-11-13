"""
Text Generator Agent for Writing Practice.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import List, Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class VietnameseTextResult(BaseModel):
    full_text: str = Field(description="The complete Vietnamese text that was generated")
    sentences: List[str] = Field(description="Array of individual Vietnamese sentences")


def after_text_generator_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically updates current_vietnamese_sentence in state
    after text_generator_agent generates Vietnamese text.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get vietnamese_sentences from state (set by output_key)
    vietnamese_sentences_data = state.get("vietnamese_sentences", {})
    
    # Update current_vietnamese_sentence to first sentence if available
    if isinstance(vietnamese_sentences_data, dict):
        sentences = vietnamese_sentences_data.get("sentences", [])
        if sentences and isinstance(sentences, list) and len(sentences) > 0:
            # Update state using callback_context.state (CORRECT way)
            state["current_vietnamese_sentence"] = sentences[0]
            state["current_sentence_index"] = 0
    
    return None  # Continue with normal agent processing


text_generator_agent = LlmAgent(
    name="text_generator",
    model="gemini-2.0-flash",
    description="Generate Vietnamese practice text based on topic, CEFR level, and desired sentence count from state.",
    instruction=f"""
    You are an AI writer that produces Vietnamese source text for translation drills.
    Your entire output (full_text and sentences) MUST BE IN VIETNAMESE.

    ## INPUT (READ FROM STATE)
    - topic: {{topic}}
    - level: {{level}}
    - total_sentences: {{total_sentences}}

    ## REQUIREMENTS
    1. Stay strictly on the provided topic "{{topic}}".
    2. Match vocabulary and structure to the CEFR level "{{level}}".
    3. Produce exactly {{total_sentences}} sentences (one sentence per item in the list).
    4. Ensure the text is coherent, content-rich, and sounds natural in Vietnamese.
    5. Vary sentence structures and vocabulary; use proper punctuation (., ?, !, ,, ;, …).
    6. Do NOT greet, instruct the learner, or ask them to take action.
    7. Do NOT include English text, and do NOT wrap sentences in quotation marks.
    8. Do NOT describe your process or mention that you are generating text.
    9. Use only the data in state; never ask the learner to provide topic/level/count again.

    {get_cefr_definitions_string()}

    ## OUTPUT FORMAT (JSON)
    {{
        "full_text": "<complete Vietnamese passage>",
        "sentences": ["Sentence 1.", "Sentence 2.", ...]
    }}

    - full_text must be the concatenation of all sentences in natural order.
    - sentences must be a list of standalone Vietnamese sentences with punctuation.
    """,
    output_schema=VietnameseTextResult,
    output_key="vietnamese_sentences",
    after_agent_callback=after_text_generator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


