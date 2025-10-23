from fastapi import Depends
from src.reading.service import ReadingService

def get_reading_service() -> ReadingService:
    """Get ReadingService instance"""
    return ReadingService()
