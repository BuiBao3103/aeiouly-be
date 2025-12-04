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
    # Note: Set to False for localhost development (ws://), True for production (wss://)
    COOKIE_SECURE: bool = False  # Set to True in production with HTTPS/WSS
    COOKIE_HTTPONLY: bool = True  # Prevent XSS
    COOKIE_SAMESITE: str = "lax"  # CSRF protection
    COOKIE_DOMAIN: str = "localhost"
    
    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour instead of 30 minutes
    PASSWORD_RESET_TOKEN_LENGTH: int = 32
    
    # Database - prefer discrete Postgres settings; fallback to DATABASE_URL
    DATABASE_URL: str = ""  # Optional explicit URL; leave empty to assemble from fields below
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "aeiouly"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    DATABASE_DIALECT: str = "postgresql+psycopg2"  # e.g., postgresql+psycopg2, sqlite
    
    # SMTP Configuration
    SMTP_SERVER: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@aeiouly.local"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    # Google AI API
    GOOGLE_API_KEY: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    
    # Google Cloud Speech-to-Text API
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""  # Path to service account JSON file

    # Migrations
    AUTO_MIGRATE_ON_STARTUP: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # Front-end URL
    CLIENT_SIDE_URL: str = "http://localhost:3000"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_REGION: str = "ap-southeast-1"
    AWS_S3_BUCKET: str = ""
    AWS_S3_PUBLIC_URL: str = ""  # Optional CDN/base URL; if empty, build from region/bucket
    
    # Default Avatar URL
    DEFAULT_AVATAR_URL: str = "https://aeiouly.s3.ap-southeast-1.amazonaws.com/avatars/default-avatar.png"

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

# Helper to assemble DB URL when not explicitly provided
def get_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    # Safely URL-encode credentials to handle special characters like @ : /
    try:
        from urllib.parse import quote_plus
    except Exception:  # pragma: no cover
        quote_plus = lambda x: x  # fallback (should not happen)

    user = quote_plus(settings.POSTGRES_USER or "")
    password = quote_plus(settings.POSTGRES_PASSWORD or "")
    host = settings.POSTGRES_HOST
    port = settings.POSTGRES_PORT
    db = settings.POSTGRES_DB
    dialect = settings.DATABASE_DIALECT
    if password:
        cred = f"{user}:{password}@"
    elif user:
        cred = f"{user}@"
    else:
        cred = ""
    return f"{dialect}://{cred}{host}:{port}/{db}"