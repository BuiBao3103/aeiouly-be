"""
Speaking Practice Coordinator Agent for English conversation practice.

Acts as the primary orchestrator that routes requests to specialized agents
for conversation management, hint generation, and session completion.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.chat_agent.agent import chat_agent
from .sub_agents.hint_provider_agent.agent import hint_provider_agent
from .sub_agents.final_evaluator_agent.agent import final_evaluator_agent
from .sub_agents.intro_message_agent.agent import intro_message_agent
from .sub_agents.skip_response_agent.agent import skip_response_agent


speaking_practice = Agent(
    name="speaking_practice",
    model="gemini-2.5-flash-lite",
    description="Routes speaking practice requests to specialized tools.",
    instruction="""
    Route requests by SOURCE only. Do NOT analyze MESSAGE content.
    
    INPUT: SOURCE:<origin>\nMESSAGE:<content>
    
    ROUTING:
    - SOURCE=chat_input → transfer to chat sub-agent (forward payload as-is)
    - SOURCE=start_conversation_button → intro_message tool
    - SOURCE=skip_button → skip_response tool
    - SOURCE=hint_button → hint_provider tool
    - SOURCE=final_evaluation_button → final_evaluator tool
    
    CRITICAL: For chat_input, transfer immediately. Do NOT read MESSAGE. Do NOT call tools.
    """,
    tools=[
        AgentTool(agent=intro_message_agent, skip_summarization=True),
        AgentTool(agent=skip_response_agent, skip_summarization=True),
        AgentTool(agent=hint_provider_agent, skip_summarization=True),
        AgentTool(agent=final_evaluator_agent, skip_summarization=True),
    ],
    sub_agents=[chat_agent],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

