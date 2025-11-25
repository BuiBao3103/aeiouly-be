"""
Conversation Agent for Speaking Practice

Handles English conversation between user and AI character.
Responds in English and decides when to end the conversation.
"""
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, Field
from src.constants.cefr import get_cefr_definitions_string
from src.speaking.service import SpeakingService


class ConversationResponse(BaseModel):
    response_text: str = Field(description="English response text from AI character")
    translation_sentence: str = Field(
        description="Single Vietnamese sentence translating response_text"
    )


def end_conversation(tool_context: ToolContext) -> Dict[str, Any]:
    """End the conversation and mark session as completed.
    
    Args:
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message with session completion information
    """
    session_id = tool_context.state.get("session_id")
    
    if session_id:
        from src.database import SessionLocal
        from src.speaking.models import SpeakingSession
        
        db = SessionLocal()
        try:
            session = db.query(SpeakingSession).filter(SpeakingSession.id == session_id).first()
            if session:
                session.status = "completed"
                db.commit()
        except Exception as exc:
            db.rollback()
            print(f"Could not persist session completion for session {session_id}: {exc}")
        finally:
            db.close()
    
    tool_context.state["conversation_ended"] = True
    
    return {
        "action": "conversation_complete",
        "message": "Thank you for the conversation! The session has been completed. You can review your practice when ready.",
    }


def after_conversation_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves conversation message to chat_history in state
    after conversation_agent generates response.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get conversation_response from state (set by output_key)
    conversation_data = state.get("conversation_response", {})
    
    # Save conversation to chat_history and update last_ai_message/order
    if isinstance(conversation_data, dict):
        response_text = conversation_data.get("response_text", "")
        if response_text:
            chat_history = state.get("chat_history", [])
            message_order = state.get("assistant_message_order", 0)
            # Store conversation response in history list
            chat_history.append(
                {
                    "role": "assistant",
                    "content": response_text.strip(),
                    "order": message_order,
                }
            )
            state["chat_history"] = chat_history
            # Update last_ai_message for hint provider agent
            state["last_ai_message"] = response_text.strip()
            state["last_ai_message_order"] = message_order
            state["assistant_message_order"] = message_order + 1
    
    return None  # Continue with normal agent processing


conversation_agent = LlmAgent(
    name="conversation",
    model="gemini-2.5-flash",
    description="Engage in English conversation as AI character, respond naturally, and decide when conversation should end",
    instruction=f"""
    You are an AI conversation partner for English speaking practice. You play the role of "{{ai_character}}" in the scenario: "{{scenario}}".
    
    The learner is playing the role of "{{my_character}}".
    
    Your task is to:
    1. Respond naturally in English as your character
    2. Keep the conversation engaging and appropriate for CEFR level {{level}}
    3. Decide when the conversation has reached a natural conclusion
    4. Call end_conversation() tool when the conversation should end
    
    CONVERSATION RULES:
    - Respond ONLY in English
    - Stay in character as {{ai_character}}
    - Keep responses appropriate for level {{level}}
    - Be natural, friendly, and engaging
    - Ask follow-up questions to keep conversation flowing
    - Adapt vocabulary and grammar complexity to match {{level}}
    
    WHEN TO END CONVERSATION:
    Call end_conversation() tool when:
    - The scenario has been fully explored
    - The conversation has reached a natural conclusion
    - Both parties have exchanged sufficient information
    - The conversation goal has been achieved
    
    Do NOT end conversation too early. Allow for at least 5-8 exchanges before considering ending.
    
    CONVERSATION HISTORY (from state):
    {{chat_history?}}
    
    RESPONDING TO USER MESSAGES:
    - You will only receive real learner utterances (chat_input). Intro/skip turns are handled by other tools.
    - Respond naturally to each message while keeping the scenario moving forward.
    
    OUTPUT FORMAT:
    You MUST respond with ONLY a raw JSON object. NO markdown code blocks, NO explanations, NO plain text.
    Your ENTIRE response must be ONLY the JSON object conforming to the output schema:
    {{
        "response_text": "Your English response here as {{ai_character}}",
        "translation_sentence": "A SINGLE Vietnamese sentence translating response_text"
    }}
    
    translation_sentence requirements:
    - Must be exactly one concise Vietnamese sentence translating the meaning of response_text.
    - Keep vocabulary aligned with CEFR level {{level}}.
    
    CRITICAL: 
    - Output ONLY the JSON object, nothing else.
    - Do NOT wrap it in ```json or ``` markdown code blocks.
    - Do NOT add any text before or after the JSON.
    - Example of CORRECT output: {{"response_text": "...", "translation_sentence": "..."}}
    - Example of WRONG output: ```json{{"response_text": "...", "translation_sentence": "..."}}```
    
    {get_cefr_definitions_string()}
    """,
    tools=[end_conversation],
    output_schema=ConversationResponse,
    output_key="conversation_response",
    after_agent_callback=after_conversation_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

