"""
Content Evaluator Agent for English Answers

This agent evaluates whether the user's English answer demonstrates understanding of the reading text.
For English answers, it coordinates parallel evaluation with grammar and then synthesizes feedback.
"""

from google.adk.agents import ParallelAgent, SequentialAgent
from .subagents.content_evaluator.agent import content_evaluator_agent
from .subagents.grammar_evaluator.agent import grammar_evaluator_agent
from .subagents.feedback_synthesizer.agent import feedback_synthesizer_agent

# Parallel agent: content + grammar evaluation
parallel_evaluator = ParallelAgent(
    name="parallel_content_grammar_evaluator_en",
    sub_agents=[content_evaluator_agent, grammar_evaluator_agent],
)

# Sequential agent: parallel evaluation -> feedback synthesis
content_evaluator_en = SequentialAgent(
    name="content_evaluator_en",
    sub_agents=[parallel_evaluator, feedback_synthesizer_agent],
)
