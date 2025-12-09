"""
Text Generator Agent for Writing Practice.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string
from ...schemas import VietnameseTextResult


def after_text_generator_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that generates full_text from sentences and updates state
    after text_generator_agent generates Vietnamese sentences.

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

    # Process sentences and generate full_text
    if isinstance(vietnamese_sentences_data, dict):
        sentences = vietnamese_sentences_data.get("sentences", [])
        if sentences and isinstance(sentences, list) and len(sentences) > 0:
            # Count actual number of sentences generated
            actual_sentence_count = len(sentences)

            # Generate full_text by joining sentences with spaces
            full_text = " ".join(sentences)

            # Update state with both full_text and sentences
            state["vietnamese_sentences"] = {
                "full_text": full_text,
                "sentences": sentences
            }

            # Update total_sentences to match actual count
            state["total_sentences"] = actual_sentence_count

            # Update current_vietnamese_sentence to first sentence
            state["current_vietnamese_sentence"] = sentences[0]
            state["current_sentence_index"] = 0

    return None  # Continue with normal agent processing


text_generator_agent = LlmAgent(
    name="text_generator",
    model="gemini-2.5-flash",
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
    - sentences: List of standalone Vietnamese sentences with punctuation
    """,
    output_schema=VietnameseTextResult,
    output_key="vietnamese_sentences",
    after_agent_callback=after_text_generator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
