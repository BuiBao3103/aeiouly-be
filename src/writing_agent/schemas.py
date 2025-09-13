from pydantic import Field
from typing import Optional, List, Dict, Any
from src.models import CustomModel

# Phase 2: Main Interface - Chat (moved up)
class ChatMessageRequest(CustomModel):
    message: str = Field(..., description="Tin nhắn từ người dùng")

class ChatRequest(CustomModel):
    request: ChatMessageRequest = Field(..., description="Request object containing message")
    user_id: str = Field(..., description="User ID")

class ChatResponse(CustomModel):
    response: str
    type: str = Field(..., description="instruction|feedback|encouragement|summary|status")

# Phase 1: Setup - Create Session
class CreateSessionRequest(CustomModel):
    topic: str = Field(..., description="Chủ đề luyện viết")
    level: str = Field(..., description="Mức độ: basic, intermediate, advanced")
    length: str = Field(..., description="Độ dài số câu")

class CreateSessionResponse(CustomModel):
    session_id: str
    paragraph_vi: str
    sentences_vi: List[str]
    chat_response: ChatResponse = Field(..., description="Phản hồi từ AI agent sau khi tạo session")

# Phase 2: Main Interface - Dashboard
class LessonInfo(CustomModel):
    topic: str
    level: str
    length: str
    paragraph_vi: str

class Progress(CustomModel):
    current_sentence_index: int
    total_sentences: int
    completed_sentences: int

class CurrentSentence(CustomModel):
    text_vi: str
    user_translation: Optional[str] = None
    feedback: Optional[Dict[str, Any]] = None
    status: str = Field(..., description="pending|submitted|reviewed")

class Statistics(CustomModel):
    accuracy_rate: float
    common_errors: List[str]
    strengths: List[str]

class DashboardResponse(CustomModel):
    lesson_info: LessonInfo
    progress: Progress
    current_sentence: CurrentSentence
    statistics: Statistics

# Phase 3: Session End
class EndSessionResponse(CustomModel):
    final_score: float
    detailed_summary: str
    strengths: List[str]
    areas_to_improve: List[str]
    next_steps: str
    session_duration: int  # in seconds
