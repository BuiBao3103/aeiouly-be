"""
Text Refiner Agent

This agent refines reading texts based on review feedback.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from src.constants.cefr import get_cefr_definitions_string

# Constants
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Use faster model for refinement (most time-consuming in loop)


class TextGenerationResult(BaseModel):
    """Response schema for text generation"""
    content: str = Field(..., description="Generated reading text content")


def create_refiner_instruction() -> str:
    """Create instruction for text refiner"""
    instruction = """
    Bạn là AI chuyên tinh chỉnh bài đọc tiếng Anh.
    
    Your task is to refine a reading text based on review feedback.
    
    ## INPUTS
    **Current Text:**
    {current_text}
    
    **Review Feedback:**
    {review_feedback}
    
    ## TASK
    Carefully apply the feedback to improve the text.
    - Maintain the original tone, theme, and content quality
    - Ensure all original requirements are still met:
      1. Level CEFR phù hợp: {level}
      2. Genre: {genre}
      3. Topic: {topic}
      4. Word count: xấp xỉ {target_word_count} (±20%)
    - Apply the feedback to adjust word count while maintaining quality
    
    """
    
    # Add CEFR definitions
    instruction += get_cefr_definitions_string()
    
    instruction += """
    ## OUTPUT INSTRUCTIONS
    - Output ONLY the refined text content in JSON format
    - Do not add explanations or justifications
    - Maintain the same level, genre, and topic
    - Adjust length according to feedback
    
    OUTPUT FORMAT:
    {{
      "content": "Toàn bộ nội dung bài đọc đã được tinh chỉnh..."
    }}
    """
    
    return instruction


def after_refiner_callback(callback_context: CallbackContext) -> Optional[None]:
    """Store refined content into state for next review iteration."""
    state = callback_context.state or {}
    result = state.get("text_generation_result", {})
    if isinstance(result, dict) and result.get("content"):
        state["current_text"] = result["content"]
    return None


# Define the Text Refiner Agent
text_refiner_agent = LlmAgent(
    name="text_refiner_agent",
    model=GEMINI_MODEL,
    instruction=create_refiner_instruction(),
    description="Refines reading texts based on feedback to meet word count requirements",
    output_schema=TextGenerationResult,
    output_key="text_generation_result",
    after_agent_callback=after_refiner_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

