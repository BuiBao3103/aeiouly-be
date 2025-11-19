from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
from src.constants.cefr import CEFRLevel
import enum


class SpeakingSession(Base, SoftDeleteMixin, TimestampMixin):
    """Speaking session model - Phiên học nói"""
    __tablename__ = "speaking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    my_character = Column(String(255), nullable=False)  # Nhân vật của người dùng
    ai_character = Column(String(255), nullable=False)  # Nhân vật AI
    scenario = Column(Text, nullable=False)  # Tình huống giao tiếp
    level = Column(String(10), nullable=False)
    status = Column(String(20), default="active")
    
    # Relationships
    user = relationship("User", back_populates="speaking_sessions")
    chat_messages = relationship("SpeakingChatMessage", back_populates="session", cascade="all, delete-orphan")

class SpeakingChatMessage(Base, SoftDeleteMixin, TimestampMixin):
    """Speaking chat message model - Tin nhắn chat trong phiên nói"""
    __tablename__ = "speaking_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("speaking_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)  # English content
    is_audio = Column(Boolean, default=False, nullable=False)  # True if message was sent as audio
    
    # Relationships
    session = relationship("SpeakingSession", back_populates="chat_messages")
