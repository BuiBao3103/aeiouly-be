from fastapi import HTTPException, status


class NotificationException(HTTPException):
    """Base exception for notification-related errors"""
    def __init__(self, detail: str = "Notification error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ConnectionException(NotificationException):
    """Exception for WebSocket connection errors"""
    def __init__(self, detail: str = "Connection error"):
        super().__init__(detail=detail)


class BroadcastException(NotificationException):
    """Exception for broadcast notification errors"""
    def __init__(self, detail: str = "Broadcast error"):
        super().__init__(detail=detail)


class AuthenticationException(HTTPException):
    """Exception for WebSocket authentication errors"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.WS_1008_POLICY_VIOLATION, detail=detail)
