"""
Listening Lesson Coordinator Agent.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.determine_level_agent.agent import determine_level_agent
from .sub_agents.translation_agent.agent import translation_agent


listening_lesson_agent = Agent(
    name="listening_lesson",
    model="gemini-2.0-flash",
    description="Coordinates listening lesson workflows and routes requests to specialized tools.",
    instruction="""
    You orchestrate listening lesson tasks. Every input arrives as two lines:
    
    SOURCE:<command>
    MESSAGE:<payload>
    
    ROUTING RULES:
    - SOURCE:determine_level → call determine_level tool (forward MESSAGE verbatim)
    - SOURCE:translate_sentences → call translation_agent tool (forward MESSAGE verbatim)
    
    BEHAVIOR:
    - Always call the appropriate tool. Never respond directly.
    - Forward MESSAGE exactly so the tool has full context.
    - Do not summarize or modify tool responses.
    """,
    tools=[
        AgentTool(agent=determine_level_agent, skip_summarization=True),
        AgentTool(agent=translation_agent, skip_summarization=True),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


