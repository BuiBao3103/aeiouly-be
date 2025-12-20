from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.database import get_db
from src.auth.dependencies import get_current_active_user, resolve_user_from_websocket
from src.users.models import User

from src.online.service import LoginStreakService
from src.online.dependencies import get_login_streak_service, get_connection_manager


router = APIRouter(prefix="/online", tags=["Online"])


# ===== LOGIN STREAK ENDPOINTS =====


@router.get("/streak/stats")
async def get_login_streak_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's login streak statistics"""
    service = LoginStreakService()
    stats = await service.get_user_streak_stats(current_user.id, db)

    current = stats["current_streak"]
    longest = stats["longest_streak"]

    # Một số mốc thú vị để hiển thị cho user
    milestones = [1, 3, 5, 10, 20, 30]
    next_milestone = next((m for m in milestones if m > current), None)
    remaining = next_milestone - current if next_milestone is not None else 0

    # Level đơn giản dựa trên current_streak
    if current >= 30:
        level = "legend"
    elif current >= 20:
        level = "diamond"
    elif current >= 10:
        level = "gold"
    elif current >= 5:
        level = "silver"
    elif current >= 1:
        level = "bronze"
    else:
        level = "newbie"

    return {
        "user_id": current_user.id,
        "current_streak": current,
        "longest_streak": longest,
        "level": level,
        "next_milestone": next_milestone,
        "remaining_to_next_milestone": remaining,
    }


@router.get("/streak/leaderboard")
async def get_login_streak_leaderboard(
    limit: int = Query(10, description="Number of top users to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: LoginStreakService = Depends(get_login_streak_service)
):
    """Get top users by login streak"""

    leaderboard = await service.get_top_streak_users(db, limit)
    return {
        "leaderboard": leaderboard,
        "limit": limit
    }


@router.get("/streak/weekly")
async def get_weekly_streak_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: LoginStreakService = Depends(get_login_streak_service)
):
    """Get weekly streak statistics for the last 7 days"""
    weekly_stats = await service.get_weekly_streak_status(current_user.id, db)
    return weekly_stats


# WebSocket endpoint is defined in main.py at /online/ws
