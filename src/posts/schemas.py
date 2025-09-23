from pydantic import Field, validator
from typing import Optional
from datetime import datetime
from src.models import CustomModel

# Constants for field descriptions
CONTENT_DESCRIPTION = "Nội dung bài viết"
PUBLISH_STATUS_DESCRIPTION = "Trạng thái xuất bản"

# Import UserResponse để sử dụng làm nested object
class AuthorResponse(CustomModel):
    id: int = Field(..., description="ID của tác giả")
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    full_name: Optional[str] = Field(None, max_length=100, description="Họ và tên đầy đủ")

class PostBase(CustomModel):
    content: str = Field(..., min_length=1, max_length=10000, description=CONTENT_DESCRIPTION)
    is_published: bool = Field(True, description=PUBLISH_STATUS_DESCRIPTION)

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Nội dung bài viết không được để trống')
        return v.strip()

class PostCreate(PostBase):
    """Schema cho việc tạo bài viết mới"""
    pass

class PostUpdate(CustomModel):
    """Schema cho việc cập nhật bài viết"""
    content: Optional[str] = Field(None, min_length=1, max_length=10000, description=CONTENT_DESCRIPTION)
    is_published: Optional[bool] = Field(None, description=PUBLISH_STATUS_DESCRIPTION)

    @validator('content')
    def validate_content(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Nội dung bài viết không được để trống')
        return v.strip() if v else v

class PostResponse(CustomModel):
    """Schema cho response bài viết"""
    id: int = Field(..., description="ID của bài viết")
    content: str = Field(..., description=CONTENT_DESCRIPTION)
    is_published: bool = Field(..., description=PUBLISH_STATUS_DESCRIPTION)
    image_url: Optional[str] = Field(None, description="URL hình ảnh đính kèm")
    author: AuthorResponse = Field(..., description="Thông tin tác giả")
    likes_count: int = Field(..., ge=0, description="Số lượng lượt thích")
    is_liked_by_user: Optional[bool] = Field(None, description="User đã like bài viết này chưa")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: Optional[datetime] = Field(None, description="Thời gian cập nhật cuối")

class PostListResponse(CustomModel):
    """Schema cho danh sách bài viết có phân trang"""
    items: list[PostResponse] = Field(..., description="Danh sách bài viết")
    total: int = Field(..., ge=0, description="Tổng số bài viết")
    page: int = Field(..., ge=1, description="Trang hiện tại")
    size: int = Field(..., ge=1, le=100, description="Số bài viết mỗi trang")
    pages: int = Field(..., ge=0, description="Tổng số trang")

class PostLikeResponse(CustomModel):
    """Schema cho response like/unlike bài viết"""
    post_id: int = Field(..., description="ID của bài viết")
    is_liked: bool = Field(..., description="Trạng thái like")
    likes_count: int = Field(..., ge=0, description="Số lượng lượt thích") 