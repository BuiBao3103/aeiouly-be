from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.analytics.service import LearningAnalyticsService
from src.analytics.online_service import OnlineAnalyticsService
from src.analytics.dependencies import get_learning_analytics_service, get_online_analytics_service
from src.analytics.dependencies import get_login_streak_service
from src.analytics.streak_service import LoginStreakService
from src.analytics.schemas import (
    LearningStatsResponse, DailyLearningStats, WeeklyLearningStats, 
    MonthlyLearningStats, YearlyLearningStats
)
from datetime import date, datetime, timezone

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/learning/start", response_model=dict)
async def start_learning_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Start a new learning session"""
    session = await service.start_learning_session(current_user.id, db)
    return {
        "message": "Learning session started",
        "session_id": session.id,
        "start_time": session.session_start
    }


@router.post("/learning/end", response_model=dict)
async def end_learning_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """End the current learning session"""
    session = await service.end_learning_session(current_user.id, db)
    
    if not session:
        raise HTTPException(status_code=404, detail="No active learning session found")
    
    return {
        "message": "Learning session ended",
        "session_id": session.id,
        "duration_minutes": session.duration_minutes
    }


@router.get("/learning/stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get overall learning statistics"""
    return await service.get_learning_stats(current_user.id, db)


@router.get("/learning/daily", response_model=DailyLearningStats)
async def get_daily_stats(
    target_date: date = Query(..., description="Date to get stats for (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for a specific day"""
    return await service.get_daily_stats(current_user.id, target_date, db)


@router.get("/learning/weekly", response_model=WeeklyLearningStats)
async def get_weekly_stats(
    year: int = Query(..., description="Year"),
    week: int = Query(..., description="Week number (1-53)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for a specific week"""
    return await service.get_weekly_stats(current_user.id, year, week, db)


@router.get("/learning/weekly/current", response_model=WeeklyLearningStats)
async def get_current_week_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for current week"""
    return await service.get_current_week_stats(current_user.id, db)


@router.get("/learning/monthly", response_model=MonthlyLearningStats)
async def get_monthly_stats(
    year: int = Query(..., description="Year"),
    month: int = Query(..., description="Month (1-12)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for a specific month"""
    return await service.get_monthly_stats(current_user.id, year, month, db)


@router.get("/learning/monthly/current", response_model=MonthlyLearningStats)
async def get_current_month_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for current month"""
    return await service.get_current_month_stats(current_user.id, db)


@router.get("/learning/yearly", response_model=YearlyLearningStats)
async def get_yearly_stats(
    year: int = Query(..., description="Year"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for a specific year"""
    return await service.get_yearly_stats(current_user.id, year, db)


@router.get("/learning/yearly/current", response_model=YearlyLearningStats)
async def get_current_year_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LearningAnalyticsService = Depends(get_learning_analytics_service)
):
    """Get learning stats for current year"""
    return await service.get_current_year_stats(current_user.id, db)


# Online Status APIs - Simplified after removing user_online_status table


# ===== LOGIN STREAK ENDPOINTS =====

@router.get("/streak/stats")
async def get_login_streak_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's login streak statistics"""
    service = LoginStreakService()
    stats = await service.get_user_streak_stats(current_user.id, db)
    return {
        "user_id": current_user.id,
        "current_streak": stats["current_streak"],
        "longest_streak": stats["longest_streak"],
        "today_logins": stats["today_logins"],
        "last_login_date": stats["last_login_date"]
    }


@router.get("/streak/history")
async def get_login_streak_history(
    days: int = Query(30, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LoginStreakService = Depends(get_login_streak_service)
    
):
    """Get user's login streak history for the last N days"""
    history = await service.get_streak_history(db, current_user.id, days)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "days": days,
        "streak_history": history,
        "summary": {
            "total_login_days": sum(1 for day in history if day['logged_in']),
            "current_streak": max((day['current_streak'] for day in history), default=0),
            "longest_streak": max((day['current_streak'] for day in history), default=0)
        }
    }


@router.get("/streak/leaderboard")
async def get_login_streak_leaderboard(
    limit: int = Query(10, description="Number of top users to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LoginStreakService = Depends(get_login_streak_service)
):
    """Get top users by login streak (Admin only)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view leaderboard"
        )
    
    leaderboard = await service.get_top_streak_users(db, limit)
    return {
        "leaderboard": leaderboard,
        "limit": limit
    }


@router.get("/streak/weekly")
async def get_weekly_streak_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: LoginStreakService = Depends(get_login_streak_service)
):
    """Get streak status for all days in the current week"""
    weekly_data = await service.get_weekly_streak_status(db, current_user.id)
    return weekly_data


# ===== USER ONLINE STATUS ENDPOINTS =====

@router.get("/online/check/{user_id}")
async def check_user_online_status(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: OnlineAnalyticsService = Depends(get_online_analytics_service)
):
    """Check if a specific user is currently online"""
    # Users can only check their own status or admins can check anyone
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own online status"
        )
    
    today = date.today()
    online_status = await service.get_user_online_status(user_id, today, db)
    
    return {
        "user_id": user_id,
        "date": today,
        "is_online": online_status["is_online"],
        "checked_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/online/check")
async def check_current_user_online_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    service: OnlineAnalyticsService = Depends(get_online_analytics_service)
):
    """Check current user's online status"""
    today = date.today()
    online_status = await service.get_user_online_status(current_user.id, today, db)
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "date": today,
        "is_online": online_status["is_online"],
        "checked_at": datetime.now(timezone.utc).isoformat()
    }
