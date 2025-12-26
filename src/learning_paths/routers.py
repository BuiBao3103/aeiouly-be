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
from src.learning_paths.dependencies import get_learning_path_service
from fastapi import APIRouter, Depends, BackgroundTasks # Thêm BackgroundTasks

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])



@router.post("/", response_model=LearningPathResponse)
async def generate_learning_path(
    form_data: LearningPathForm,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: LearningPathService = Depends(get_learning_path_service)
):
    lp_response = await service.generate_learning_path(current_user.id, form_data, db)
    
    background_tasks.add_task(
        service.run_generation_pipeline_background, 
        lp_response.id, 
        current_user.id
    )
    
    return lp_response

@router.get("/{learning_path_id}/status")
async def get_learning_path_status(
    learning_path_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: LearningPathService = Depends(get_learning_path_service)
):
    """
    Endpoint để Frontend kiểm tra trạng thái lộ trình sau khi gọi API tạo.
    """
    return await service.get_learning_path_status(learning_path_id, current_user.id, db)

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