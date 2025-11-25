"""
Skip Response Agent for Speaking Practice.

Produces a fresh assistant turn when the learner chooses to skip their turn.
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


class SkipResponseOutput(BaseModel):
    response_text: str = Field(description="Next assistant reply as the AI character")
    translation_sentence: str = Field(description="Single Vietnamese sentence translating response_text")


def after_skip_response_callback(callback_context: CallbackContext) -> types.Content | None:
    state = callback_context.state
    result = state.get("skip_response_result")
    if isinstance(result, dict):
        state[CHAT_RESPONSE_STATE_KEY] = result
        return after_conversation_callback(callback_context)
    return None


skip_response_agent = LlmAgent(
    name="skip_response",
    model="gemini-2.0-flash",
    description="Generate the next assistant turn after the learner presses skip.",
    instruction=f"""
    The learner asked to skip their turn. Continue the conversation for them.

    CONTEXT FROM STATE:
    - AI role: {{ai_character}}
    - Learner role: {{my_character}}
    - Scenario: "{{scenario}}"
    - CEFR level: {{level}}
    - chat_history: {{chat_history?}}

    TASK:
    - Produce the next natural English line as {{ai_character}}.
    - Briefly acknowledge the flow and move the scenario forward with a question or prompt.
    - Reference relevant details from the scenario or recent chat history if available.
    - Keep vocabulary/grammar aligned with level {{level}}.
    - Do NOT mention the skip action or system instructions.

    OUTPUT FORMAT:
    Return ONLY a JSON object:
    {{
        "response_text": "<assistant reply as {{ai_character}}>",
        "translation_sentence": "Một câu tiếng Việt dịch lại response_text"
    }}
    - translation_sentence phải là đúng 1 câu tiếng Việt ngắn gọn, phù hợp với level {{level}}.

    {get_cefr_definitions_string()}
    """,
    output_schema=SkipResponseOutput,
    output_key="skip_response_result",
    after_agent_callback=after_skip_response_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

