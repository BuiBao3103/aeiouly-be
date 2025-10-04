from fastapi import Depends
from src.notifications.connection_manager import ConnectionManager

# Global connection manager instance
_connection_manager = None

def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
