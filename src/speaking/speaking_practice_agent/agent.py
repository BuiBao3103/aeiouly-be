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
    model="gemini-2.0-flash",
    description="Coordinates English conversation practice by routing requests to specialized tools.",
    instruction="""
    Orchestrate the speaking practice workflow. Route requests based on SOURCE and respond appropriately.
    
    INPUT: Two-line format
    SOURCE:<origin>
    MESSAGE:<content>
    
    ROUTING RULES from SOURCE:
    - chat_input → chat tool (forward full payload, don't generate own response)
    - start_conversation_button → intro_message tool (generate the opening assistant line)
    - skip_button → skip_response tool (produce the next assistant turn after learner skips)
    - hint_button → hint_provider tool (reply in Vietnamese with hint)
    - final_evaluation_button → final_evaluator tool (summarize in Vietnamese)
    
    TOOL CALLS:
    - chat: Pass full two-line payload as-is, forward response
    - intro_message: MESSAGE = "Generate opening line"
    - skip_response: MESSAGE = "Generate next turn after skip"
    - hint_provider: MESSAGE = "Create conversation hints"
    - final_evaluator: MESSAGE = "Produce final evaluation"
    
    CRITICAL: For chat_input, call chat tool immediately without generating your own response.
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

