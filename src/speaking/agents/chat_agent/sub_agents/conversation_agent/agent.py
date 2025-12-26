"""
Conversation Agent for Speaking Practice

Handles English conversation between user and AI character.
Responds in English and decides when to end the conversation.
"""
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string

from src.speaking.agents.schemas import ConversationAgentResponse

# State key for storing conversation response
CHAT_RESPONSE_STATE_KEY = "chat_response"
# Maximum number of messages to include in chat history for prompt
MAX_CHAT_HISTORY_MESSAGES = 10


def before_conversation_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that limits chat_history to the most recent 10 messages before agent runs.
    
    This ensures the prompt only includes recent conversation context, improving
    performance and token usage while maintaining conversation flow.
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    chat_history = state.get("chat_history", [])
    
    # Limit to most recent 10 messages (keep the latest ones)
    if len(chat_history) > MAX_CHAT_HISTORY_MESSAGES:
        # Keep only the last MAX_CHAT_HISTORY_MESSAGES messages
        limited_history = chat_history[-MAX_CHAT_HISTORY_MESSAGES:]
        # Store limited history in a separate key for prompt injection
        state["recent_chat_history"] = limited_history
    else:
        # If history is already within limit, use it as is
        state["recent_chat_history"] = chat_history
    
    return None  # Continue with normal agent processing


async def after_conversation_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves user message and AI response to chat_history in state
    after conversation_agent generates response.
    
    Also handles session completion when is_conversation_complete=True.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get pending user message (set by service before calling agent)
    pending_user_message = state.get("pending_user_message", "")
    
    # Get chat_response from state (set by output_key)
    conversation_data = state.get(CHAT_RESPONSE_STATE_KEY, {})
    
    chat_history = state.get("chat_history", [])
    
    # Add user message to chat_history if it exists (only for conversation_agent)
    if pending_user_message:
        user_message_order = state.get("user_message_order", 0)
        chat_history.append({
            "role": "user",
            "content": pending_user_message.strip(),
            "order": user_message_order,
        })
        state["user_message_order"] = user_message_order + 1
        # Clear pending user message after adding to history
        state["pending_user_message"] = ""
    
    # Save AI response to chat_history and update last_ai_message/order
    if isinstance(conversation_data, dict):
        response_text = conversation_data.get("response_text", "")
        is_conversation_complete = conversation_data.get("is_conversation_complete", False)
        
        if response_text:
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
        
        # Handle conversation completion
        if is_conversation_complete:
            session_id = state.get("session_id")
            if session_id:
                try:
                    from src.speaking.service import SpeakingService
                    speaking_service = SpeakingService()
                    await speaking_service.mark_session_completed(session_id)
                except Exception as exc:
                    logger = __import__("logging").getLogger(__name__)
                    logger.error(f"Error handling conversation completion: {exc}")
    
    return None  # Continue with normal agent processing


conversation_agent = LlmAgent(
    name="conversation",
    model="gemini-2.5-flash-lite",
    description="English conversation partner as AI character.",
    instruction=f"""
    You are an AI conversation partner. 
    AI role: "{{ai_character}}".
    AI gender: {{ai_gender}}.
    Learner role: "{{my_character}}".
    Conversation Level: {{level}}.
    Scenario: "{{scenario}}".
    Last AI Message: {{last_ai_message?}}
    
    TASKS:
    1. Respond naturally in English as {{ai_character}} (tone matches {{ai_gender}})
    2. Keep conversation engaging and appropriate for CEFR level {{level}}
    3. Decide when conversation has reached natural conclusion
    4. Set is_conversation_complete=true when conversation should end
    
    CONVERSATION RULES:
    - Analyze relationship: If family roles (anh trai/em gái/chị gái/em trai), identify older/younger and use correct English terms (brother/sister)
    - Respond ONLY in English as {{ai_character}} with tone matching gender {{ai_gender}}
    - Keep vocabulary and grammar appropriate for level {{level}}
    - Be natural, friendly, engaging. Ask follow-up questions to keep conversation flowing
    - translation_sentence must be a single Vietnamese sentence translating response_text, subject must suit roles "{{my_character}}" and "{{ai_character}}"
    
    WHEN TO END:
    Set is_conversation_complete=true when scenario fully explored, natural conclusion reached, sufficient information exchanged, or goal achieved. Do NOT end too early. Allow at least 5-8 exchanges.
    
    CONVERSATION HISTORY (most recent 10 messages): {{recent_chat_history?}}
    
    OUTPUT FORMAT:
    You MUST respond with a JSON object matching the output schema:
    {{
        "response_text": "Your English response here as {{ai_character}}",
        "translation_sentence": "A SINGLE Vietnamese sentence translating response_text (optional, can be null)",
        "is_conversation_complete": false
    }}
    
    FIELD DESCRIPTIONS:
    - response_text (required): Your English response as {{ai_character}}
    - translation_sentence (optional): Single Vietnamese sentence translating response_text. Can be null if not needed.
    - is_conversation_complete (required): Set to true when conversation should end, false otherwise
    
    CRITICAL: 
    - Output MUST match the schema exactly
    - response_text is required and must be a non-empty string
    - translation_sentence is optional (can be null or empty string)
    - is_conversation_complete must be a boolean (true/false)
    
    {get_cefr_definitions_string()}
    """,
    output_schema=ConversationAgentResponse,
    output_key="chat_response",
    before_agent_callback=before_conversation_callback,
    after_agent_callback=after_conversation_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

