from src.online.service import LoginStreakService
from src.online.connection_manager import ConnectionManager


def get_login_streak_service() -> LoginStreakService:
    """Get LoginStreakService instance"""
    return LoginStreakService()


_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager



