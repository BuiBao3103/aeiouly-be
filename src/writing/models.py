from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
import enum

class CEFRLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class WritingSession(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "writing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    difficulty = Column(Enum(CEFRLevel), nullable=False)
    total_sentences = Column(Integer, nullable=False)
    current_sentence_index = Column(Integer, default=0)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    vietnamese_text = Column(Text, nullable=False)  # Full Vietnamese text
    current_sentence = Column(Text, nullable=True)  # Current sentence being translated
    session_data = Column(JSON, nullable=True)  # Additional session data for agents
    
    # Relationships
    user = relationship("User", back_populates="writing_sessions")
    chat_messages = relationship("WritingChatMessage", back_populates="session", cascade="all, delete-orphan")

class WritingChatMessage(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "writing_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("writing_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sentence_index = Column(Integer, nullable=True)  # Which sentence this message relates to
    
    # Relationships
    session = relationship("WritingSession", back_populates="chat_messages")
