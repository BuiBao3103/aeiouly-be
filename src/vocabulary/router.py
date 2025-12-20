from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.vocabulary.service import VocabularyService
from src.vocabulary.dependencies import get_vocabulary_service
from src.vocabulary.schemas import (
    VocabularySetCreate, VocabularySetUpdate, VocabularySetResponse,
    VocabularyItemCreate, VocabularyItemResponse,
    FlashcardSessionResponse, MultipleChoiceSessionResponse,
    StudySessionCreate
)
from src.vocabulary.exceptions import (
    VocabularySetNotFoundException, VocabularyItemNotFoundException,
    DictionaryWordNotFoundException, VocabularyItemAlreadyExistsException,
    InsufficientVocabularyException
)
from src.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/vocabulary", tags=["Vocabulary"])


# Vocabulary Set endpoints
@router.post("/sets", response_model=VocabularySetResponse, status_code=status.HTTP_201_CREATED)
async def create_vocabulary_set(
    set_data: VocabularySetCreate,
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Tạo bộ từ vựng mới"""
    try:
        return await service.create_vocabulary_set(current_user.id, set_data, db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tạo bộ từ vựng: {str(e)}"
        )


@router.get("/sets", response_model=PaginatedResponse[VocabularySetResponse])
async def get_vocabulary_sets(
    page: int = Query(1, ge=1, description="Trang"),
    size: int = Query(10, ge=1, le=50, description="Kích thước trang"),
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách bộ từ vựng của người dùng"""
    try:
        pagination = PaginationParams(page=page, size=size)
        return await service.get_vocabulary_sets(current_user.id, db, pagination)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách bộ từ vựng: {str(e)}"
        )


@router.get("/sets/{set_id}", response_model=VocabularySetResponse)
async def get_vocabulary_set(
    set_id: int = Path(..., description="ID bộ từ vựng"),
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Lấy chi tiết bộ từ vựng"""
    try:
        return await service.get_vocabulary_set_by_id(current_user.id, set_id, db)
    except VocabularySetNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy bộ từ vựng: {str(e)}"
        )


@router.put("/sets/{set_id}", response_model=VocabularySetResponse)
async def update_vocabulary_set(
    set_id: int = Path(..., description="ID bộ từ vựng"),
    set_data: VocabularySetUpdate = None,
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật bộ từ vựng"""
    try:
        return await service.update_vocabulary_set(current_user.id, set_id, set_data, db)
    except VocabularySetNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi cập nhật bộ từ vựng: {str(e)}"
        )


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocabulary_set(
    set_id: int = Path(..., description="ID bộ từ vựng"),
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Xóa bộ từ vựng"""
    try:
        success = await service.delete_vocabulary_set(current_user.id, set_id, db)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy bộ từ vựng"
            )
    except VocabularySetNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xóa bộ từ vựng: {str(e)}"
        )


# Vocabulary Item endpoints
@router.post("/items", response_model=VocabularyItemResponse, status_code=status.HTTP_201_CREATED)
async def add_vocabulary_item(
    item_data: VocabularyItemCreate,
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Thêm từ vựng vào bộ từ vựng
    
    - **vocabulary_set_id**: ID bộ từ vựng (bỏ trống nếu muốn thêm vào bộ mặc định)
    - **dictionary_id**: ID từ trong từ điển
    - **use_default_set**: Thêm vào bộ từ vựng mặc định của user (nếu chưa có sẽ tự động tạo)
    """
    try:
        return await service.add_vocabulary_item(current_user.id, item_data, db)
    except (VocabularySetNotFoundException, DictionaryWordNotFoundException, VocabularyItemAlreadyExistsException) as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi thêm từ vựng: {str(e)}"
        )


@router.get("/sets/{set_id}/items", response_model=PaginatedResponse[VocabularyItemResponse])
async def get_vocabulary_items(
    set_id: int = Path(..., description="ID bộ từ vựng"),
    page: int = Query(1, ge=1, description="Trang"),
    size: int = Query(10, ge=1, le=50, description="Kích thước trang"),
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách từ vựng trong bộ"""
    try:
        pagination = PaginationParams(page=page, size=size)
        return await service.get_vocabulary_items(current_user.id, set_id, db, pagination)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách từ vựng: {str(e)}"
        )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vocabulary_item(
    item_id: int = Path(..., description="ID từ vựng"),
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Xóa từ vựng khỏi bộ"""
    try:
        success = await service.remove_vocabulary_item(current_user.id, item_id, db)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy từ vựng"
            )
    except VocabularyItemNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xóa từ vựng: {str(e)}"
        )


# Study endpoints
@router.post("/study/flashcard", response_model=FlashcardSessionResponse)
async def create_flashcard_session(
    session_data: StudySessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Tạo phiên học Flashcard"""
    try:
        return await service.create_flashcard_session(current_user.id, session_data, db)
    except (VocabularySetNotFoundException, InsufficientVocabularyException) as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tạo phiên học Flashcard: {str(e)}"
        )


@router.post("/study/multiple-choice", response_model=MultipleChoiceSessionResponse)
async def create_multiple_choice_session(
    session_data: StudySessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: VocabularyService = Depends(get_vocabulary_service),
    db: AsyncSession = Depends(get_db)
):
    """Tạo phiên học Multiple Choice"""
    try:
        return await service.create_multiple_choice_session(current_user.id, session_data, db)
    except (VocabularySetNotFoundException, InsufficientVocabularyException) as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tạo phiên học Multiple Choice: {str(e)}"
        )
