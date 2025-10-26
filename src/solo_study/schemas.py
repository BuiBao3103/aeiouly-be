from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.models import CustomModel

# Constants for field descriptions
FILE_SIZE_DESC = "Kích thước file (bytes)"
DURATION_DESC = "Thời lượng (seconds)"


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
