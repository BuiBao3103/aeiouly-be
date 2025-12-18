from pydantic import EmailStr
from typing import Optional
from src.models import CustomModel
from src.users.schemas import UserCreate, UserResponse, UserUpdateResponse, UserProfileUpdate

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

# Re-export UserUpdate as UserProfileUpdate for backward compatibility
UserUpdate = UserProfileUpdate