from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import TimestampMixin, SoftDeleteMixin


class LearningPath(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    form_data = Column(JSONB, nullable=False, default={})
    status = Column(String(20), default="generating", nullable=False)

    user = relationship("User", back_populates="learning_paths")
    daily_plans = relationship(
        "DailyLessonPlan", back_populates="learning_path", cascade="all, delete-orphan")


class DailyLessonPlan(Base, TimestampMixin):
    __tablename__ = "daily_lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(Integer, ForeignKey(
        "learning_paths.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)

    learning_path = relationship("LearningPath", back_populates="daily_plans")
    user_progress = relationship(
        "UserLessonProgress", back_populates="daily_lesson_plan", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('learning_path_id', 'day_number',
                         name='_learning_day_uc'),
    )


class UserLessonProgress(Base, TimestampMixin):
    __tablename__ = "user_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    daily_lesson_plan_id = Column(Integer, ForeignKey(
        "daily_lesson_plans.id"), nullable=False, index=True)
    lesson_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    lesson_type = Column(String(20), nullable=False)
    # ID của phiên học cụ thể (ReadingSession,...)
    session_id = Column(Integer, nullable=True)
    # 'start', 'in_progress', 'done'
    status = Column(String(20), default="start", nullable=False)
    metadata_ = Column(JSONB, nullable=False, default={})

    user = relationship("User", back_populates="lesson_progress")
    daily_lesson_plan = relationship(
        "DailyLessonPlan", back_populates="user_progress")

    __table_args__ = (
        UniqueConstraint('user_id', 'daily_lesson_plan_id',
                         'lesson_index', name='_user_lesson_progress_uc'),
    )
