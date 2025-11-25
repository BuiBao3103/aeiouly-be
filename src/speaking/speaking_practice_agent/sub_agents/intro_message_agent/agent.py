"""
Intro Message Agent for Speaking Practice.

Generates the initial assistant turn when a new speaking session starts.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, Field

from src.speaking.speaking_practice_agent.sub_agents.chat_agent.sub_agents.conversation_agent.agent import (
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
    model="gemini-2.0-flash",
    description="Compose the opening assistant message for a new speaking session.",
    instruction=f"""
    You generate the very first assistant message for the speaking practice session.

    CONTEXT FROM STATE:
    - AI role: {{ai_character}}
    - Learner role: {{my_character}}
    - Scenario: "{{scenario}}"
    - CEFR level: {{level}}

    REQUIREMENTS:
    1. Respond ONLY in English, fully in-character as {{ai_character}}.
    2. Craft a natural greeting that references the scenario and invites the learner to speak.
    3. Keep tone friendly and match CEFR level {{level}} (simpler language for lower levels).
    4. Ask a follow-up question so the learner knows how to start.
    5. Do NOT mention the system, instructions, or that you are an AI tutor. Stay inside the scenario.

    OUTPUT FORMAT:
    Return ONLY a JSON object that matches:
    {{
        "response_text": "<opening line as {{ai_character}}>",
        "translation_sentence": "Một câu tiếng Việt dịch lại response_text"
    }}
    - translation_sentence phải là đúng 1 câu tiếng Việt ngắn gọn diễn đạt lại nội dung response_text.

    {get_cefr_definitions_string()}
    """,
    output_schema=IntroMessageOutput,
    output_key="intro_message_result",
    after_agent_callback=after_intro_message_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

