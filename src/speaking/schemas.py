"""Schemas for Speaking module"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.models import CustomModel
from src.constants.cefr import CEFRLevel


class SpeechToTextResponse(BaseModel):
    """Response schema for speech-to-text conversion"""
    text: str = Field(..., description="Transcribed text from audio")


class SpeechToTextRequest(BaseModel):
    """Request schema for speech-to-text (optional metadata)"""
    language_code: str = Field(default="en-US", description="Language code (default: en-US)")
    sample_rate_hertz: int = Field(default=16000, description="Sample rate in Hz (default: 16000)")
    encoding: str = Field(default="LINEAR16", description="Audio encoding (default: LINEAR16)")


class SpeakingSessionCreate(CustomModel):
    """Schema for creating a new speaking session"""
    my_character: str = Field(..., min_length=1, max_length=255, description="Nhân vật của bạn trong cuộc trò chuyện")
    ai_character: str = Field(..., min_length=1, max_length=255, description="Nhân vật AI trong cuộc trò chuyện")
    scenario: str = Field(..., min_length=1, description="Tình huống giao tiếp")
    level: CEFRLevel = Field(..., description="Độ khó theo thang CEFR")


class SpeakingSessionResponse(CustomModel):
    """Schema for speaking session response"""
    id: int
    user_id: int
    my_character: str
    ai_character: str
    scenario: str
    level: CEFRLevel
    status: str 
    created_at: datetime
    updated_at: Optional[datetime] = None


class SpeakingSessionListResponse(CustomModel):
    """Schema for listing speaking sessions"""
    id: int
    my_character: str
    ai_character: str
    scenario: str
    level: CEFRLevel
    status: str
    created_at: datetime


class ChatMessageCreate(CustomModel):
    """Schema for sending a chat message (text or audio)"""
    content: Optional[str] = Field(None, description="Text content (required if audio_file is not provided)")


class ChatMessageResponse(CustomModel):
    """Schema for chat message response"""
    id: int
    session_id: int
    role: str
    content: str  # English content
    is_audio: bool
    audio_url: Optional[str] = Field(None, description="URL of attached audio for this message, if any")
    translation_sentence: Optional[str] = Field(None, description="Vietnamese translation of the assistant message")
    session: Optional[SpeakingSessionResponse] = Field(
        None, description="Updated speaking session state associated with this response"
    )
    created_at: datetime


class HintResponse(CustomModel):
    """Schema for hint response"""
    hint: str = Field(..., description="Gợi ý bằng tiếng Việt (format: Phân tích, Gợi ý, Ví dụ)")
    last_ai_message: str = Field(..., description="Tin nhắn cuối cùng của AI để gợi ý dựa trên đó")


class FinalEvaluationResponse(CustomModel):
    """Schema for final evaluation response"""
    session_id: int
    overall_score: float = Field(..., ge=0, le=100, description="Điểm tổng thể")
    pronunciation_score: float = Field(..., ge=0, le=100, description="Điểm phát âm")
    fluency_score: float = Field(..., ge=0, le=100, description="Điểm trôi chảy")
    vocabulary_score: float = Field(..., ge=0, le=100, description="Điểm từ vựng")
    grammar_score: float = Field(..., ge=0, le=100, description="Điểm ngữ pháp")
    interaction_score: float = Field(..., ge=0, le=100, description="Điểm tương tác")
    feedback: str = Field(..., description="Nhận xét tổng thể")
    suggestions: List[str] = Field(..., description="Gợi ý cải thiện")
    completed_at: datetime

