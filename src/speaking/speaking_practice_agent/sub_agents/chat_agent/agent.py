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
    You coordinate chat messages. You MUST ALWAYS call a tool first. NEVER respond directly.

    INPUT: SOURCE:chat_input, MESSAGE:<learner text>

    ROUTING:
    - conversation tool: MESSAGE is in English, relevant to scenario, continues dialogue
    - guidance tool: MESSAGE is in Vietnamese, questions, "I don't know", off-topic, or needs help

    RULES:
    - Call exactly one tool per message. Pass MESSAGE verbatim.
    - Forward ONLY the tool's response. Do not add anything.
    - If unsure, default to conversation tool.
    - You are ONLY a router. Never generate responses yourself.

    STATE: my_character, ai_character, ai_gender, scenario, level, chat_history
    """,
    tools=[
        AgentTool(agent=conversation_agent, skip_summarization=True),
        AgentTool(agent=guidance_agent, skip_summarization=True),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

