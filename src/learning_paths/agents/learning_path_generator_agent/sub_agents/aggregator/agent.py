"""
Aggregator Agent with Callback for Learning Path Generation.
"""
from typing import List
import logging
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LessonRef(BaseModel):
    lesson_type: str
    index: int


class LessonAllocation(BaseModel):
    day_number: int
    title: str
    lesson_indices: List[LessonRef]


class LearningPathMatrix(BaseModel):
    daily_allocations: List[LessonAllocation]


FINAL_LEARNING_PATH_STATE_KEY = "final_learning_path"


def validate_and_adjust_lesson_counts(
    lesson_counts: dict,
    lesson_pools: dict,
    days: int,
    daily_lesson_count: int
) -> tuple[dict, int, str]:
    """Kiểm tra và điều chỉnh lesson counts"""
    warnings = []
    adjusted_counts = {}
    
    for lesson_type in ["reading", "writing", "speaking", "listening"]:
        expected = lesson_counts.get(f"{lesson_type}_count", 0)
        actual = len(lesson_pools.get(lesson_type, []))
        adjusted_counts[f"{lesson_type}_count"] = actual
        
        if actual < expected:
            warnings.append(f"{lesson_type}: expected {expected}, got {actual}")
    
    total_actual = sum(len(pool) for pool in lesson_pools.values())
    total_needed = days * daily_lesson_count
    adjusted_days = days
    
    if total_actual < total_needed:
        adjusted_days = max(1, total_actual // daily_lesson_count)
        warnings.append(
            f"Not enough lessons: have {total_actual}, need {total_needed}. "
            f"Adjusted to {adjusted_days} days."
        )
    
    return adjusted_counts, adjusted_days, "; ".join(warnings) if warnings else ""


def after_aggregator_callback(callback_context: CallbackContext) -> types.Content | None:
    """Callback xử lý mapping từ matrix sang lessons"""
    state = callback_context.state
    allocation_matrix = state.get("allocation_matrix")

    if not allocation_matrix:
        logger.error("Allocation matrix not found")
        state[FINAL_LEARNING_PATH_STATE_KEY] = None
        return None

    # Lấy lesson pools
    lesson_pools = {
        "reading": state.get("reading_output", {}).get("lessons", []),
        "writing": state.get("writing_output", {}).get("lessons", []),
        "speaking": state.get("speaking_output", {}).get("lessons", []),
        "listening": state.get("listening_output", {}).get("lessons", [])
    }

    logger.info(f"Pool sizes: {', '.join(f'{k}={len(v)}' for k, v in lesson_pools.items())}")

    # Validate & adjust
    adjusted_counts, adjusted_days, warning = validate_and_adjust_lesson_counts(
        state.get("lesson_counts", {}),
        lesson_pools,
        state.get("days", 7),
        state.get("dailyLessonCount", 2)
    )
    
    if warning:
        logger.warning(warning)
        state["generation_warning"] = warning
    
    state["adjusted_days"] = adjusted_days
    state["adjusted_lesson_counts"] = adjusted_counts

    # Map lessons
    daily_plans = []
    try:
        allocations = allocation_matrix.get("daily_allocations", [])
        allocations = [a for a in allocations if a.get("day_number") <= adjusted_days]
        
        for alloc in allocations:
            lessons = []
            for ref in alloc.get("lesson_indices", []):
                pool = lesson_pools.get(ref.get("lesson_type"), [])
                idx = ref.get("index")
                if 0 <= idx < len(pool):
                    lessons.append(pool[idx])
            
            if lessons:
                daily_plans.append({
                    "day_number": alloc.get("day_number"),
                    "title": alloc.get("title", f"Ngày {alloc.get('day_number')}"),
                    "lessons": lessons
                })

        if daily_plans:
            state[FINAL_LEARNING_PATH_STATE_KEY] = {"daily_plans": daily_plans}
            logger.info(f"Mapped {len(daily_plans)} days")
        else:
            state[FINAL_LEARNING_PATH_STATE_KEY] = None
            
    except Exception as e:
        logger.error(f"Mapping error: {e}", exc_info=True)
        state[FINAL_LEARNING_PATH_STATE_KEY] = None

    return None


aggregator_agent = LlmAgent(
    name="aggregator_agent",
    model="gemini-2.5-flash",
    description="Creates lesson allocation matrix",
    instruction="""
        You are the Learning Path Planner.

        AVAILABLE LESSONS:
        - Reading: {adjusted_lesson_counts.reading_count}
        - Writing: {adjusted_lesson_counts.writing_count}
        - Speaking: {adjusted_lesson_counts.speaking_count}
        - Listening: {adjusted_lesson_counts.listening_count}

        TARGET: {dailyLessonCount} lessons per day

        TASK: Create allocation matrix using indices 0 to N-1 for each type.

        OUTPUT FORMAT:
        {{
        "daily_allocations": [
            {{
            "day_number": 1,
            "title": "Ngày 1",
            "lesson_indices": [
                {{"lesson_type": "reading", "index": 0}},
                {{"lesson_type": "writing", "index": 0}}
            ]
            }}
        ]
        }}

        RULES:
        - Use each lesson exactly once
        - Days can have 1-{dailyLessonCount} lessons
        - Mix lesson types for variety
        """,
    output_schema=LearningPathMatrix,
    output_key="allocation_matrix",
    after_agent_callback=after_aggregator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)