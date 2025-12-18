"""
Text Generation Root Agent

This module defines the root agent for text generation using a loop pattern
to ensure word count compliance (±10%).
"""

from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from typing import Optional

from .subagents.initial_text import initial_text_agent
from .subagents.text_refiner import text_refiner_agent
from .subagents.text_reviewer import text_reviewer_agent


# Create the Refinement Loop Agent
text_refinement_loop = LoopAgent(
    name="text_refinement_loop",
    max_iterations=5,  # Reduced from 10 to 5 for faster execution
    sub_agents=[
        text_reviewer_agent,  # Step 1: Review word count
        text_refiner_agent,   # Step 2: Refine text based on feedback
    ],
    description="Iteratively reviews and refines reading text until word count requirements are met (±20%)",
)

# Create the Sequential Pipeline
text_generation_agent = SequentialAgent(
    name="text_generation_agent",
    sub_agents=[
        initial_text_agent,  # Step 1: Generate initial text
        text_refinement_loop,         # Step 2: Review and refine in a loop
    ],
    description="Generates and refines English reading texts for practice based on level, genre, and topic, ensuring word count compliance (±20%)",
)

