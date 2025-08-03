from src.config import settings

# Auth specific configurations
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password validation
MIN_PASSWORD_LENGTH = 8
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]"

# Username validation
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
USERNAME_REGEX = r"^[a-zA-Z0-9_]+$" 