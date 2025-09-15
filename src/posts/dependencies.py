from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.posts.models import Post
from src.database import get_db
from src.auth.models import User, UserRole
from src.auth.dependencies import get_current_active_user
from src.posts.exceptions import PostNotFoundException, InsufficientPermissionsException

def get_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
) -> Post:
    """
    Lấy bài viết theo ID hoặc raise 404 nếu không tìm thấy
    
    Args:
        post_id: ID của bài viết
        db: Database session
        
    Returns:
        Post: Bài viết được tìm thấy
        
    Raises:
        PostNotFoundException: Nếu không tìm thấy bài viết
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise PostNotFoundException()
    return post

def get_post_owner_or_403(
    post: Post = Depends(get_post_or_404),
    current_user: User = Depends(get_current_active_user)
) -> Post:
    """
    Kiểm tra quyền sở hữu bài viết
    
    Args:
        post: Bài viết cần kiểm tra
        current_user: User hiện tại
        
    Returns:
        Post: Bài viết nếu có quyền
        
    Raises:
        InsufficientPermissionsException: Nếu không có quyền
    """
    # Admin có thể chỉnh sửa mọi bài viết
    if current_user.role == UserRole.ADMIN:
        return post
    
    # Tác giả có thể chỉnh sửa bài viết của mình
    if post.author_id != current_user.id:
        raise InsufficientPermissionsException("Bạn chỉ có thể chỉnh sửa bài viết của chính mình")
    return post

def get_published_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
) -> Post:
    """
    Lấy bài viết đã xuất bản theo ID hoặc raise 404
    
    Args:
        post_id: ID của bài viết
        db: Database session
        
    Returns:
        Post: Bài viết đã xuất bản
        
    Raises:
        PostNotFoundException: Nếu không tìm thấy hoặc chưa xuất bản
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.is_published == True
    ).first()
    if not post:
        raise PostNotFoundException()
    return post

def get_post_with_permission_check(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Post:
    """
    Lấy bài viết với kiểm tra quyền truy cập
    
    - Admin: Có thể xem mọi bài viết
    - Tác giả: Có thể xem bài viết của mình (kể cả chưa xuất bản)
    - User khác: Chỉ xem được bài viết đã xuất bản
    """
    post = get_post_or_404(post_id, db)
    
    # Admin có thể xem mọi bài viết
    if current_user.role == UserRole.ADMIN:
        return post
    
    # Tác giả có thể xem bài viết của mình
    if post.author_id == current_user.id:
        return post
    
    # User khác chỉ xem được bài viết đã xuất bản
    if not post.is_published:
        raise PostNotFoundException()
    
    return post 