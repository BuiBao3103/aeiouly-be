"""
Intro Message Agent for Speaking Practice.

Generates the initial assistant turn when a new speaking session starts.
"""
from google.adk.agents import LlmAgent
from src.speaking.speaking_practice_agent.sub_agents.chat_agent.sub_agents.conversation_agent.agent import (
    ConversationResponse,
    after_conversation_callback,
)
from src.constants.cefr import get_cefr_definitions_string


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
        "response_text": "<opening line as {{ai_character}}>"
    }}

    {get_cefr_definitions_string()}
    """,
    output_schema=ConversationResponse,
    output_key="conversation_response",
    after_agent_callback=after_conversation_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

