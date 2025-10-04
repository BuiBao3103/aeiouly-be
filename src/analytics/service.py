from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List
from src.analytics.models import LearningSession
from src.analytics.schemas import (
    LearningSessionCreate, LearningStatsResponse, 
    DailyLearningStats, WeeklyLearningStats, 
    MonthlyLearningStats, YearlyLearningStats
)


class LearningAnalyticsService:
    def __init__(self):
        pass

    async def start_learning_session(self, user_id: int, db: Session) -> LearningSession:
        """Start a new learning session for user"""
        # End any existing active session
        await self.end_active_session(user_id, db)
        
        session = LearningSession(
            user_id=user_id,
            session_start=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    async def end_learning_session(self, user_id: int, db: Session) -> Optional[LearningSession]:
        """End the current active learning session"""
        active_session = db.query(LearningSession).filter(
            and_(
                LearningSession.user_id == user_id,
                LearningSession.is_active == True
            )
        ).first()
        
        if active_session:
            active_session.session_end = datetime.now(timezone.utc)
            active_session.is_active = False
            # Calculate duration in minutes
            duration = active_session.session_end - active_session.session_start
            active_session.duration_minutes = duration.total_seconds() / 60
            db.commit()
            db.refresh(active_session)
        
        return active_session

    async def end_active_session(self, user_id: int, db: Session) -> None:
        """Helper to end any active session before starting new one"""
        await self.end_learning_session(user_id, db)

    async def get_active_session(self, user_id: int, db: Session) -> Optional[LearningSession]:
        """Get the current active learning session for a user"""
        return db.query(LearningSession).filter(
            and_(
                LearningSession.user_id == user_id,
                LearningSession.is_active == True
            )
        ).first()

    async def get_learning_stats(self, user_id: int, db: Session) -> LearningStatsResponse:
        """Get overall learning statistics for user"""
        # Get total minutes and session count
        stats = db.query(
            func.sum(LearningSession.duration_minutes).label('total_minutes'),
            func.count(LearningSession.id).label('total_sessions')
        ).filter(LearningSession.user_id == user_id).first()
        
        total_minutes = float(stats.total_minutes or 0)
        total_sessions = int(stats.total_sessions or 0)
        average_session_minutes = total_minutes / total_sessions if total_sessions > 0 else 0
        
        # Get current active session
        current_session = db.query(LearningSession).filter(
            and_(
                LearningSession.user_id == user_id,
                LearningSession.is_active == True
            )
        ).first()
        
        return LearningStatsResponse(
            total_minutes=total_minutes,
            total_sessions=total_sessions,
            average_session_minutes=average_session_minutes,
            current_active_session=current_session
        )

    async def get_daily_stats(self, user_id: int, target_date: date, db: Session) -> DailyLearningStats:
        """Get learning stats for a specific day"""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        stats = db.query(
            func.sum(LearningSession.duration_minutes).label('total_minutes'),
            func.count(LearningSession.id).label('session_count')
        ).filter(
            and_(
                LearningSession.user_id == user_id,
                LearningSession.session_start >= start_datetime,
                LearningSession.session_start <= end_datetime
            )
        ).first()
        
        return DailyLearningStats(
            date=target_date,
            total_minutes=float(stats.total_minutes or 0),
            session_count=int(stats.session_count or 0)
        )

    async def get_weekly_stats(self, user_id: int, year: int, week: int, db: Session) -> WeeklyLearningStats:
        """Get learning stats for a specific week"""
        # Calculate week start and end dates
        jan_1 = date(year, 1, 1)
        week_start = jan_1 + timedelta(weeks=week-1)
        week_end = week_start + timedelta(days=6)
        
        # Get daily breakdown
        daily_stats = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            daily_stat = await self.get_daily_stats(user_id, current_date, db)
            daily_stats.append(daily_stat)
        
        total_minutes = sum(stat.total_minutes for stat in daily_stats)
        session_count = sum(stat.session_count for stat in daily_stats)
        
        return WeeklyLearningStats(
            week_start=week_start,
            week_end=week_end,
            total_minutes=total_minutes,
            session_count=session_count,
            daily_breakdown=daily_stats
        )

    async def get_monthly_stats(self, user_id: int, year: int, month: int, db: Session) -> MonthlyLearningStats:
        """Get learning stats for a specific month"""
        # Get all days in the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get daily breakdown
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            daily_stat = await self.get_daily_stats(user_id, current_date, db)
            daily_stats.append(daily_stat)
            current_date += timedelta(days=1)
        
        total_minutes = sum(stat.total_minutes for stat in daily_stats)
        session_count = sum(stat.session_count for stat in daily_stats)
        
        return MonthlyLearningStats(
            month=month,
            year=year,
            total_minutes=total_minutes,
            session_count=session_count,
            daily_breakdown=daily_stats
        )

    async def get_yearly_stats(self, user_id: int, year: int, db: Session) -> YearlyLearningStats:
        """Get learning stats for a specific year"""
        # Get monthly breakdown
        monthly_stats = []
        for month in range(1, 13):
            monthly_stat = await self.get_monthly_stats(user_id, year, month, db)
            monthly_stats.append(monthly_stat)
        
        total_minutes = sum(stat.total_minutes for stat in monthly_stats)
        session_count = sum(stat.session_count for stat in monthly_stats)
        
        return YearlyLearningStats(
            year=year,
            total_minutes=total_minutes,
            session_count=session_count,
            monthly_breakdown=monthly_stats
        )

    async def get_current_week_stats(self, user_id: int, db: Session) -> WeeklyLearningStats:
        """Get stats for current week"""
        today = date.today()
        year, week, _ = today.isocalendar()
        return await self.get_weekly_stats(user_id, year, week, db)

    async def get_current_month_stats(self, user_id: int, db: Session) -> MonthlyLearningStats:
        """Get stats for current month"""
        today = date.today()
        return await self.get_monthly_stats(user_id, today.year, today.month, db)

    async def get_current_year_stats(self, user_id: int, db: Session) -> YearlyLearningStats:
        """Get stats for current year"""
        today = date.today()
        return await self.get_yearly_stats(user_id, today.year, db)
