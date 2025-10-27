from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.pagination import PaginationParams, PaginatedResponse
from src.solo_study.service import BackgroundVideoService
from src.solo_study.schemas import BackgroundVideoCreate, BackgroundVideoUpdate, BackgroundVideoResponse
from src.solo_study.dependencies import get_background_video_service
from src.solo_study.exceptions import (
    BackgroundVideoNotFoundException,
    BackgroundVideoValidationException,
    background_video_not_found_exception,
    background_video_validation_exception
)

router = APIRouter(prefix="/background-videos", tags=["Background Videos"])


@router.post("/", response_model=BackgroundVideoResponse)
async def create_background_video(
    video_data: BackgroundVideoCreate,
    service: BackgroundVideoService = Depends(get_background_video_service),
    db: Session = Depends(get_db)
):
    """
    Tạo video nền mới
    - **youtube_url**: URL video YouTube
    - **image_url**: URL hình ảnh (optional)
    - **type_id**: ID loại video nền
    """
    try:
        return service.create_video(video_data, db)
    except BackgroundVideoValidationException as e:
        raise background_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo video nền: {str(e)}")


@router.get("/", response_model=PaginatedResponse[BackgroundVideoResponse])
async def get_background_videos(
    pagination: PaginationParams = Depends(),
    service: BackgroundVideoService = Depends(get_background_video_service),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách video nền với phân trang
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bản ghi mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        return service.get_videos(db, pagination)
    except BackgroundVideoValidationException as e:
        raise background_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách video nền: {str(e)}")


@router.get("/{video_id}", response_model=BackgroundVideoResponse)
async def get_background_video(
    video_id: int,
    service: BackgroundVideoService = Depends(get_background_video_service),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin video nền theo ID
    - **video_id**: ID của video nền
    """
    try:
        return service.get_video_by_id(video_id, db)
    except BackgroundVideoNotFoundException as e:
        raise background_video_not_found_exception(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy video nền: {str(e)}")


@router.put("/{video_id}", response_model=BackgroundVideoResponse)
async def update_background_video(
    video_id: int,
    video_data: BackgroundVideoUpdate,
    service: BackgroundVideoService = Depends(get_background_video_service),
    db: Session = Depends(get_db)
):
    """
    Cập nhật video nền
    - **video_id**: ID của video nền
    - **youtube_url**: URL video YouTube (optional)
    - **image_url**: URL hình ảnh (optional)
    - **type_id**: ID loại video nền (optional)
    """
    try:
        return service.update_video(video_id, video_data, db)
    except BackgroundVideoNotFoundException as e:
        raise background_video_not_found_exception(video_id)
    except BackgroundVideoValidationException as e:
        raise background_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật video nền: {str(e)}")


@router.delete("/{video_id}")
async def delete_background_video(
    video_id: int,
    service: BackgroundVideoService = Depends(get_background_video_service),
    db: Session = Depends(get_db)
):
    """
    Xóa video nền (soft delete)
    - **video_id**: ID của video nền
    """
    try:
        success = service.delete_video(video_id, db)
        if success:
            return {"message": f"Đã xóa video nền với ID {video_id}"}
        else:
            raise HTTPException(status_code=500, detail="Không thể xóa video nền")
    except BackgroundVideoNotFoundException as e:
        raise background_video_not_found_exception(video_id)
    except BackgroundVideoValidationException as e:
        raise background_video_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa video nền: {str(e)}")

