from fastapi import Depends
from src.reading.service import ReadingService

_reading_service_instance: ReadingService | None = None


def get_reading_service() -> ReadingService:
    """Get a shared ReadingService instance (singleton per process)."""
    global _reading_service_instance
    if _reading_service_instance is None:
        _reading_service_instance = ReadingService()
    return _reading_service_instance
