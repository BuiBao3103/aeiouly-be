from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from src.posts.schemas import PostCreate, PostUpdate, PostResponse
from src.posts.service import PostService
from src.auth.dependencies import get_current_active_user
from src.auth.models import User
from src.pagination import PaginationParams, paginate
from src.database import get_db

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new post"""
    return await PostService.create_post(post_data, current_user, db)

@router.get("/", response_model=List[PostResponse])
async def get_posts(pagination: PaginationParams = Depends(), db: Session = Depends(get_db)):
    """Get all posts with pagination"""
    return await PostService.get_posts(pagination, db)

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific post by ID"""
    return await PostService.get_post_by_id(post_id, db)

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a post"""
    return await PostService.update_post(post_id, post_data, current_user, db)

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a post"""
    await PostService.delete_post(post_id, current_user, db)
    return {"message": "Xóa bài viết thành công"}

@router.get("/user/{user_id}", response_model=List[PostResponse])
async def get_user_posts(
    user_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db)
):
    """Get all posts by a specific user"""
    return await PostService.get_posts_by_user(user_id, pagination, db) 