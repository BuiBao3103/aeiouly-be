"""
Schemas for Users module
"""
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from src.models import CustomModel
from src.users.models import UserRole

# Constants for field descriptions
FULL_NAME_DESC = "Họ tên đầy đủ"
ROLE_DESC = "Vai trò"


class UserBase(CustomModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(CustomModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    # Note: role is always USER and cannot be set via API
    # Admin users must be created manually


class UserUpdate(CustomModel):
    email: Optional[str] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Họ tên đầy đủ")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động")
    # Note: role cannot be changed via API
    # Admin users must be created manually


class UserProfileUpdate(CustomModel):
    """Schema for users to update their own profile"""
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserResetPassword(CustomModel):
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới")


class UserResponse(CustomModel):
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


class UserUpdateResponse(CustomModel):
    """Response after updating user profile"""
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

