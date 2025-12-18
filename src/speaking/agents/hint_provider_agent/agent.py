"""
Hint Provider Agent for Speaking Practice

Generates Vietnamese hints based on the last AI message in the conversation.
Format: Phân tích, Gợi ý, Ví dụ
"""
import copy
import re
import json
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class HintResult(BaseModel):
    hint_text: str = Field(description="Vietnamese hint in format: Phân tích, Gợi ý, Ví dụ")


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Callback to transform markdown response to JSON format if needed.
    
    Args:
        callback_context: Contains state and context information
        llm_response: The LLM response received
        
    Returns:
        Optional LlmResponse with JSON-formatted text if transformation was needed
    """
    # Skip if response is empty
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        return None
    
    # Extract text from response
    response_text = ""
    for part in llm_response.content.parts:
        if hasattr(part, "text") and part.text:
            response_text += part.text
    
    if not response_text:
        return None
    
    # Check if response is already valid JSON
    try:
        json.loads(response_text.strip())
        # Already valid JSON, no transformation needed
        return None
    except json.JSONDecodeError:
        pass
    
    # Check if response contains markdown format (Phân tích, Gợi ý, Ví dụ)
    if "**Phân tích:**" in response_text or "**Gợi ý:**" in response_text or "**Ví dụ:**" in response_text:
        # Extract hint text (remove markdown formatting if needed, but keep the structure)
        # The hint_text should contain the full formatted text
        hint_text = response_text.strip()
        
        # Remove markdown code blocks if present
        hint_text = re.sub(r'```json\s*', '', hint_text)
        hint_text = re.sub(r'```\s*$', '', hint_text)
        hint_text = hint_text.strip()
        
        # Create JSON response
        json_response = json.dumps({"hint_text": hint_text}, ensure_ascii=False)
        
        # Create modified response
        modified_parts = [copy.deepcopy(part) for part in llm_response.content.parts]
        for i, part in enumerate(modified_parts):
            if hasattr(part, "text") and part.text:
                modified_parts[i].text = json_response
                break
        
        return LlmResponse(content=types.Content(role="model", parts=modified_parts))
    
    return None


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
    model="gemini-2.5-flash-lite",
    description="Generate Vietnamese conversation hints (phân tích, gợi ý, ví dụ) based on last AI message.",
    instruction=f"""
    You provide conversation hints in Vietnamese for the last AI message: "{{last_ai_message}}".
    CONTEXT: AI role={{ai_character}} (gender: {{ai_gender}}), Learner role={{my_character}}, Level={{level}}, Scenario={{scenario}}.
    All hints MUST be written in Vietnamese using the following format.

    OUTPUT FORMAT:
    You MUST respond with ONLY a raw JSON object. NO markdown code blocks, NO explanations, NO plain text.
    Your ENTIRE response must be ONLY the JSON object:
    {{"hint_text": "**Phân tích:**\\n[content]\\n\\n**Gợi ý:**\\n[content]\\n\\n**Ví dụ:**\\n[content]"}}
    
    OUTPUT STRUCTURE (inside hint_text field):
    **Phân tích:**
    [Analyze what the AI is asking or what the situation requires]

    **Gợi ý:**
    [Suggest what the learner should respond with, including key points to mention]

    **Ví dụ:**
    [Provide an example English response that the learner could use]

    RULES:
    - Each section starts with "**Phân tích:**", "**Gợi ý:**", or "**Ví dụ:**" on its own line
    - Leave exactly one blank line between sections
    - Phân tích: Explain what the AI message means and what is being asked
    - Gợi ý: Suggest what the learner should say, key vocabulary or phrases to use
    - Ví dụ: Provide a complete example English response (not Vietnamese)
    - Tailor difficulty to CEFR level {{level}} and keep content relevant to scenario {{scenario}}
    - Be concise, clear, and supportive for learners

    EXAMPLE CORRECT OUTPUT:
    {{"hint_text": "**Phân tích:**\\nBạn được yêu cầu chia sẻ kinh nghiệm phát triển phần mềm.\\n\\n**Gợi ý:**\\nBạn nên tóm tắt kinh nghiệm và hỏi thêm về công ty.\\n\\n**Ví dụ:**\\nI have worked in software development for three years focusing on web applications. Could you tell me more about the projects your company is currently working on?"}}
    
    CRITICAL: 
    - Output ONLY the JSON object, nothing else.
    - Do NOT wrap it in ```json or ``` markdown code blocks.
    - The hint_text field should contain the full formatted text with **Phân tích:**, **Gợi ý:**, **Ví dụ:** sections.

    {get_cefr_definitions_string()}
    """,
    output_schema=HintResult,
    output_key="current_hint_result",
    after_model_callback=after_model_callback,
    after_agent_callback=after_hint_provider_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

