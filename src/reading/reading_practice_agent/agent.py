"""
Reading Practice Coordinator Agent

Acts as the primary orchestrator that delegates work to specialized sub-agents
for reading practice workflow.
"""
from google.adk.agents import Agent
from typing import Dict, Any
from google.adk.tools import AgentTool

from .sub_agents.text_generation_agent.agent import text_generation_agent
from .sub_agents.text_analysis_agent.agent import text_analysis_agent
from .sub_agents.quiz_generation_agent.agent import quiz_generation_agent
from .sub_agents.discussion_generation_agent.agent import discussion_generation_agent
from .sub_agents.analyze_discussion_answer_agent.agent import analyze_discussion_answer_agent


reading_practice = Agent(
    name="reading_practice",
    model="gemini-2.5-flash-lite",
    description="Coordinates the reading practice workflow, delegating work to specialized tools.",
    instruction="""
    You orchestrate the reading practice module. Your job is to route each request to the correct sub-agent/tool.

    INPUT:
    - Always exactly two lines:
      SOURCE:<origin>
      MESSAGE:<raw content>

    SUPPORTED SOURCE VALUES:
    - generate_text → generate a new reading text.
    - analyze_text → analyze a custom text to determine level, genre, topic.
    - generate_quiz → generate quiz questions from the reading text.
    - generate_discussion → generate discussion questions from the reading text.
    - analyze_discussion_answer → evaluate a user's answer to a discussion question.

    ROUTING RULES:
    - SOURCE == generate_text → call text_generation tool. Let the sub-agent write text into state; do NOT generate any natural-language reply.
    - SOURCE == analyze_text → call text_analysis tool, then return the structured analysis (level, genre, topic) from sub-agent.
    - SOURCE == generate_quiz → call quiz_generation tool, then return the quiz questions from sub-agent.
    - SOURCE == generate_discussion → call discussion_generation tool, then return the discussion questions from sub-agent.
    - SOURCE == analyze_discussion_answer → transfer to analyze_discussion_answer sub-agent with the full original two-line payload.

    STATE AVAILABLE:
    - level, genre, topic, content (reading text and metadata).

    IMPORTANT:
    - Always use sub-agents/tools for real work; do not invent JSON structures yourself.
    - For generate_text, respond only via state updates (no direct answer needed).
    - For other sources, surface exactly the structured output produced by the sub-agents.
    """,
    sub_agents=[
        analyze_discussion_answer_agent,
    ],
    tools=[
        AgentTool(agent=text_generation_agent, skip_summarization=False),
        AgentTool(agent=text_analysis_agent, skip_summarization=False),
        AgentTool(agent=quiz_generation_agent, skip_summarization=False),
        AgentTool(agent=discussion_generation_agent, skip_summarization=False),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

