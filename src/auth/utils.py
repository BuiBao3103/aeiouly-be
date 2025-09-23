import secrets
from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from jose import JWTError, jwt
from src.config import settings
from src.auth.exceptions import TokenNotValidException

def generate_secure_token(length: int = settings.PASSWORD_RESET_TOKEN_LENGTH) -> str:
    """
    Generate a secure random token
    """
    return secrets.token_urlsafe(length)

def generate_refresh_token() -> str:
    """
    Generate a secure refresh token
    """
    return secrets.token_urlsafe(32)

def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if a token is expired
    """
    # Ensure both datetimes have timezone info for comparison
    now = datetime.now(ZoneInfo("UTC"))
    if expires_at.tzinfo is None:
        # If expires_at is naive, assume it's UTC
        expires_at = expires_at.replace(tzinfo=ZoneInfo("UTC"))
    return now > expires_at

def validate_access_token(token: str) -> Optional[str]:
    """
    Validate access token and return username if valid
    Returns None if token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def get_token_error_response(token: str) -> dict:
    """
    Get structured error response for token validation
    """
    username = validate_access_token(token)
    if username is None:
        return {
            "message": "Token không hợp lệ hoặc đã hết hạn",
            "code": "token_not_valid",
            "action": "refresh_token"
        }
    return {
        "message": "Token hợp lệ",
        "code": "token_valid",
        "action": "none"
    } 