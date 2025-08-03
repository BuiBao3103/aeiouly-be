from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.posts.models import Post
from src.database import get_db
from src.auth.models import User
from src.auth.dependencies import get_current_active_user

async def get_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
) -> Post:
    """Get post by ID or raise 404 if not found"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bài viết"
        )
    return post

async def get_post_owner_or_403(
    post: Post = Depends(get_post_or_404),
    current_user: User = Depends(get_current_active_user)
) -> Post:
    """Check if current user is the owner of the post"""
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không đủ quyền để chỉnh sửa bài viết này"
        )
    return post

async def get_published_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
) -> Post:
    """Get published post by ID or raise 404 if not found"""
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.is_published == True
    ).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bài viết"
        )
    return post 