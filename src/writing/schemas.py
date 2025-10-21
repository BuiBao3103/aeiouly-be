from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from src.models import CustomModel
from src.writing.models import CEFRLevel, SessionStatus

class WritingSessionCreate(CustomModel):
    topic: str = Field(..., min_length=1, max_length=255, description="Chủ đề luyện viết")
    difficulty: CEFRLevel = Field(..., description="Độ khó theo thang CEFR")
    total_sentences: int = Field(..., ge=1, le=20, description="Số câu cần dịch")

class WritingSessionResponse(CustomModel):
    id: int
    user_id: int
    topic: str
    difficulty: CEFRLevel
    total_sentences: int
    current_sentence_index: int
    status: SessionStatus
    vietnamese_text: str
    vietnamese_sentences: List[str]  # Array of sentences
    current_sentence: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class WritingSessionListResponse(CustomModel):
    id: int
    topic: str
    difficulty: CEFRLevel
    total_sentences: int
    current_sentence_index: int
    status: SessionStatus
    created_at: datetime

class ChatMessageCreate(CustomModel):
    content: str = Field(..., min_length=1, description="Nội dung tin nhắn")

class ChatMessageResponse(CustomModel):
    id: int
    session_id: int
    role: str
    content: str
    sentence_index: Optional[int] = None
    status: SessionStatus
    created_at: datetime

class HintResponse(CustomModel):
    hint: str = Field(..., description="Gợi ý dịch cho câu hiện tại")
    sentence_index: int = Field(..., description="Chỉ số câu hiện tại")

class FinalEvaluationResponse(CustomModel):
    session_id: int
    total_sentences: int
    completed_sentences: int
    overall_score: float = Field(..., ge=0, le=100, description="Điểm tổng thể")
    accuracy_score: float = Field(..., ge=0, le=100, description="Điểm chính xác")
    fluency_score: float = Field(..., ge=0, le=100, description="Điểm trôi chảy")
    vocabulary_score: float = Field(..., ge=0, le=100, description="Điểm từ vựng")
    grammar_score: float = Field(..., ge=0, le=100, description="Điểm ngữ pháp")
    feedback: str = Field(..., description="Nhận xét tổng thể")
    suggestions: List[str] = Field(..., description="Gợi ý cải thiện")
    completed_at: datetime

class SessionCompleteRequest(CustomModel):
    force_complete: bool = Field(False, description="Kết thúc phiên ngay lập tức")
