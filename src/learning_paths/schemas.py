from enum import Enum
from turtle import title
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from src.constants.cefr import CEFRLevel



class EnglishGoal(str, Enum):
    DAILY_COMMUNICATION = "daily_communication"
    WORK = "work"
    TRAVEL = "travel"
    STUDY_EXAM = "study_exam"
    CERTIFICATE = "certificate"
    IMMIGRATION = "immigration"
    PERSONAL_INTEREST = "personal_interest"


class LearningPathForm(BaseModel):
    goals: List[EnglishGoal] = Field(..., min_items=1)
    level: CEFRLevel
    skills: List[str] = Field(..., min_items=1)
    interests: List[str] = Field(..., min_items=1)
    ageRange: str
    profession: str
    dailyLessonCount: int = Field(..., ge=1, le=4)
    planDuration: str


class LessonParams(BaseModel):
    lesson_type: str = Field(..., description="Type of the lesson")
    title: str = Field(..., description="Title of the lesson")
    topic: Optional[str] = Field(None, description="Topic of the lesson")
    level: Optional[str] = Field(None, description="Level of the lesson")
    genre: Optional[str] = Field(None, description="Genre of the lesson")
    word_count: Optional[int] = Field(None,
                                      description="Word count of the lesson")
    total_sentences: Optional[int] = Field(None,
                                           description="Total sentences of the lesson")
    scenario: Optional[str] = Field(None, description="Scenario of the lesson")
    my_character: Optional[str] = Field(None,
                                        description="My character of the lesson")
    ai_character: Optional[str] = Field(None,
                                        description="AI character of the lesson")
    ai_gender: Optional[str] = Field(None,
                                     description="AI gender of the lesson")
    lesson_id: Optional[int] = Field(None, description="Lesson ID")


class LessonsResult(BaseModel):
    lessons: List[LessonParams] = Field(..., description="List of lessons")


class DailyLessonContent(BaseModel):

    day_number: int
    lessons: List[LessonParams]


class LearningPathGenerationResult(BaseModel):
    daily_plans: List[DailyLessonContent]


class LessonWithProgressResponse(BaseModel):
    id: Optional[int] = None  # ID của UserLessonProgress
    lesson_index: int
    config: LessonParams
    title: str
    status: str  # 'start', 'in_progress', 'done'
    session_id: Optional[int] = None


class DailyLessonPlanResponse(BaseModel):
    id: int
    day_number: int
    status: str
    lessons: List[LessonWithProgressResponse]  # Danh sách bài học kèm tiến độ
    model_config = ConfigDict(from_attributes=True)


class UserLessonProgressResponse(BaseModel):
    id: int
    daily_lesson_plan_id: int
    lesson_index: int
    session_id: Optional[int] = None
    status: str
    metadata_: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LessonStatusUpdateRequest(BaseModel):
    status: str
    session_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class LearningPathResponse(BaseModel):
    id: int
    user_id: int
    form_data: Dict[str, Any]
    status: str
    created_at: datetime
    warning: Optional[str] = None
    daily_plans: Optional[List[DailyLessonPlanResponse]] = None
    model_config = ConfigDict(from_attributes=True)
