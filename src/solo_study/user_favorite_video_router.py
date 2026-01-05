from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.pagination import PaginationParams, PaginatedResponse
from src.users.models import User
from src.auth.dependencies import get_current_active_user
from src.solo_study.service import UserFavoriteVideoService
from src.solo_study.schemas import UserFavoriteVideoCreate, UserFavoriteVideoUpdate, UserFavoriteVideoResponse
from src.solo_study.dependencies import get_user_favorite_video_service
from src.solo_study.exceptions import (
    UserFavoriteVideoNotFoundException,
    UserFavoriteVideoValidationException,
    UserFavoriteVideoAlreadyExistsException,
    user_favorite_video_not_found_exception,
    user_favorite_video_validation_exception,
    user_favorite_video_already_exists_exception
)

router = APIRouter(prefix="/user-favorite-videos", tags=["User Favorite Videos"])


@router.post("/", response_model=UserFavoriteVideoResponse)
async def create_user_favorite_video(
    video_data: UserFavoriteVideoCreate,
    current_user: User = Depends(get_current_active_user),
    service: UserFavoriteVideoService = Depends(get_user_favorite_video_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Thêm video YouTube vào danh sách yêu thích
    - **youtube_url**: URL video YouTube
    - **Lưu ý**: Hệ thống sẽ tự động lấy thông tin video (tên, tác giả, hình ảnh) từ YouTube
    """
    try:
        return await service.create_favorite_video(video_data, current_user.id, db)
    except UserFavoriteVideoAlreadyExistsException as e:
        raise user_favorite_video_already_exists_exception(str(e))
    except UserFavoriteVideoValidationException as e:
        raise user_favorite_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo video yêu thích: {str(e)}")


@router.get("/", response_model=PaginatedResponse[UserFavoriteVideoResponse])
async def get_user_favorite_videos(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    service: UserFavoriteVideoService = Depends(get_user_favorite_video_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách video yêu thích của người dùng hiện tại
    - **page**: Số trang (mặc định: 1)
    - **size**: Số lượng video mỗi trang (mặc định: 20)
    """
    try:
        return await service.get_favorite_videos(current_user.id, db, pagination)
    except UserFavoriteVideoValidationException as e:
        raise user_favorite_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách video yêu thích: {str(e)}")


@router.get("/{video_id}", response_model=UserFavoriteVideoResponse)
async def get_user_favorite_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    service: UserFavoriteVideoService = Depends(get_user_favorite_video_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy chi tiết video yêu thích theo ID
    - **video_id**: ID của video yêu thích
    """
    try:
        return await service.get_favorite_video_by_id(video_id, current_user.id, db)
    except UserFavoriteVideoNotFoundException as e:
        raise user_favorite_video_not_found_exception(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy video yêu thích: {str(e)}")


@router.put("/{video_id}", response_model=UserFavoriteVideoResponse)
async def update_user_favorite_video(
    video_id: int,
    video_data: UserFavoriteVideoUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserFavoriteVideoService = Depends(get_user_favorite_video_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật thông tin video yêu thích
    - **video_id**: ID của video yêu thích
    - **name**: Tên video (tùy chọn)
    """
    try:
        return await service.update_favorite_video(video_id, video_data, current_user.id, db)
    except UserFavoriteVideoNotFoundException as e:
        raise user_favorite_video_not_found_exception(video_id)
    except UserFavoriteVideoValidationException as e:
        raise user_favorite_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật video yêu thích: {str(e)}")


@router.delete("/{video_id}")
async def delete_user_favorite_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    service: UserFavoriteVideoService = Depends(get_user_favorite_video_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa video yêu thích (soft delete)
    - **video_id**: ID của video yêu thích
    """
    try:
        success = await service.delete_favorite_video(video_id, current_user.id, db)
        if success:
            return {"message": "Xóa video yêu thích thành công"}
    except UserFavoriteVideoNotFoundException as e:
        raise user_favorite_video_not_found_exception(video_id)
    except UserFavoriteVideoValidationException as e:
        raise user_favorite_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa video yêu thích: {str(e)}")

