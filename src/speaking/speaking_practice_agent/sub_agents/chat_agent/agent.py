"""
Chat coordination agent for the speaking practice module.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.conversation_agent.agent import conversation_agent
from .sub_agents.guidance_agent.agent import guidance_agent


chat_agent = Agent(
    name="chat",
    model="gemini-2.0-flash",
    description="Routes chat box messages to conversation or guidance tool while ensuring appropriate responses.",
    instruction="""
    You coordinate every learner message. ALWAYS call a tool first; never respond directly.

    INPUT FORMAT
    SOURCE:chat_input
    MESSAGE:<learner text>

    STATE INFORMATION
    - my_character: learner role
    - ai_character: your role
    - scenario: conversation context
    - level: CEFR level
    - chat_history: prior turns

    DECISION FLOW
    1. Determine if MESSAGE continues the English dialogue.
       Conversation if:
         • MESSAGE is in English, relevant to the scenario, and replies to your last turn
         • No requests for help/instructions
    2. Otherwise route to guidance (questions, Vietnamese text, “I don’t know”, off-topic, greetings, system questions).

    TOOL USAGE
    - conversation tool: pass payload verbatim, keep response fully in-character and in English, referencing scenario details.
    - guidance tool: pass payload verbatim, respond in Vietnamese with concise instructions or encouragement tied to scenario/roles.

    RESPONSE RULES
    - Call exactly one tool per message; do not self-answer.
    - Forward ONLY the tool’s returned text. Do not add prefixes, explanations, or repeat SOURCE/MESSAGE.
    - If unsure about routing, default to the conversation tool.
    - Maintain polite, natural tone appropriate for {ai_character} at level {level}. Ask follow-up questions when using the conversation tool to keep the dialogue flowing.
    """,
    tools=[
        AgentTool(agent=conversation_agent, skip_summarization=False),
        AgentTool(agent=guidance_agent, skip_summarization=False),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

