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
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # SMTP Configuration
    SMTP_SERVER: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@aeiouly.local"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
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