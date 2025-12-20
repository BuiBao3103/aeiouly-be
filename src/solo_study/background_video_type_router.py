from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.pagination import PaginationParams, PaginatedResponse
from src.solo_study.service import BackgroundVideoTypeService
from src.solo_study.schemas import BackgroundVideoTypeCreate, BackgroundVideoTypeUpdate, BackgroundVideoTypeResponse
from src.solo_study.dependencies import get_background_video_type_service
from src.solo_study.exceptions import (
    BackgroundVideoTypeNotFoundException,
    BackgroundVideoTypeValidationException,
    background_video_type_not_found_exception,
    background_video_type_validation_exception
)

router = APIRouter(prefix="/background-video-types", tags=["Background Video Types"])


@router.post("/", response_model=BackgroundVideoTypeResponse)
async def create_background_video_type(
    type_data: BackgroundVideoTypeCreate,
    service: BackgroundVideoTypeService = Depends(get_background_video_type_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo loại video nền mới
    - **name**: Tên loại video nền
    - **description**: Mô tả loại video nền (optional)
    """
    try:
        return await service.create_type(type_data, db)
    except BackgroundVideoTypeValidationException as e:
        raise background_video_type_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo loại video nền: {str(e)}")


@router.get("/", response_model=PaginatedResponse[BackgroundVideoTypeResponse])
async def get_background_video_types(
    pagination: PaginationParams = Depends(),
    service: BackgroundVideoTypeService = Depends(get_background_video_type_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách loại video nền với phân trang
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bản ghi mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        return await service.get_types(db, pagination)
    except BackgroundVideoTypeValidationException as e:
        raise background_video_type_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách loại video nền: {str(e)}")


@router.get("/{type_id}", response_model=BackgroundVideoTypeResponse)
async def get_background_video_type(
    type_id: int,
    service: BackgroundVideoTypeService = Depends(get_background_video_type_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thông tin loại video nền theo ID
    - **type_id**: ID của loại video nền
    """
    try:
        return await service.get_type_by_id(type_id, db)
    except BackgroundVideoTypeNotFoundException as e:
        raise background_video_type_not_found_exception(type_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy loại video nền: {str(e)}")


@router.put("/{type_id}", response_model=BackgroundVideoTypeResponse)
async def update_background_video_type(
    type_id: int,
    type_data: BackgroundVideoTypeUpdate,
    service: BackgroundVideoTypeService = Depends(get_background_video_type_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật loại video nền
    - **type_id**: ID của loại video nền
    - **name**: Tên loại video nền (optional)
    - **description**: Mô tả loại video nền (optional)
    """
    try:
        return await service.update_type(type_id, type_data, db)
    except BackgroundVideoTypeNotFoundException as e:
        raise background_video_type_not_found_exception(type_id)
    except BackgroundVideoTypeValidationException as e:
        raise background_video_type_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật loại video nền: {str(e)}")


@router.delete("/{type_id}")
async def delete_background_video_type(
    type_id: int,
    service: BackgroundVideoTypeService = Depends(get_background_video_type_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa loại video nền (soft delete)
    - **type_id**: ID của loại video nền
    """
    try:
        success = await service.delete_type(type_id, db)
        if success:
            return {"message": f"Đã xóa loại video nền với ID {type_id}"}
        else:
            raise HTTPException(status_code=500, detail="Không thể xóa loại video nền")
    except BackgroundVideoTypeNotFoundException as e:
        raise background_video_type_not_found_exception(type_id)
    except BackgroundVideoTypeValidationException as e:
        raise background_video_type_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa loại video nền: {str(e)}")

