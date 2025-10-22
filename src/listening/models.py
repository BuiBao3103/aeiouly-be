from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Float, JSON
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

class ListenLesson(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "listen_lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    youtube_url = Column(String(500), nullable=False)
    level = Column(String(10), nullable=False)
    total_sentences = Column(Integer, default=0)
    
    # Relationships
    sentences = relationship("Sentence", back_populates="lesson", cascade="all, delete-orphan")
    sessions = relationship("ListeningSession", back_populates="lesson", cascade="all, delete-orphan")

class Sentence(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "sentences"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("listen_lessons.id"), nullable=False, index=True)
    index = Column(Integer, nullable=False)  # Order in lesson
    text = Column(Text, nullable=False)  # Original English text
    translation = Column(Text, nullable=True)  # Vietnamese translation
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    normalized_text = Column(Text, nullable=True)  # Normalized for comparison
    confidence = Column(Float, nullable=True)  # Confidence score per sentence (0-1)
    
    # Relationships
    lesson = relationship("ListenLesson", back_populates="sentences")

class ListeningSession(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "listening_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("listen_lessons.id"), nullable=False, index=True)
    current_sentence_index = Column(Integer, default=0)
    status = Column(String(20), default="active")
    attempts = Column(Integer, default=1)  # Number of attempts for this lesson
    
    # Relationships
    user = relationship("User", back_populates="listening_sessions")
    lesson = relationship("ListenLesson", back_populates="sessions")
