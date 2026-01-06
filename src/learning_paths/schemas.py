from enum import Enum
from typing import List, Optional, Dict, Any, Union, Annotated, Literal
from pydantic import Tag
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
    title: str = Field(..., description="Title of the lesson")
    level: str = Field(...,
                       description="Level of the lesson (A1, A2, B1, B2, C1, C2)")


class LessonParamsReading(LessonParams):
    lesson_type: Literal["reading"] = "reading"
    topic: str = Field(..., description="Topic of the lesson for reading")
    genre: str = Field(..., description="Genre of the lesson for reading")
    word_count: int = Field(...,
                            description="Word count of the lesson for reading")


class LessonParamsWriting(LessonParams):
    lesson_type: Literal["writing"] = "writing"
    topic: str = Field(..., description="Topic of the lesson for writing")
    total_sentences: int = Field(...,
                                 description="Total sentences of the lesson for writing")


class LessonParamsSpeaking(LessonParams):
    lesson_type: Literal["speaking"] = "speaking"
    scenario: str = Field(...,
                          description="Scenario of the lesson for speaking")
    my_character: str = Field(...,
                              description="My character of the lesson for speaking")
    ai_character: str = Field(...,
                              description="AI character of the lesson for speaking")
    ai_gender: str = Field(...,
                           description="AI gender of the lesson for speaking (male/female)")


class LessonParamsListening(LessonParams):
    lesson_type: Literal["listening"] = "listening"
    # lesson_id là bắt buộc để hệ thống biết cần load bài nghe nào từ DB
    lesson_id: int = Field(..., description="Lesson ID for listening")


class ReadingLessons(BaseModel):
    lessons: List[LessonParamsReading]


class WritingLessons(BaseModel):
    lessons: List[LessonParamsWriting]


class SpeakingLessons(BaseModel):
    lessons: List[LessonParamsSpeaking]


class ListeningLessons(BaseModel):
    lessons: List[LessonParamsListening]


AnyLessonParams = Annotated[
    Union[
        LessonParamsReading,
        LessonParamsWriting,
        LessonParamsSpeaking,
        LessonParamsListening,
    ],
    Field(discriminator="lesson_type")
]


class DailyPlanItem(BaseModel):
    day_number: int
    title: str
    lessons: List[AnyLessonParams]


class LearningPathGenerationResult(BaseModel):
    daily_plans: List[DailyPlanItem]


class LessonWithProgressResponse(BaseModel):
    id: Optional[int] = None
    lesson_index: int
    config: AnyLessonParams
    title: str
    status: str
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


class LearningPathResponse(BaseModel):
    id: int
    user_id: int
    form_data: Dict[str, Any]
    status: str
    created_at: datetime
    warning: Optional[str] = None
    daily_plans: Optional[List[DailyLessonPlanResponse]] = None
    model_config = ConfigDict(from_attributes=True)


class LessonStartRequest(BaseModel):
    session_id: Optional[int] = Field(
        None, description="ID của phiên học từ dịch vụ kỹ năng (Reading/Speaking...)")
