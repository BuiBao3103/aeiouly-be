import re
from typing import Optional
from app.auth.config import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_REGEX,
    MIN_USERNAME_LENGTH,
    MAX_USERNAME_LENGTH,
    USERNAME_REGEX
)

def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    Returns: (is_valid, error_message)
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    if not re.match(PASSWORD_REGEX, password):
        return False, "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character"
    
    return True, None

def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username format
    Returns: (is_valid, error_message)
    """
    if len(username) < MIN_USERNAME_LENGTH:
        return False, f"Username must be at least {MIN_USERNAME_LENGTH} characters long"
    
    if len(username) > MAX_USERNAME_LENGTH:
        return False, f"Username must be at most {MAX_USERNAME_LENGTH} characters long"
    
    if not re.match(USERNAME_REGEX, username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, None

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Basic email validation
    Returns: (is_valid, error_message)
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    
    return True, None

def sanitize_username(username: str) -> str:
    """
    Sanitize username by removing special characters and converting to lowercase
    """
    return re.sub(r'[^a-zA-Z0-9_]', '', username.lower())

def generate_username_from_email(email: str) -> str:
    """
    Generate a username from email address
    """
    base_username = email.split('@')[0]
    return sanitize_username(base_username) 