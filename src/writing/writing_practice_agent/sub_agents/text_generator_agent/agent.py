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
    Generate Vietnamese source text for translation practice.

    INPUT (from state):
    - topic: {{topic}}
    - level: {{level}}
    - total_sentences: {{total_sentences}}

    REQUIREMENTS:
    - Stay strictly on topic "{{topic}}"
    - Match CEFR level "{{level}}" vocabulary and structure
    - Produce exactly {{total_sentences}} sentences
    - All text MUST BE IN VIETNAMESE
    - Coherent, natural, content-rich
    - Vary sentence structures; use proper punctuation
    - Do NOT greet, instruct, or describe your process
    - Do NOT include English text

    {get_cefr_definitions_string()}

    OUTPUT:
    - full_text: Complete Vietnamese passage (concatenation of all sentences)
    - sentences: List of standalone Vietnamese sentences with punctuation
    """,
    output_schema=VietnameseTextResult,
    output_key="vietnamese_sentences",
    after_agent_callback=after_text_generator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


