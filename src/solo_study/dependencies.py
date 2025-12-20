from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from src.database import get_db
from src.solo_study.service import (
    SoundService, 
    BackgroundVideoTypeService, 
    BackgroundVideoService, 
    SessionGoalService,
    UserFavoriteVideoService
)


def get_sound_service() -> SoundService:
    """Dependency to get SoundService instance"""
    return SoundService()


def get_background_video_type_service() -> BackgroundVideoTypeService:
    """Dependency to get BackgroundVideoTypeService instance"""
    return BackgroundVideoTypeService()


def get_background_video_service() -> BackgroundVideoService:
    """Dependency to get BackgroundVideoService instance"""
    return BackgroundVideoService()


def get_session_goal_service() -> SessionGoalService:
    """Dependency to get SessionGoalService instance"""
    return SessionGoalService()


def get_user_favorite_video_service() -> UserFavoriteVideoService:
    """Dependency to get UserFavoriteVideoService instance"""
    return UserFavoriteVideoService()
