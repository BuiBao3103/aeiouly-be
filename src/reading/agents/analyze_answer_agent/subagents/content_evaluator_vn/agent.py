"""
Content Evaluator Agent for Vietnamese Answers

This agent evaluates whether the user's Vietnamese answer demonstrates understanding of the reading text.
For Vietnamese answers, it evaluates content and then synthesizes feedback.
"""

from google.adk.agents import SequentialAgent
from .subagents.content_evaluator.agent import content_evaluator_agent
from .subagents.feedback_synthesizer.agent import feedback_synthesizer_agent

# Sequential agent: content evaluation -> feedback synthesis
content_evaluator_vn = SequentialAgent(
    name="content_evaluator_vn",
    sub_agents=[content_evaluator_agent, feedback_synthesizer_agent],
)
