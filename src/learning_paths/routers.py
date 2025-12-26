from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.auth.models import User

from src.learning_paths.schemas import (
    LearningPathForm,
    LearningPathResponse,
    DailyLessonPlanResponse,
    UserLessonProgressResponse,
    LessonStatusUpdateRequest,
)
from src.learning_paths.service import LearningPathService
from src.learning_paths.exceptions import (
    LearningPathNotFoundException,
    DailyLessonPlanNotFoundException,
    UserLessonProgressNotFoundException,
    LearningPathGenerationException,
    InvalidLessonStatusException,
    InvalidLessonIndexException,
)

router = APIRouter(prefix="/learning-paths", tags=["learning_paths"])

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

@router.post(
    "/lessons/{daily_lesson_plan_id}/start/{lesson_index}",
    response_model=UserLessonProgressResponse,
    summary="Start or resume a specific lesson within a daily lesson plan",
)
async def start_lesson_endpoint(
    daily_lesson_plan_id: int,
    lesson_index: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Starts or resumes a specific lesson for the authenticated user within a daily lesson plan.

    If the lesson has already been completed, it will return the existing progress. Otherwise, it will
    initialize or resume the user's progress for the specified lesson.
    
    Args:
        daily_lesson_plan_id: The ID of the daily lesson plan containing the lesson.
        lesson_index: The 0-based index of the lesson within the daily lesson plan's content.
        db: The asynchronous database session dependency.
        current_user: The authenticated user dependency.
        
    Returns:
        A `UserLessonProgressResponse` object representing the user's progress for the lesson.
        
    Raises:
        HTTPException 404: If the daily lesson plan is not found.
        HTTPException 400: If the lesson index is out of bounds or invalid.
        HTTPException 500: For unexpected internal server errors.
    """
    service = LearningPathService()
    try:
        progress = await service.start_lesson(
            daily_lesson_plan_id=daily_lesson_plan_id,
            lesson_index=lesson_index,
            user_id=current_user.id,
            db=db,
        )
        return progress
    except DailyLessonPlanNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily lesson plan not found")
    except InvalidLessonIndexException as e: # Catch generic LearningPathException for index out of bounds
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put(
    "/progress/{user_lesson_progress_id}",
    response_model=UserLessonProgressResponse,
    summary="Update the status and metadata of a user's lesson progress",
)
async def update_lesson_progress_endpoint(
    user_lesson_progress_id: int,
    update_data: LessonStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Updates the status and optional metadata of a user's lesson progress for the authenticated user.

    If the status is updated to 'done' and the `end_time` is not already set, it will be set to the current time.
    
    Args:
        user_lesson_progress_id: The ID of the user lesson progress to update.
        update_data: The `LessonStatusUpdateRequest` containing the new status and optional metadata.
        db: The asynchronous database session dependency.
        current_user: The authenticated user dependency.
        
    Returns:
        A `UserLessonProgressResponse` object representing the updated user's lesson progress.
        
    Raises:
        HTTPException 404: If the user lesson progress is not found for the current user.
        HTTPException 400: If an invalid lesson status is provided.
        HTTPException 500: For unexpected internal server errors.
    """
    service = LearningPathService()
    try:
        progress = await service.update_lesson_progress(
            user_lesson_progress_id=user_lesson_progress_id,
            user_id=current_user.id,
            update_data=update_data,
            db=db,
        )
        return progress
    except UserLessonProgressNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User lesson progress not found")
    except InvalidLessonStatusException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



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