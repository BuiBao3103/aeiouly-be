"""
Skip Response Agent for Speaking Practice.

Produces a fresh assistant turn when the learner chooses to skip their turn.
"""
from google.adk.agents import LlmAgent
from src.speaking.speaking_practice_agent.sub_agents.chat_agent.sub_agents.conversation_agent.agent import (
    ConversationResponse,
    after_conversation_callback,
)
from src.constants.cefr import get_cefr_definitions_string


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
        "response_text": "<assistant reply as {{ai_character}}>"
    }}

    {get_cefr_definitions_string()}
    """,
    output_schema=ConversationResponse,
    output_key="conversation_response",
    after_agent_callback=after_conversation_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

