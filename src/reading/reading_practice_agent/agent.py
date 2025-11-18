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
    model="gemini-2.0-flash",
    description="Coordinates the reading practice workflow, delegating work to specialized tools.",
    instruction="""
    You orchestrate the reading practice module. Analyze each request and select the correct tool.
    When you speak to the user, respond in natural, supportive Vietnamese or English as appropriate.

    INPUT FORMAT:
    - Every message arrives as two lines:
      SOURCE:<origin>
      MESSAGE:<raw content>
    - SOURCE indicates which action triggered the request (button vs. API call).

    SUPPORTED SOURCE VALUES:
    - generate_text: Generate a new reading text.
    - analyze_text: Analyze a custom text to determine level, genre, and topic.
    - generate_quiz: Generate quiz questions from reading text.
    - generate_discussion: Generate discussion questions from reading text.
    - analyze_discussion_answer: Evaluate a user's answer to a discussion question.

    SUB-AGENT USAGE RULES:
    1. text_generation sub-agent:
       - Trigger: SOURCE == generate_text
       - Transfer to text_generation sub-agent with MESSAGE containing the generation parameters (level, genre, topic, word_count).
       - The sub-agent will generate the text silently and store it. No user-facing response is needed.

    2. text_analysis sub-agent:
       - Trigger: SOURCE == analyze_text
       - Transfer to text_analysis sub-agent with MESSAGE containing the text to analyze.
       - After receiving sub-agent output, return the analysis result (level, genre, topic).

    3. quiz_generation sub-agent:
       - Trigger: SOURCE == generate_quiz
       - Transfer to quiz_generation sub-agent with MESSAGE containing the reading text and number of questions.
       - After receiving sub-agent output, return the quiz questions.

    4. discussion_generation sub-agent:
       - Trigger: SOURCE == generate_discussion
       - Transfer to discussion_generation sub-agent with MESSAGE containing the reading text and number of questions.
       - After receiving sub-agent output, return the discussion questions.

    5. analyze_discussion_answer sub-agent:
       - Trigger: SOURCE == analyze_discussion_answer
       - Transfer to analyze_discussion_answer sub-agent.
       - This sub-agent handles routing based on answer language (Vietnamese or English).
       - Pass the full two-line payload exactly as received (both SOURCE and MESSAGE lines).

    STATE INFORMATION AVAILABLE:
    - level: CEFR difficulty level.
    - genre: Reading genre.
    - topic: Practice topic.
    - content: Reading text content.

    IMPORTANT:
    - Always transfer to sub-agents; do not craft answers without sub-agent output.
    - Study SOURCE and MESSAGE carefully before choosing a sub-agent.
    - For generate_text: Transfer to text_generation sub-agent and do NOT generate any response text. The text generation is handled silently.
    - For other sources: After receiving sub-agent output, format and return the result appropriately.
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

