from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from src.models import CustomModel
from src.listening.models import CEFRLevel, SessionStatus

# Lesson schemas
class LessonCreate(CustomModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề bài học")
    youtube_url: str = Field(..., min_length=1, max_length=500, description="URL YouTube")

class LessonUpload(CustomModel):
    lesson_data: LessonCreate
    srt_content: str = Field(..., description="Nội dung file SRT")

class LessonUpdate(CustomModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Tiêu đề bài học")
    youtube_url: Optional[str] = Field(None, min_length=1, max_length=500, description="URL YouTube")
    level: Optional[str] = Field(None, description="Độ khó theo thang CEFR")

class SentenceResponse(CustomModel):
    id: int
    lesson_id: int
    index: int
    text: str
    translation: Optional[str] = None
    start_time: float
    end_time: float
    normalized_text: Optional[str] = None

class LessonResponse(CustomModel):
    id: int
    title: str
    youtube_url: str
    level: CEFRLevel
    total_sentences: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class LessonDetailResponse(CustomModel):
    id: int
    title: str
    youtube_url: str
    level: CEFRLevel
    total_sentences: int
    sentences: List[SentenceResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None

# Session schemas
class SessionCreate(CustomModel):
    lesson_id: int = Field(..., description="ID bài học")

class SessionResponse(CustomModel):
    id: int
    user_id: int
    lesson_id: int
    current_sentence_index: int
    status: SessionStatus
    attempts: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class SessionDetailResponse(CustomModel):
    id: int
    user_id: int
    lesson_id: int
    current_sentence_index: int
    status: SessionStatus
    attempts: int
    lesson: LessonResponse
    current_sentence: Optional[SentenceResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

# Progress schemas
class ProgressSubmit(CustomModel):
    is_correct: bool = Field(..., description="Trả lời đúng hay sai")
    attempts: int = Field(..., ge=1, description="Số lần thử")
    hints_used: int = Field(0, ge=0, description="Số gợi ý đã dùng")
    skipped: bool = Field(False, description="Có bỏ qua câu này không")
    time_spent: float = Field(..., ge=0, description="Thời gian làm câu (giây)")

class ProgressStats(CustomModel):
    total_sentences: int
    completed_sentences: int
    correct_answers: int
    total_attempts: int
    total_hints_used: int
    total_time_spent: float
    accuracy: float
    average_time_per_sentence: float

class SessionCompleteResponse(CustomModel):
    session_id: int
    lesson_id: int
    completed_at: datetime
    stats: ProgressStats
    overall_score: float = Field(..., ge=0, le=100, description="Điểm tổng thể")

# Filter schemas
class LessonFilter(CustomModel):
    level: Optional[CEFRLevel] = None
    search: Optional[str] = None

class UserSessionResponse(CustomModel):
    """Response schema for user's sessions list"""
    id: int
    lesson_id: int
    current_sentence_index: int
    status: SessionStatus
    attempts: int
    lesson: LessonResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
