from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class NotificationMessage(BaseModel):
    message: str
    type: Optional[str] = "info"  # info, success, warning, error
    timestamp: Optional[str] = None


class BroadcastRequest(BaseModel):
    message: str
    type: Optional[str] = "info"


class ConnectionStatus(BaseModel):
    connected: bool
    total_connections: int
    user_connections: int


class StreakUpdatedMessage(BaseModel):
    """Message sent when user's streak is updated after 5-minute timer"""
    type: str = "streak_updated"
    current_streak: int
    longest_streak: int
    message: str
    timestamp: str


