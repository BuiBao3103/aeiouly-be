"""
Schemas for Users module
"""
from datetime import datetime
from typing import Optional
from pydantic import Field

from src.models import CustomModel
from src.users.models import UserRole

# Constants for field descriptions
FULL_NAME_DESC = "Họ tên đầy đủ"
ROLE_DESC = "Vai trò"


class UserBase(CustomModel):
    username: str = Field(..., description="Tên đăng nhập")
    email: str = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description=FULL_NAME_DESC)
    role: UserRole = Field(UserRole.USER, description=ROLE_DESC)
    is_active: bool = Field(True, description="Trạng thái hoạt động")


class UserCreate(CustomModel):
    username: str = Field(..., description="Tên đăng nhập")
    email: str = Field(..., description="Email")
    password: str = Field(..., min_length=6, description="Mật khẩu")
    full_name: Optional[str] = Field(None, description=FULL_NAME_DESC)
    # Note: role is always USER and cannot be set via API
    # Admin users must be created manually


class UserUpdate(CustomModel):
    email: Optional[str] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Họ tên đầy đủ")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động")
    # Note: role cannot be changed via API
    # Admin users must be created manually


class UserResetPassword(CustomModel):
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới")


class UserResponse(UserBase):
    id: int = Field(..., description="ID user")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True

