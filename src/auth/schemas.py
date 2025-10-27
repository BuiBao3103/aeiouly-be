from pydantic import EmailStr
from typing import Optional
from datetime import datetime
from src.models import CustomModel
from src.users.models import UserRole

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
    avatar_url: Optional[str] = None
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


class GoogleLoginRequest(CustomModel):
    id_token: str

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

class UserUpdate(CustomModel):
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserUpdateResponse(CustomModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 