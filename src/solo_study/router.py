from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.pagination import PaginationParams, PaginatedResponse, paginate
from src.solo_study.service import SoundService
from src.solo_study.schemas import SoundCreate, SoundUpdate, SoundResponse, SoundUploadResponse
from src.solo_study.dependencies import get_sound_service
from src.solo_study.exceptions import (
    SoundException,
    SoundNotFoundException,
    SoundValidationException,
    SoundUploadException,
    SoundDeleteException,
    sound_not_found_exception,
    sound_validation_exception,
    sound_upload_exception,
    sound_delete_exception
)

router = APIRouter(prefix="/sounds", tags=["Sounds"])


@router.post("/", response_model=SoundResponse)
async def create_sound(
    sound_data: SoundCreate,
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo âm thanh mới
    - **name**: Tên âm thanh (có thể chứa ký tự đặc biệt như 🌸 Anime)
    - **Lưu ý**: sound_file_url, file_size, duration sẽ được set khi upload file
    """
    try:
        return await service.create_sound(sound_data, db)
    except SoundValidationException as e:
        raise sound_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo âm thanh: {str(e)}")


@router.get("/", response_model=PaginatedResponse[SoundResponse])
async def get_sounds(
    pagination: PaginationParams = Depends(),
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách âm thanh với phân trang
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bản ghi mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        return await service.get_sounds(db, pagination)
    except SoundValidationException as e:
        raise sound_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách âm thanh: {str(e)}")


@router.get("/{sound_id}", response_model=SoundResponse)
async def get_sound(
    sound_id: int,
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thông tin âm thanh theo ID
    - **sound_id**: ID của âm thanh
    """
    try:
        return await service.get_sound_by_id(sound_id, db)
    except SoundNotFoundException as e:
        raise sound_not_found_exception(sound_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy âm thanh: {str(e)}")


@router.put("/{sound_id}", response_model=SoundResponse)
async def update_sound(
    sound_id: int,
    sound_data: SoundUpdate,
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật tên âm thanh
    - **sound_id**: ID của âm thanh
    - **name**: Tên âm thanh (optional)
    - **Lưu ý**: file_size và duration sẽ được cập nhật tự động khi upload file
    """
    try:
        return await service.update_sound(sound_id, sound_data, db)
    except SoundNotFoundException as e:
        raise sound_not_found_exception(sound_id)
    except SoundValidationException as e:
        raise sound_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật âm thanh: {str(e)}")


@router.delete("/{sound_id}")
async def delete_sound(
    sound_id: int,
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa âm thanh (soft delete)
    - **sound_id**: ID của âm thanh
    """
    try:
        success = await service.delete_sound(sound_id, db)
        if success:
            return {"message": f"Đã xóa âm thanh với ID {sound_id}"}
        else:
            raise HTTPException(status_code=500, detail="Không thể xóa âm thanh")
    except SoundNotFoundException as e:
        raise sound_not_found_exception(sound_id)
    except SoundDeleteException as e:
        raise sound_delete_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa âm thanh: {str(e)}")


@router.post("/{sound_id}/upload", response_model=SoundUploadResponse)
async def upload_sound_file(
    sound_id: int,
    sound_file: UploadFile = File(..., description="File âm thanh (audio/*)"),
    service: SoundService = Depends(get_sound_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload file âm thanh lên AWS S3
    - **sound_id**: ID của âm thanh
    - **sound_file**: File âm thanh (phải là audio/*)
    """
    try:
        return await service.upload_sound_file(sound_id, sound_file, db)
    except SoundNotFoundException as e:
        raise sound_not_found_exception(sound_id)
    except SoundUploadException as e:
        raise sound_upload_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload file âm thanh: {str(e)}")


