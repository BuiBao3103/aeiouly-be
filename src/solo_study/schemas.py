from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.models import CustomModel
from src.solo_study.models import SessionGoalsStatus

# Constants for field descriptions
FILE_SIZE_DESC = "Kích thước file (bytes)"
DURATION_DESC = "Thời lượng (seconds)"


# Sound Schemas
class SoundBase(CustomModel):
    name: str = Field(..., description="Tên âm thanh (có thể chứa ký tự đặc biệt như 🌸 Anime)")
    sound_file_url: Optional[str] = Field(None, description="URL file âm thanh trên AWS S3")
    file_size: Optional[int] = Field(None, description=FILE_SIZE_DESC)
    duration: Optional[int] = Field(None, description=DURATION_DESC)


class SoundCreate(CustomModel):
    name: str = Field(..., description="Tên âm thanh (có thể chứa ký tự đặc biệt như 🌸 Anime)")


class SoundUpdate(CustomModel):
    name: Optional[str] = Field(None, description="Tên âm thanh")


class SoundResponse(SoundBase):
    id: int = Field(..., description="ID âm thanh")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True


class SoundUploadResponse(CustomModel):
    id: int = Field(..., description="ID âm thanh")
    name: str = Field(..., description="Tên âm thanh")
    sound_file_url: str = Field(..., description="URL file âm thanh trên AWS S3")
    file_size: int = Field(..., description="Kích thước file (bytes)")
    duration: Optional[int] = Field(None, description="Thời lượng (seconds)")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


# BackgroundVideoType Schemas
class BackgroundVideoTypeBase(CustomModel):
    name: str = Field(..., description="Tên loại video nền", max_length=100)
    description: Optional[str] = Field(None, description="Mô tả loại video nền")


class BackgroundVideoTypeCreate(CustomModel):
    name: str = Field(..., description="Tên loại video nền", max_length=100)
    description: Optional[str] = Field(None, description="Mô tả loại video nền")


class BackgroundVideoTypeUpdate(CustomModel):
    name: Optional[str] = Field(None, description="Tên loại video nền", max_length=100)
    description: Optional[str] = Field(None, description="Mô tả loại video nền")


class BackgroundVideoTypeResponse(BackgroundVideoTypeBase):
    id: int = Field(..., description="ID loại video nền")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True


# BackgroundVideo Schemas
class BackgroundVideoBase(CustomModel):
    youtube_url: str = Field(..., description="URL video YouTube", max_length=500)
    image_url: Optional[str] = Field(None, description="URL hình ảnh", max_length=500)
    type_id: int = Field(..., description="ID loại video nền")


class BackgroundVideoCreate(CustomModel):
    youtube_url: str = Field(..., description="URL video YouTube", max_length=500)
    type_id: int = Field(..., description="ID loại video nền")


class BackgroundVideoUpdate(CustomModel):
    youtube_url: Optional[str] = Field(None, description="URL video YouTube", max_length=500)
    image_url: Optional[str] = Field(None, description="URL hình ảnh", max_length=500)
    type_id: Optional[int] = Field(None, description="ID loại video nền")


class BackgroundVideoResponse(BackgroundVideoBase):
    id: int = Field(..., description="ID video nền")
    type_name: Optional[str] = Field(None, description="Tên loại video nền")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True


# SessionGoal Schemas
class SessionGoalBase(CustomModel):
    goal: str = Field(..., description="Mục tiêu phiên học", max_length=255)
    status: SessionGoalsStatus = Field(default=SessionGoalsStatus.OPEN, description="Trạng thái mục tiêu")


class SessionGoalCreate(CustomModel):
    goal: str = Field(..., description="Mục tiêu phiên học", max_length=255)
    status: Optional[SessionGoalsStatus] = Field(default=SessionGoalsStatus.OPEN, description="Trạng thái mục tiêu")


class SessionGoalUpdate(CustomModel):
    goal: Optional[str] = Field(None, description="Mục tiêu phiên học", max_length=255)
    status: Optional[SessionGoalsStatus] = Field(None, description="Trạng thái mục tiêu")


class SessionGoalResponse(SessionGoalBase):
    id: int = Field(..., description="ID mục tiêu phiên học")
    user_id: int = Field(..., description="ID người dùng")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True
