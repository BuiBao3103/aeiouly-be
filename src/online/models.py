from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Date
from sqlalchemy.orm import relationship

from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin


class LoginStreak(Base, SoftDeleteMixin, TimestampMixin):
    """Track login streak aggregate per user (no per-day rows)."""

    __tablename__ = "login_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Aggregate counters
    current_streak = Column(Integer, default=0, nullable=False)  # Current consecutive logins
    longest_streak = Column(Integer, default=0, nullable=False)  # Longest streak achieved

    # Ensure one record per user
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_login_streak_user"),
    )

    # Relationship
    user = relationship("User", back_populates="login_streaks")
    daily_records = relationship("LoginStreakDaily", back_populates="streak")


class LoginStreakDaily(Base, SoftDeleteMixin, TimestampMixin):
    """Track daily login streak for weekly statistics.
    
    Design decisions:
    - `user_id`: Cần thiết để query trực tiếp theo user (không cần join với streak)
    - `streak_id`: Foreign key để maintain referential integrity và relationship
    - Record tồn tại = user đã logged_in trong ngày đó (không cần field streak_count)
    - Unique constraint (user_id, date): Đảm bảo mỗi user chỉ có 1 record mỗi ngày, tự động tạo composite index
    
    Index optimization:
    - Unique constraint (user_id, date) tự động tạo composite index → tối ưu cho query theo user_id và date range
    - Index trên user_id riêng: Hữu ích cho query chỉ theo user_id
    - Index trên date riêng: Có thể không cần thiết nhưng giữ lại cho các query tương lai
    - Index trên streak_id: Hữu ích cho relationship queries
    """

    __tablename__ = "login_streak_daily"

    id = Column(Integer, primary_key=True, index=True)
    streak_id = Column(Integer, ForeignKey("login_streaks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Ensure one record per user per day
    # Unique constraint tự động tạo composite index (user_id, date) → tối ưu query weekly status
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_login_streak_daily_user_date"),
    )

    # Relationships
    streak = relationship("LoginStreak", back_populates="daily_records")
    user = relationship("User", back_populates="streak_daily_records")


