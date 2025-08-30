from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Import UserResponse để sử dụng làm nested object
class AuthorResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    is_published: bool = True

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    is_published: Optional[bool] = None

class PostResponse(PostBase):
    id: int
    author: AuthorResponse  # Nested author object thay vì flat fields
    likes_count: int
    is_liked_by_user: Optional[bool] = None  # Sẽ được set nếu user đã đăng nhập
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    size: int
    pages: int

class PostLikeResponse(BaseModel):
    post_id: int
    is_liked: bool
    likes_count: int 