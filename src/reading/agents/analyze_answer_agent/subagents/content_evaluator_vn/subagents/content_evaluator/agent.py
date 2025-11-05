"""
Content Evaluator Agent for Vietnamese Answers

This agent evaluates whether the user's Vietnamese answer demonstrates understanding of the reading text.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from ....content_evaluator.agent import ContentEvaluationRequest, ContentEvaluationResult, content_evaluator_agent as base_content_evaluator

content_evaluator_agent = LlmAgent(
    name="content_evaluator_vn_agent",
    model="gemini-2.0-flash",
    description="Evaluates content for Vietnamese answers",
    instruction=base_content_evaluator.instruction,
    output_schema=ContentEvaluationResult,
    output_key="content_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

