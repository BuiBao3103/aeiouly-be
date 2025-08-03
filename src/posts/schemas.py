from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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
    author_id: int
    author_username: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    page: int
    size: int
    pages: int 