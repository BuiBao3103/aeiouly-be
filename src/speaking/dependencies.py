"""Dependencies for Speaking module"""
from src.speaking.service import SpeakingService

# Singleton instance - reuse across all requests for better performance
_speaking_service_instance: SpeakingService | None = None


def get_speaking_service() -> SpeakingService:
    """Dependency to get SpeakingService instance (singleton pattern for performance)"""
    global _speaking_service_instance
    if _speaking_service_instance is None:
        _speaking_service_instance = SpeakingService()
    return _speaking_service_instance

