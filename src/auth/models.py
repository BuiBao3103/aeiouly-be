from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base, SoftDeleteMixin, TimestampMixin):
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
    
    # Relationships
    posts = relationship("Post", back_populates="author")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    liked_posts = relationship("PostLike", back_populates="user")
    learning_sessions = relationship("LearningSession", back_populates="user")
    login_streaks = relationship("LoginStreak", back_populates="user")
    writing_sessions = relationship("WritingSession", back_populates="user")
    listening_sessions = relationship("ListeningSession", back_populates="user")

class PasswordResetToken(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    # moved to TimestampMixin

class RefreshToken(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    # moved to TimestampMixin

    # Relationship
    user = relationship("User", back_populates="refresh_tokens") 