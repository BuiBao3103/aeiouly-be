from src.config import settings

# Auth specific configurations
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Giảm thời gian access token
REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

# Cookie settings
COOKIE_SECURE = True  # HTTPS only
COOKIE_HTTPONLY = True  # Prevent XSS
COOKIE_SAMESITE = "lax"  # CSRF protection

# Password reset
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30
PASSWORD_RESET_TOKEN_LENGTH = 32 