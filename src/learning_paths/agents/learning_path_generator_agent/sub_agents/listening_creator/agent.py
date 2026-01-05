from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from src.learning_paths.schemas import LessonsResult
from typing import List, Dict, Any
from google.adk.agents.callback_context import CallbackContext


def search_listening_lessons_tool(topic: str, level: str, count: int, tool_context: ToolContext) -> List[Dict[str, Any]]:
    """Search for listening lessons from database"""
    return [{"lesson_id": 1, "title": f"Listening lesson about {topic}", "description": "Practice listening skills.", "goal": "Improve comprehension."}]


def after_listening_creator_callback(callback_context: CallbackContext) -> None:

    state = callback_context.state
    percent = state.get("status_percent", "")
    message = state.get("status_message", "")

    percent += 15
    message += "\nĐã tạo các bài học nghe."

    state["status_percent"] = percent
    state["status_message"] = message

    return None

listening_creator_agent = LlmAgent(
    name="listening_creator",
    model="gemini-2.5-flash",
    tools=[search_listening_lessons_tool],
    description="Generates personalized listening lesson configurations by searching lesson database and matching with user profile.",
    instruction="""
        You are a listening lesson designer. Generate {lesson_counts.listening_count} listening lessons in Vietnamese.

        REQUIRED OUTPUT STRUCTURE:
        Each lesson MUST contain ALL these fields:
        - lesson_type: "listening" (fixed value)
        - title: Engaging lesson title
        - description: Brief lesson summary
        - goal: Specific listening skill target
        - params: Object with REQUIRED field:
        - lesson_id: integer (unique identifier from database)

        TASK:
        1. Use search_listening_lessons_tool to find relevant lessons
        2. Match lessons to user profile below
        3. Ensure lesson_id is present for each lesson
        4. Write all content in Vietnamese

        USER PROFILE:
        - Level: {level}
        - Goals: {goals}
        - Skills: {skills}
        - Interests: {interests}
        - Profession: {profession}
        - Age Range: {ageRange}

        EXAMPLE OUTPUT:
        {{
        "title": "Nghe hiểu về công nghệ AI",
        "lesson_type": "listening",
        "description": "Luyện nghe đoạn hội thoại về ứng dụng AI trong cuộc sống",
        "goal": "Nắm được từ vựng và ý chính về công nghệ",
        "params": {{"lesson_id": 42}}
        }}

        CRITICAL: Never omit lesson_id field.
        """,
    output_schema=LessonsResult,
    output_key="listening_output",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    after_agent_callback=after_listening_creator_callback
)
