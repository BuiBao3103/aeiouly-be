from sqlalchemy.orm import Session
from fastapi import Depends

from src.database import get_db
from src.solo_study.service import SoundService


def get_sound_service() -> SoundService:
    """Dependency to get SoundService instance"""
    return SoundService()
