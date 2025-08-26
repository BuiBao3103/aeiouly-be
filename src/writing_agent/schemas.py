from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Phase 2: Main Interface - Chat (moved up)
class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="Tin nhắn từ người dùng")

class ChatRequest(BaseModel):
    request: ChatMessageRequest = Field(..., description="Request object containing message")
    user_id: str = Field(..., description="User ID")

class ChatResponse(BaseModel):
    response: str
    type: str = Field(..., description="instruction|feedback|encouragement|summary|status")

# Phase 1: Setup - Create Session
class CreateSessionRequest(BaseModel):
    topic: str = Field(..., description="Chủ đề luyện viết")
    level: str = Field(..., description="Mức độ: basic, intermediate, advanced")
    length: str = Field(..., description="Độ dài số câu")

class CreateSessionResponse(BaseModel):
    session_id: str
    paragraph_vi: str
    sentences_vi: List[str]
    chat_response: ChatResponse = Field(..., description="Phản hồi từ AI agent sau khi tạo session")

# Phase 2: Main Interface - Dashboard
class LessonInfo(BaseModel):
    topic: str
    level: str
    length: str
    paragraph_vi: str

class Progress(BaseModel):
    current_sentence_index: int
    total_sentences: int
    completed_sentences: int

class CurrentSentence(BaseModel):
    text_vi: str
    user_translation: Optional[str] = None
    feedback: Optional[Dict[str, Any]] = None
    status: str = Field(..., description="pending|submitted|reviewed")

class Statistics(BaseModel):
    accuracy_rate: float
    common_errors: List[str]
    strengths: List[str]

class DashboardResponse(BaseModel):
    lesson_info: LessonInfo
    progress: Progress
    current_sentence: CurrentSentence
    statistics: Statistics

# Phase 3: Session End
class EndSessionResponse(BaseModel):
    final_score: float
    detailed_summary: str
    strengths: List[str]
    areas_to_improve: List[str]
    next_steps: str
    session_duration: int  # in seconds
