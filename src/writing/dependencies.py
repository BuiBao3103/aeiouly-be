"""
Dependencies for Writing Practice module
"""

from src.writing.service import WritingService

def get_writing_service() -> WritingService:
    """Get WritingService instance"""
    return WritingService()
