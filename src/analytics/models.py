from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, UniqueConstraint, DateTime, Float
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin


class LearningSession(Base, SoftDeleteMixin, TimestampMixin):
    """Track learning sessions and study time for users"""
    __tablename__ = "learning_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_start = Column(DateTime(timezone=True), nullable=False, index=True)
    session_end = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_minutes = Column(Float, default=0.0, nullable=False)  # Duration in minutes
    is_active = Column(Boolean, default=True, nullable=False)  # Whether session is still ongoing
    
    # Relationship
    user = relationship("User", back_populates="learning_sessions")


class LoginStreak(Base, SoftDeleteMixin, TimestampMixin):
    """Track user login streaks"""
    __tablename__ = "login_streaks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    login_count = Column(Integer, default=1, nullable=False)  # Number of logins on this date
    current_streak = Column(Integer, default=1, nullable=False)  # Current consecutive days
    longest_streak = Column(Integer, default=1, nullable=False)  # Longest streak achieved
    
    # Ensure one record per user per date
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_login_streak_user_date'),
    )
    
    # Relationship
    user = relationship("User", back_populates="login_streaks")