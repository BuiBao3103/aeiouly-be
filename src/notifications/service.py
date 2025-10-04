from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from src.notifications.connection_manager import ConnectionManager
from src.notifications.schemas import NotificationMessage
from src.notifications.dependencies import get_connection_manager


class NotificationService:
    """Service for managing notifications and WebSocket connections"""
    
    def __init__(self, connection_manager: ConnectionManager = None):
        self.connection_manager = connection_manager or get_connection_manager()
    
    async def send_to_user(self, user_id: int, message: str, notification_type: str = "info") -> bool:
        """Send notification to a specific user"""
        try:
            await self.connection_manager._send_to_user(user_id, message)
            return True
        except Exception as e:
            print(f"Error sending notification to user {user_id}: {e}")
            return False
    
    async def broadcast_to_all(self, message: str, notification_type: str = "info") -> int:
        """Broadcast notification to all connected users"""
        try:
            await self.connection_manager.broadcast(message)
            return len(self.connection_manager.active_connections)
        except Exception as e:
            print(f"Error broadcasting notification: {e}")
            return 0
    
    async def get_connection_stats(self) -> Dict:
        """Get current connection statistics"""
        return {
            "total_connections": len(self.connection_manager.active_connections),
            "unique_users": len(self.connection_manager.user_connections),
            "active_learning_timers": len(self.connection_manager.learning_timers)
        }
    
    async def get_user_connections(self, user_id: int) -> int:
        """Get number of connections for a specific user"""
        user_set = self.connection_manager.user_connections.get(user_id)
        return len(user_set) if user_set else 0
    
    async def is_user_online(self, user_id: int) -> bool:
        """Check if user is currently online"""
        return user_id in self.connection_manager.user_connections
