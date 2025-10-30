"""Dependencies for Speaking module"""
from src.speaking.service import SpeakingService


def get_speaking_service() -> SpeakingService:
    """Dependency to get SpeakingService instance"""
    return SpeakingService()

