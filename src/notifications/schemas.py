from pydantic import BaseModel
from typing import Optional


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
