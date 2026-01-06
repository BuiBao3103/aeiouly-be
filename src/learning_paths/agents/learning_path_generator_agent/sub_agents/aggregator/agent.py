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
    
    # Nếu không đủ bài, vẫn giữ nguyên số ngày nhưng thêm cảnh báo lặp bài
    if total_actual < total_needed:
        warnings.append(
            f"Không đủ bài học: có {total_actual}, cần {total_needed}. "
            f"Các bài học sẽ được lặp lại để đủ {days} ngày."
        )
    
    return adjusted_counts, days, "; ".join(warnings) if warnings else ""


def after_aggregator_callback(callback_context: CallbackContext) -> types.Content | None:
    """Callback xử lý mapping từ matrix sang lessons, hỗ trợ quay vòng bài học"""
    state = callback_context.state
    allocation_matrix = state.get("allocation_matrix")

    if not allocation_matrix:
        logger.error("Allocation matrix not found")
        state[FINAL_LEARNING_PATH_STATE_KEY] = None
        return None

    # Hàm trợ giúp để lấy danh sách bài học an toàn từ state
    # (Hỗ trợ cả khi Agent trả về dict hoặc Pydantic object)
    def get_lessons_from_pool(key: str) -> list:
        output = state.get(key)
        if not output:
            return []
        # Nếu là dict (như trong log state bạn gửi)
        if isinstance(output, dict):
            return output.get("lessons", [])
        # Nếu là Pydantic object (do ADK tự động parse)
        return getattr(output, "lessons", [])

    # 1. Lấy lesson pools từ các Agent Creator trước đó
    lesson_pools = {
        "reading": get_lessons_from_pool("reading_output"),
        "writing": get_lessons_from_pool("writing_output"),
        "speaking": get_lessons_from_pool("speaking_output"),
        "listening": get_lessons_from_pool("listening_output")
    }

    logger.info(f"Pool sizes: {', '.join(f'{k}={len(v)}' for k, v in lesson_pools.items())}")

    # 2. Validate và điều chỉnh số lượng (nếu cần)
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

    # 3. Phân bổ bài học vào từng ngày theo Matrix
    daily_plans = []
    try:
        # Lấy danh sách phân bổ (hỗ trợ cả dict và object)
        allocations = allocation_matrix.get("daily_allocations", []) if isinstance(allocation_matrix, dict) else getattr(allocation_matrix, "daily_allocations", [])
        
        for alloc in allocations:
            lessons = []
            # Lấy các chỉ số bài học trong ngày (LessonRef)
            lesson_indices = alloc.get("lesson_indices", []) if isinstance(alloc, dict) else getattr(alloc, "lesson_indices", [])
            
            for ref in lesson_indices:
                l_type = ref.get("lesson_type") if isinstance(ref, dict) else getattr(ref, "lesson_type", "")
                pool = lesson_pools.get(l_type, [])
                
                if not pool:
                    continue
                
                # Quay vòng lấy bài học nếu index vượt quá kích thước pool (Modulo logic)
                idx = ref.get("index", 0) if isinstance(ref, dict) else getattr(ref, "index", 0)
                lesson_obj = pool[idx % len(pool)]
                lessons.append(lesson_obj)
            
            if lessons:
                day_num = alloc.get("day_number") if isinstance(alloc, dict) else getattr(alloc, "day_number")
                daily_plans.append({
                    "day_number": day_num,
                    "title": f"Ngày {day_num}",
                    "lessons": lessons
                })

        # 4. Lưu kết quả cuối cùng vào state
        if daily_plans:
            state[FINAL_LEARNING_PATH_STATE_KEY] = {"daily_plans": daily_plans}
            logger.info(f"Mapped {len(daily_plans)} days successfully")
        else:
            logger.error("No lessons could be mapped to daily plans")
            state[FINAL_LEARNING_PATH_STATE_KEY] = None
            
    except Exception as e:
        logger.error(f"Mapping error in aggregator callback: {e}", exc_info=True)
        state[FINAL_LEARNING_PATH_STATE_KEY] = None

    # 5. Cập nhật trạng thái tiến độ cho UI
    message = state.get("status_message", "")
    percent = 100
    message += "\nĐã phân bổ lộ trình hoàn tất."

    state["status_percent"] = percent
    state["status_message"] = message

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