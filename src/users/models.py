"""
Models for Users module
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base, SoftDeleteMixin, TimestampMixin):
    """User model - moved from auth module"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    evaluation_history = Column(JSONB, default=[], nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="author")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    liked_posts = relationship("PostLike", back_populates="user")
    login_streaks = relationship("LoginStreak", back_populates="user")
    streak_daily_records = relationship("LoginStreakDaily", back_populates="user")
    writing_sessions = relationship("WritingSession", back_populates="user")
    listening_sessions = relationship("ListeningSession", back_populates="user")
    reading_sessions = relationship("ReadingSession", back_populates="user")
    vocabulary_sets = relationship("VocabularySet", back_populates="user")
    vocabulary_items = relationship("VocabularyItem", back_populates="user")
    session_goals = relationship("SessionGoal", back_populates="user")
    favorite_videos = relationship("UserFavoriteVideo", back_populates="user")
    speaking_sessions = relationship("SpeakingSession", back_populates="user")

