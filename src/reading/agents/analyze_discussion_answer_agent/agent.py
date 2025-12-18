"""
Analyze Discussion Answer Agent

This agent coordinates the answer evaluation workflow using a sequential flow:
1. Parallel evaluation (content + grammar)
2. Feedback synthesis
"""
from google.adk.agents import SequentialAgent, ParallelAgent

from .sub_agents.content_evaluator.agent import content_evaluator_agent
from .sub_agents.grammar_evaluator.agent import grammar_evaluator_agent
from .sub_agents.feedback_synthesizer.agent import feedback_synthesizer_agent

# Parallel agent: content + grammar evaluation
parallel_evaluator = ParallelAgent(
    name="parallel_content_grammar_evaluator",
    sub_agents=[content_evaluator_agent, grammar_evaluator_agent],
)

# Sequential agent: parallel evaluation -> feedback synthesis
analyze_discussion_answer_agent = SequentialAgent(
    name="analyze_discussion_answer",
    sub_agents=[parallel_evaluator, feedback_synthesizer_agent],
)

