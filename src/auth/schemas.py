from pydantic import EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
from src.models import CustomModel

class UserRole(str, Enum):
    ADMIN = "admin"  # Match the values in models.py
    USER = "user"

class UserBase(CustomModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginRequest(CustomModel):
    username: str
    password: str

class Token(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class ErrorResponse(CustomModel):
    message: str
    code: str
    action: str

class AuthErrorResponse(CustomModel):
    detail: ErrorResponse

class PasswordResetRequest(CustomModel):
    email: EmailStr

class PasswordResetConfirm(CustomModel):
    token: str
    new_password: str

class PasswordChange(CustomModel):
    current_password: str
    new_password: str 