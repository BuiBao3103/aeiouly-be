"""
Chat coordination agent for the speaking practice module.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.conversation_agent.agent import conversation_agent
from .sub_agents.guidance_agent.agent import guidance_agent


chat_agent = Agent(
    name="chat",
    model="gemini-2.5-flash-lite",
    description="Routes chat messages to conversation or guidance tool.",
    instruction="""
    Route MESSAGE to one tool. NEVER respond directly.

    INPUT: SOURCE:chat_input, MESSAGE:<learner text>
    CONTEXT: Scenario="{scenario}", AI={ai_character}, Learner={my_character}, Level={level}, History={chat_history?}, Last AI={last_ai_message?}

    ROUTING RULES:
    - conversation tool: Use when MESSAGE is:
      * In English
      * Relevant to scenario "{scenario}"
      * Continues dialogue naturally
      * Responds to previous messages
      * Is a natural conversation turn
    
    - guidance tool: Use when MESSAGE is:
      * In Vietnamese
      * A question (e.g., "giờ tôi phải làm gì?", "làm thế nào?", "what should I do?")
      * Requesting help, hints, or guidance
      * Off-topic or unrelated to scenario
      * Asking to skip ("bỏ qua", "skip")
      * Expressing confusion ("không biết", "I don't know")
      * Asking about system or instructions

    RULES:
    - Call exactly one tool per message. Pass MESSAGE verbatim.
    - Forward ONLY the tool's response. Do not add anything.
    - If unsure, default to conversation tool.
    - You are ONLY a router. Never generate responses yourself.
    """,
    tools=[
        AgentTool(agent=conversation_agent, skip_summarization=True),
        AgentTool(agent=guidance_agent, skip_summarization=True),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

