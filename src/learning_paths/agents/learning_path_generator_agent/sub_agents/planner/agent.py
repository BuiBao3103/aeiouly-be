from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, Field


class LessonPlanCounts(BaseModel):
    reading_count: int = Field(..., description="Number of reading lessons")
    writing_count: int = Field(..., description="Number of writing lessons")
    speaking_count: int = Field(..., description="Number of speaking lessons")
    listening_count: int = Field(...,
                                 description="Number of listening lessons")


def after_planner_callback(callback_context: CallbackContext) -> None:

    state = callback_context.state
    percent = state.get("status_percent", "")
    message = state.get("status_message", "")

    percent += 10
    message += "\nĐã lên kế hoạch lộ trình"

    state["status_percent"] = percent
    state["status_message"] = message

    return None


planner_agent = LlmAgent(
    name="planner_agent",
    model="gemini-2.5-flash-lite",
    description="Allocates lesson counts per skill based on user priorities and profile.",
    instruction="""
    You are an expert educational planner. 
    Your goal is to allocate the provided `{total_lessons}` total count across Reading, Writing, Speaking, and Listening skills.
    
    RULES:
    1. The sum of (reading_count + writing_count + speaking_count + listening_count) MUST exactly equal `{total_lessons}`.
    2. Prioritize skills listed in `{skills}` (assign them higher counts).
    3. Ensure the distribution allows for variety throughout the learning path duration.

    USER PROFILE FOR PERSONALIZATION:
    - Current English Level: {level}
    - Learning Goals: {goals}
    - Prioritized Skills: {skills}
    - Interests: {interests}
    - Profession: {profession}
    - Age Range: {ageRange}
    
    INPUT DATA:
    - Total lessons to allocate: {total_lessons}
    """,
    output_schema=LessonPlanCounts,
    output_key="lesson_counts",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    after_agent_callback=after_planner_callback
)
