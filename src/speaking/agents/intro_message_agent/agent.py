"""
Intro Message Agent for Speaking Practice.

Generates the initial assistant turn when a new speaking session starts.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, Field

from src.speaking.agents.chat_agent.sub_agents.conversation_agent.agent import (
    CHAT_RESPONSE_STATE_KEY,
    after_conversation_callback,
)
from src.constants.cefr import get_cefr_definitions_string


class IntroMessageOutput(BaseModel):
    response_text: str = Field(description="Opening English line as the AI character")
    translation_sentence: str = Field(description="Single Vietnamese sentence translating response_text")


def after_intro_message_callback(callback_context: CallbackContext) -> types.Content | None:
    state = callback_context.state
    result = state.get("intro_message_result")
    if isinstance(result, dict):
        state[CHAT_RESPONSE_STATE_KEY] = result
        return after_conversation_callback(callback_context)
    return None


intro_message_agent = LlmAgent(
    name="intro_message",
    model="gemini-2.5-flash-lite",
    description="Generate opening assistant message.",
    instruction=f"""
    Generate the very first assistant message for the speaking practice session.

    CONTEXT:
    - AI role: {{ai_character}}
    - AI gender: {{ai_gender}}
    - Learner role: {{my_character}}
    - Scenario: "{{scenario}}"
    - CEFR level: {{level}}
    - User evaluation history: {{user_evaluation_history}}

    CRITICAL INSTRUCTIONS:
    1. Analyze relationship: Determine relationship between AI role "{{ai_character}}" and learner role "{{my_character}}". If family members (anh trai/em gái/chị gái/em trai), identify older/younger and use appropriate English terms ("brother" or "sister").
    2. Read scenario: "{{scenario}}" and start conversation naturally based on it. Do NOT use generic greetings.
    3. Respond ONLY in English as {{ai_character}} with tone matching gender {{ai_gender}}.
    4. Match vocabulary and grammar to CEFR level {{level}} (simpler for A1-A2).
    5. Sound natural, not robotic. Stay in character. Do NOT mention system or AI tutor.

    OUTPUT FORMAT:
    Return ONLY a JSON object:
    {{"response_text": "<natural opening line as {{ai_character}} based on scenario>", "translation_sentence": "Một câu tiếng Việt dịch lại response_text"}}
    - translation_sentence phải là đúng 1 câu tiếng Việt ngắn gọn diễn đạt lại nội dung response_text.

    {get_cefr_definitions_string()}
    """,
    output_schema=IntroMessageOutput,
    output_key="intro_message_result",
    after_agent_callback=after_intro_message_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

