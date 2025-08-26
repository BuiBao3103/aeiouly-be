import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "Aeiouly"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A FastAPI project with authentication and posts"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    # Auth specific configurations
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_COOKIE_NAME: str = "access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    
    # Cookie settings
    COOKIE_SECURE: bool = True  # HTTPS only
    COOKIE_HTTPONLY: bool = True  # Prevent XSS
    COOKIE_SAMESITE: str = "lax"  # CSRF protection
    
    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_TOKEN_LENGTH: int = 32
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Google AI API Configuration
    GOOGLE_AI_API_KEY: str = ""
    
    # SMTP Configuration
    SMTP_SERVER: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@aeiouly.local"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    # Google AI API
    GOOGLE_AI_API_KEY: str = ""

    # Migrations
    AUTO_MIGRATE_ON_STARTUP: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # Front-end URL
    CLIENT_SIDE_URL: str = "http://localhost:3000"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()