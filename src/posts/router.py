from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from src.posts.schemas import PostCreate, PostUpdate, PostResponse, PostLikeResponse, PostListResponse
from src.posts.service import PostService
from src.posts.dependencies import get_post_service
from src.auth.dependencies import get_current_active_user, get_current_user_optional
from src.users.models import User, UserRole
from src.pagination import PaginationParams, paginate
from src.database import get_db
from src.posts.exceptions import PostException

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Tạo bài viết mới
    
    - **content**: Nội dung bài viết (1-10000 ký tự)
    - **is_published**: Trạng thái xuất bản (mặc định: true)
    
    Chỉ admin mới có thể tạo bài viết.
    """
    try:
        return await service.create_post(post_data, current_user, db)
    except (PostException, HTTPException) as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo bài viết: {str(e)}"
        )

@router.get("/", response_model=PostListResponse)
async def get_posts(
    pagination: PaginationParams = Depends(), 
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách bài viết có phân trang
    
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bài viết mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        posts_with_likes = await service.get_posts_with_like_info(pagination, current_user, db)
        total = await service.get_total_posts_count(db)
        
        return paginate(
            posts_with_likes,
            total,
            pagination.page,
            pagination.size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách bài viết: {str(e)}"
        )

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int, 
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chi tiết bài viết theo ID
    
    - **post_id**: ID của bài viết
    """
    try:
        return await service.get_post_by_id_with_like_info(post_id, current_user, db)
    except (PostException, HTTPException) as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy bài viết: {str(e)}"
        )

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Cập nhật bài viết
    
    - **post_id**: ID của bài viết
    - **content**: Nội dung mới (tùy chọn)
    - **is_published**: Trạng thái xuất bản mới (tùy chọn)
    
    Chỉ tác giả hoặc admin mới có thể cập nhật.
    """
    try:
        return await service.update_post(post_id, post_data, current_user, db)
    except (PostException, HTTPException) as e:
        # Re-raise known HTTP errors (e.g., 404 Not Found, 403 Forbidden)
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi cập nhật bài viết: {str(e)}"
        )

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Xóa bài viết
    
    - **post_id**: ID của bài viết
    
    Chỉ tác giả hoặc admin mới có thể xóa.
    """
    try:
        await service.delete_post(post_id, current_user, db)
    except (PostException, HTTPException) as e:
        # Re-raise known HTTP errors (e.g., 404 Not Found, 403 Forbidden)
        raise e
    except Exception as e:
        # Unexpected errors -> 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa bài viết: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=PostListResponse)
async def get_user_posts(
    user_id: int,
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách bài viết của một user cụ thể
    
    - **user_id**: ID của user
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bài viết mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        posts_with_likes = await service.get_posts_by_user_with_like_info(user_id, pagination, current_user, db)
        total = await service.get_user_posts_count(user_id, db)
        return paginate(
            posts_with_likes,
            total,
            pagination.page,
            pagination.size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy bài viết của user: {str(e)}"
        )

@router.post("/{post_id}/like", response_model=PostLikeResponse)
async def toggle_post_like(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Like hoặc unlike một bài viết
    
    - **post_id**: ID của bài viết
    
    Nếu đã like thì sẽ unlike và ngược lại.
    """
    try:
        result = await service.like_post(post_id, current_user, db)
        return PostLikeResponse(
            post_id=post_id,
            is_liked=result.is_liked_by_user,
            likes_count=result.likes_count
        )
    except (PostException, HTTPException) as e:
        # Re-raise known HTTP errors (e.g., 404 Not Found)
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi like/unlike bài viết: {str(e)}"
        ) 

@router.post("/{post_id}/image", response_model=PostResponse)
async def upload_post_image(
    post_id: int,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Upload hình ảnh cho bài viết. Chỉ tác giả hoặc admin được phép.
    """
    try:
        return await service.upload_post_image(post_id, image, current_user, db)
    except (PostException, HTTPException) as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload hình ảnh: {str(e)}")

@router.get("/admin/all", response_model=PostListResponse)
async def get_all_posts_admin(
    pagination: PaginationParams = Depends(),
    include_draft: Optional[bool] = Query(None, description="True: chỉ lấy nháp, False: chỉ lấy đã xuất bản, None: lấy tất cả"),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(get_post_service),
    db: Session = Depends(get_db)
):
    """
    Lấy tất cả bài viết (bao gồm nháp) - Chỉ admin mới có thể truy cập
    
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bài viết mỗi trang (mặc định: 10, tối đa: 100)
    - **include_draft**: 
        - `True`: Chỉ lấy bài viết nháp (is_published = false)
        - `False`: Chỉ lấy bài viết đã xuất bản (is_published = true)
        - `None`: Lấy tất cả bài viết (cả nháp và đã xuất bản)
    """
    # Check if user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có thể xem tất cả bài viết"
        )
    
    try:
        posts_with_likes = await service.get_all_posts_admin_with_like_info(
            pagination, current_user, db, include_draft
        )
        total = await service.get_total_all_posts_count_admin(db, include_draft)
        
        return paginate(
            posts_with_likes,
            total,
            pagination.page,
            pagination.size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách bài viết: {str(e)}"
        )