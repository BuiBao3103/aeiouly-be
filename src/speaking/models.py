from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin

class SpeakingSession(Base, SoftDeleteMixin, TimestampMixin):
    """Speaking session model - Phiên học nói"""
    __tablename__ = "speaking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    level = Column(String(2), nullable=False, index=True)  # A1, A2, B1, B2, C1, C2
    status = Column(String(20), default="active", nullable=False)  # active, completed
    
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
    vietnamese_content = Column(Text, nullable=True)  # Vietnamese translation (only for assistant role)
    
    # Relationships
    session = relationship("SpeakingSession", back_populates="chat_messages")
