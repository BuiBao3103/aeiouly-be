from src.learning_paths.service import LearningPathService

# Singleton instance - reuse across all requests for better performance
_learning_path_service_instance: LearningPathService | None = None


def get_learning_path_service() -> LearningPathService:
    """Dependency to get SpeakingService instance (singleton pattern for performance)"""
    global _learning_path_service_instance
    if _learning_path_service_instance is None:
        _learning_path_service_instance = LearningPathService()
    return _learning_path_service_instance

