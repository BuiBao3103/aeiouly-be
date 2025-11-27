"""
Chat coordination agent for the speaking practice module.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.conversation_agent.agent import conversation_agent
from .sub_agents.guidance_agent.agent import guidance_agent


chat_agent = Agent(
    name="chat",
    model="gemini-2.5-flash",
    description="Routes chat box messages to conversation or guidance tool while ensuring appropriate responses.",
    instruction="""
    You coordinate chat messages. You MUST ALWAYS call a tool first. NEVER respond directly.

    INPUT: SOURCE:chat_input, MESSAGE:<learner text>

    CONTEXT FROM STATE:
    - Scenario: "{{scenario}}"
    - AI role: {{ai_character}}
    - Learner role: {{my_character}}
    - CEFR level: {{level}}
    - Recent chat history: {{chat_history?}}
    - Last AI message: {{last_ai_message?}}

    ROUTING RULES:
    - conversation tool: Use when MESSAGE is:
      * In English
      * Relevant to the scenario "{{scenario}}"
      * Continues the dialogue naturally
      * Responds to previous messages in chat_history
      * Is a natural conversation turn
    
    - guidance tool: Use when MESSAGE is:
      * In Vietnamese
      * A question (e.g., "giờ tôi phải làm gì?", "làm thế nào?", "what should I do?")
      * Requesting help, hints, or guidance
      * Off-topic or unrelated to scenario
      * Asking to skip ("bỏ qua", "skip")
      * Expressing confusion ("không biết", "I don't know")
      * Asking about the system or instructions

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

