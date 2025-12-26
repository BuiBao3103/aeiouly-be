from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.auth.models import User

from src.learning_paths.schemas import (
    LearningPathForm,
    LearningPathResponse,
    UserLessonProgressResponse,
    LessonStartRequest
)
from src.learning_paths.service import LearningPathService
from src.learning_paths.exceptions import (
    LearningPathNotFoundException,
    LearningPathGenerationException,
)

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])

@router.post(
    "/",
    response_model=LearningPathResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new personalized learning path for the user",
)
async def generate_learning_path_endpoint(
    form_data: LearningPathForm,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generates a new personalized learning path for the authenticated user.

    The learning path is created based on the preferences provided in the `form_data`.
    
    Args:
        form_data: The `LearningPathForm` containing user preferences for the learning path.
        db: The asynchronous database session dependency.
        current_user: The authenticated user dependency.
        
    Returns:
        A `LearningPathResponse` object representing the newly generated learning path.
        
    Raises:
        HTTPException 400: If the learning path generation fails due to invalid input or agent issues.
        HTTPException 500: For unexpected internal server errors.
    """
    service = LearningPathService()
    try:
        learning_path = await service.generate_learning_path(
            user_id=current_user.id,
            form_data=form_data,
            db=db,
        )
        return learning_path
    except LearningPathGenerationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/progress/{user_lesson_progress_id}/start", response_model=UserLessonProgressResponse)
async def start_lesson(
    user_lesson_progress_id: int,
    data: LessonStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """API bắt đầu bài học (Sử dụng ID tiến độ cụ thể)"""
    service = LearningPathService()
    return await service.start_lesson(
        user_lesson_progress_id, 
        current_user.id, 
        db, 
        data.session_id
    )
@router.post("/progress/{user_lesson_progress_id}/complete", response_model=UserLessonProgressResponse)
async def complete_lesson(
    user_lesson_progress_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService()
    return await service.complete_lesson(user_lesson_progress_id, current_user.id, db)

@router.get("/me", response_model=LearningPathResponse)
async def get_my_learning_path(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService()
    
    lp = await service.get_current_learning_path(current_user.id, db)
    if not lp:
        raise LearningPathNotFoundException("Bạn chưa tạo lộ trình học tập nào.")
    return lp