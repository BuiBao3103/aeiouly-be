from google.adk.agents import SequentialAgent, ParallelAgent
from .sub_agents.planner import planner_agent
from .sub_agents.reading_creator import reading_creator_agent
from .sub_agents.writing_creator import writing_creator_agent
from .sub_agents.speaking_creator import speaking_creator_agent
from .sub_agents.listening_creator import listening_creator_agent
from .sub_agents.aggregator import aggregator_agent

# Phase 2: Parallel content generation for each skill
parallel_creators = ParallelAgent(
    name="content_generation_step",
    sub_agents=[reading_creator_agent, writing_creator_agent, speaking_creator_agent]
    # sub_agents=[reading_creator_agent, writing_creator_agent, speaking_creator_agent, listening_creator_agent]
)

# Main pipeline: Sequential flow of planning -> parallel creation -> aggregation
learning_path_generator_agent = SequentialAgent(
    name="learning_path_pipeline",
    sub_agents=[
        planner_agent,      # Phase 1: Determine lesson counts per skill
        parallel_creators,  # Phase 2: Generate content for all skills in parallel
        aggregator_agent    # Phase 3: Aggregate and randomize lessons into daily plans, then save to DB
    ]
)
