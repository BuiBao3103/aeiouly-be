import secrets
from typing import Optional
from datetime import datetime, timedelta
from src.auth.config import PASSWORD_RESET_TOKEN_LENGTH

def generate_secure_token(length: int = PASSWORD_RESET_TOKEN_LENGTH) -> str:
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
    return datetime.utcnow() > expires_at 