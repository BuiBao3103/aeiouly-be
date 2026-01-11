"""
Aggregator Agent - Optimized Matrix Design
Agent focuses on distribution strategy, Python handles index allocation
"""
import random
import logging
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Dict

logger = logging.getLogger(__name__)

FINAL_LEARNING_PATH_STATE_KEY = "final_learning_path"


class DailySkillPattern(BaseModel):
    """Agent chỉ chọn skill types, không chọn index"""
    day_number: int = Field(ge=1)
    skill_types: List[str] = Field(
        description="List of skill types for this day",
        min_length=1
    )


class SkillAllocationStrategy(BaseModel):
    """Agent output: High-level strategy only"""
    daily_patterns: List[DailySkillPattern] = Field(
        description="Skill types for each day"
    )
    variety_strategy: str = Field(
        description="How to select lessons within each skill type",
        default="sequential_with_shuffle"
    )


def allocate_lessons_smart(
    daily_patterns: List[Dict],
    lesson_pools: Dict[str, List],
    variety_strategy: str
) -> List[Dict]:
    """
    Python allocates specific lesson indices based on agent's skill pattern
    
    Args:
        daily_patterns: [{"day_number": 1, "skill_types": ["reading", "speaking"]}, ...]
        lesson_pools: {"reading": [...], "writing": [...], ...}
        variety_strategy: "sequential_with_shuffle" | "random" | "priority_first"
    
    Returns:
        Daily plans with actual lesson objects
    """
    
    # Prepare shuffled indices for each pool
    pool_indices = {}
    for skill_type, pool in lesson_pools.items():
        if not pool:
            pool_indices[skill_type] = []
            continue
            
        indices = list(range(len(pool)))
        
        if variety_strategy == "sequential_with_shuffle":
            random.shuffle(indices)
        elif variety_strategy == "random":
            # Will pick randomly each time
            pass
        elif variety_strategy == "priority_first":
            # Keep original order (assumes creator already sorted by priority)
            pass
        
        pool_indices[skill_type] = indices
    
    # Track usage
    pool_counters = {k: 0 for k in lesson_pools.keys()}
    used_lesson_ids = {k: set() for k in lesson_pools.keys()}
    
    daily_plans = []
    
    for pattern in daily_patterns:
        day_number = pattern.get("day_number") if isinstance(pattern, dict) else getattr(pattern, "day_number")
        skill_types = pattern.get("skill_types") if isinstance(pattern, dict) else getattr(pattern, "skill_types")
        
        day_lessons = []
        
        for skill_type in skill_types:
            pool = lesson_pools.get(skill_type, [])
            if not pool:
                logger.warning(f"No {skill_type} lessons available")
                continue
            
            # Get next lesson from this pool
            if variety_strategy == "random":
                # Random selection
                available = [i for i in range(len(pool)) 
                           if (pool[i].get("lesson_id") if isinstance(pool[i], dict) 
                               else getattr(pool[i], "lesson_id", None)) 
                           not in used_lesson_ids[skill_type]]
                
                if available:
                    idx = random.choice(available)
                else:
                    idx = pool_counters[skill_type] % len(pool)
            else:
                # Sequential (with or without shuffle)
                idx_in_shuffled = pool_counters[skill_type] % len(pool_indices[skill_type])
                idx = pool_indices[skill_type][idx_in_shuffled]
            
            lesson = pool[idx]
            lesson_id = (lesson.get("lesson_id") if isinstance(lesson, dict) 
                        else getattr(lesson, "lesson_id", None))
            
            if lesson_id:
                used_lesson_ids[skill_type].add(lesson_id)
            
            day_lessons.append(lesson)
            pool_counters[skill_type] += 1
        
        if day_lessons:
            daily_plans.append({
                "day_number": day_number,
                "title": f"Ngay {day_number}",
                "lessons": day_lessons
            })
    
    return daily_plans


