from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from src.learning_paths.schemas import ListeningLessons
from typing import List, Dict, Any, List
from google.adk.agents.callback_context import CallbackContext
from src.listening.service import ListeningService

async def search_listening_lessons_tool(level: str, tool_context: ToolContext) -> List[Dict[str, Any]]:
    service = ListeningService()
    lessons = await service.get_lessons_by_level_with_fallback(level)
    return [{"lesson_id": l.id, "title": l.title, "level": l.level} for l in lessons]

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
    description="Curates personalized listening lessons from the database.",
    instruction="""
        You are an expert listening lesson curator. Your primary goal is to provide exactly {lesson_counts.listening_count} listening lessons.

        USER PROFILE:
        - Level: {level}
        - Goals: {goals}
        - Skills: {skills}
        - Interests: {interests}
        - Profession: {profession}
        - Age Range: {ageRange}

        WORKFLOW:
        1. CALL `search_listening_lessons_tool` with level="{level}".
        2. FROM the returned list, SELECT lessons that best match the USER PROFILE above.

        STRICT CONSTRAINTS:
        - QUANTITY: You MUST return exactly {lesson_counts.listening_count} lessons. This is mandatory.
        - FALLBACK STRATEGY: If the tool returns fewer than {lesson_counts.listening_count} unique lessons:
            a) Include all unique lessons provided by the tool.
            b) REPEAT lessons from the same list until you reach the total count of {lesson_counts.listening_count}.
        - SELECTION PRIORITY:
            1. Total count of {lesson_counts.listening_count}.
            2. Relevance to Interests ({interests}) and Profession ({profession}).
            3. Closeness to Level ({level}).

        OUTPUT STRUCTURE:
        Return a JSON object with a "lessons" key. Each item must have:
        - title: String (from tool)
        - level: String (from tool)
        - lesson_id: Integer (from tool)

        CRITICAL: Never omit the lesson_id field. Always ensure exactly {lesson_counts.listening_count} items in the output list.
        """,
    output_schema=ListeningLessons,
    output_key="listening_output",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    after_agent_callback=after_listening_creator_callback
)
