from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
from src.models import CustomModel


class LearningSessionBase(CustomModel):
    session_start: datetime
    session_end: Optional[datetime] = None
    duration_minutes: float = 0.0
    is_active: bool = True


class LearningSessionCreate(LearningSessionBase):
    pass


class LearningSessionResponse(LearningSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class LearningStatsResponse(CustomModel):
    total_minutes: float
    total_sessions: int
    average_session_minutes: float
    current_active_session: Optional[LearningSessionResponse] = None


class DailyLearningStats(CustomModel):
    date: date
    total_minutes: float
    session_count: int


class WeeklyLearningStats(CustomModel):
    week_start: date
    week_end: date
    total_minutes: float
    session_count: int
    daily_breakdown: List[DailyLearningStats]


class MonthlyLearningStats(CustomModel):
    month: int
    year: int
    total_minutes: float
    session_count: int
    daily_breakdown: List[DailyLearningStats]


class YearlyLearningStats(CustomModel):
    year: int
    total_minutes: float
    session_count: int
    monthly_breakdown: List[MonthlyLearningStats]