def after_aggregator_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    Callback: Convert agent's skill patterns to actual lessons
    """
    state = callback_context.state
    allocation_strategy = state.get("allocation_matrix")

    if not allocation_strategy:
        logger.error("Allocation strategy not found")
        state[FINAL_LEARNING_PATH_STATE_KEY] = None
        return None

    # Get lesson pools
    def get_pool(key: str) -> list:
        output = state.get(key)
        if not output:
            return []
        if isinstance(output, dict):
            return output.get("lessons", [])
        return getattr(output, "lessons", [])

    lesson_pools = {
        "reading": get_pool("reading_output"),
        "writing": get_pool("writing_output"),
        "speaking": get_pool("speaking_output"),
        "listening": get_pool("listening_output")
    }

    logger.info(f"Pool sizes: {', '.join(f'{k}={len(v)}' for k, v in lesson_pools.items())}")

    # Extract strategy
    daily_patterns = (allocation_strategy.get("daily_patterns", []) 
                     if isinstance(allocation_strategy, dict) 
                     else getattr(allocation_strategy, "daily_patterns", []))
    
    variety_strategy = (allocation_strategy.get("variety_strategy", "sequential_with_shuffle")
                       if isinstance(allocation_strategy, dict)
                       else getattr(allocation_strategy, "variety_strategy", "sequential_with_shuffle"))

    # Validate patterns match lesson_counts
    lesson_counts = state.get("lesson_counts")
    if lesson_counts:
        expected_counts = {
            "reading": (lesson_counts.get("reading_count") if isinstance(lesson_counts, dict)
                       else getattr(lesson_counts, "reading_count", 0)),
            "writing": (lesson_counts.get("writing_count") if isinstance(lesson_counts, dict)
                       else getattr(lesson_counts, "writing_count", 0)),
            "speaking": (lesson_counts.get("speaking_count") if isinstance(lesson_counts, dict)
                        else getattr(lesson_counts, "speaking_count", 0)),
            "listening": (lesson_counts.get("listening_count") if isinstance(lesson_counts, dict)
                         else getattr(lesson_counts, "listening_count", 0)),
        }
        
        # Count skill occurrences in patterns
        actual_counts = {"reading": 0, "writing": 0, "speaking": 0, "listening": 0}
        for pattern in daily_patterns:
            skills = (pattern.get("skill_types") if isinstance(pattern, dict) 
                     else getattr(pattern, "skill_types"))
            for skill in skills:
                if skill in actual_counts:
                    actual_counts[skill] += 1
        
        # Validate
        mismatches = []
        for skill in ["reading", "writing", "speaking", "listening"]:
            if actual_counts[skill] != expected_counts[skill]:
                mismatches.append(f"{skill}: expected {expected_counts[skill]}, got {actual_counts[skill]}")
        
        if mismatches:
            logger.error(f"Pattern validation failed: {'; '.join(mismatches)}")
            state[FINAL_LEARNING_PATH_STATE_KEY] = None
            state["status_message"] = state.get("status_message", "") + "\nLoi: Phan bo khong khop voi ke hoach."
            return None

    # Allocate lessons using smart algorithm
    try:
        daily_plans = allocate_lessons_smart(
            daily_patterns=daily_patterns,
            lesson_pools=lesson_pools,
            variety_strategy=variety_strategy
        )

        if daily_plans:
            state[FINAL_LEARNING_PATH_STATE_KEY] = {"daily_plans": daily_plans}
            logger.info(f"Successfully mapped {len(daily_plans)} days")
        else:
            logger.error("No daily plans generated")
            state[FINAL_LEARNING_PATH_STATE_KEY] = None
            
    except Exception as e:
        logger.error(f"Mapping error: {e}", exc_info=True)
        state[FINAL_LEARNING_PATH_STATE_KEY] = None

    state["status_percent"] = 100
    state["status_message"] = state.get("status_message", "") + "\nĐã phân bổ lộ trình hoàn tất."

    return None


aggregator_agent = LlmAgent(
    name="aggregator_agent",
    model="gemini-2.5-flash",
    description="Creates skill distribution pattern for learning path",
    instruction="""
        You are the Learning Path Strategist.

        AVAILABLE LESSONS (from planner):
        - Reading: {lesson_counts.reading_count}
        - Writing: {lesson_counts.writing_count}
        - Speaking: {lesson_counts.speaking_count}
        - Listening: {lesson_counts.listening_count}

        USER PROFILE:
        - Level: {level}
        - Goals: {goals}
        - Priority Skills: {skills}
        - Days: {days}
        - Lessons per day: {dailyLessonCount}

        TASK: Create a skill distribution pattern (NOT specific lesson indices)

        RULES:
        1. Total skill occurrences MUST match lesson_counts exactly:
           - "reading" appears {lesson_counts.reading_count} times across all days
           - "writing" appears {lesson_counts.writing_count} times
           - "speaking" appears {lesson_counts.speaking_count} times
           - "listening" appears {lesson_counts.listening_count} times
        
        2. Each day should have {dailyLessonCount} skill types (can repeat)
        
        3. Optimize for variety:
           - Avoid same skill 3+ consecutive days
           - Mix input (reading/listening) with output (speaking/writing)
           - Prioritize skills from {skills}

        OUTPUT FORMAT:
        {{
          "daily_patterns": [
            {{"day_number": 1, "skill_types": ["reading", "speaking"]}},
            {{"day_number": 2, "skill_types": ["listening", "writing"]}}
          ],
          "variety_strategy": "sequential_with_shuffle"
        }}

        variety_strategy options:
        - "sequential_with_shuffle": Shuffle lessons within each skill, then use sequentially
        - "random": Random selection each time
        - "priority_first": Use lessons in original order (assumes pre-sorted)

        VERIFICATION:
        - Count total "reading" in all skill_types = {lesson_counts.reading_count}? 
        - Count total "writing" = {lesson_counts.writing_count}?
        - Count total "speaking" = {lesson_counts.speaking_count}?
        - Count total "listening" = {lesson_counts.listening_count}?
        - If any mismatch, recalculate!

        CRITICAL: Only specify skill type names. Python will handle lesson selection.
        """,
    output_schema=SkillAllocationStrategy,
    output_key="allocation_matrix",
    after_agent_callback=after_aggregator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)