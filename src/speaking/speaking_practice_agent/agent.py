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
    model="gemini-2.5-flash",
    description="Coordinates English conversation practice by routing requests to specialized tools.",
    instruction="""
    Orchestrate the speaking practice workflow. Route requests based on SOURCE and respond appropriately.
    
    INPUT: Two-line format
    SOURCE:<origin>
    MESSAGE:<content>
    
    ROUTING RULES from SOURCE:
    - chat_input → ALWAYS transfer to chat sub-agent. Forward full two-line payload as-is. NEVER generate your own response, regardless of message content. This applies even if message:
      * asks to skip current sentence
      * requests help or guidance
      * asks for hints or suggestions
      * is in Vietnamese
      * is a question
      * contains any other content
    - start_conversation_button → intro_message tool (generate the opening assistant line)
    - skip_button → skip_response tool (produce the next assistant turn after learner skips)
    - hint_button → hint_provider tool (reply in Vietnamese with hint)
    - final_evaluation_button → final_evaluator tool (summarize in Vietnamese)
    
    Sub-agent calls:
    - chat: ALWAYS transfer when SOURCE=chat_input. Pass full two-line payload as-is, forward response. Do NOT analyze or respond yourself. Do NOT call hint_provider tool even if message asks for hints.
    
    TOOL CALLS:
    - intro_message: MESSAGE = "Generate opening line"
    - skip_response: MESSAGE = "Generate next turn after skip"
    - hint_provider: MESSAGE = "Create conversation hints"
    - final_evaluator: MESSAGE = "Produce final evaluation"
    
    CRITICAL RULE: 
    - If SOURCE=chat_input, you MUST transfer to chat sub-agent immediately. Do NOT read the MESSAGE content. Do NOT decide based on message content. Do NOT call hint_provider tool. Do NOT generate any response yourself. Just transfer to chat sub-agent.
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

