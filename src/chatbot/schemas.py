"""Schemas for Chatbot module"""
from pydantic import BaseModel, Field
from typing import Optional
from src.models import CustomModel


class ChatbotMessageRequest(CustomModel):
    """Schema for sending a message to chatbot"""
    message: str = Field(..., min_length=1, description="Nội dung tin nhắn người dùng")
    conversation_id: Optional[str] = Field(
        default=None,
        description="ID cuộc trò chuyện (tùy chọn). Nếu không truyền, service sẽ tái sử dụng hoặc tạo mới."
    )


class ChatbotMessageResponse(CustomModel):
    """Schema for chatbot response"""
    response: str = Field(..., description="Phản hồi từ chatbot")
    conversation_id: str = Field(..., description="ID cuộc trò chuyện hiện tại (dùng để tiếp tục chat)")

