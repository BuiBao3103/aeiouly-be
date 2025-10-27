from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.pagination import PaginationParams, PaginatedResponse
from src.solo_study.service import SessionGoalService
from src.solo_study.schemas import SessionGoalCreate, SessionGoalUpdate, SessionGoalResponse
from src.solo_study.dependencies import get_session_goal_service
from src.solo_study.exceptions import (
    SessionGoalNotFoundException,
    SessionGoalValidationException,
    session_goal_not_found_exception,
    session_goal_validation_exception
)

router = APIRouter(prefix="/session-goals", tags=["Session Goals"])


@router.post("/", response_model=SessionGoalResponse)
async def create_session_goal(
    goal_data: SessionGoalCreate,
    current_user: User = Depends(get_current_active_user),
    service: SessionGoalService = Depends(get_session_goal_service),
    db: Session = Depends(get_db)
):
    """
    Tạo mục tiêu phiên học mới
    - **goal**: Mục tiêu phiên học
    - **status**: Trạng thái mục tiêu (OPEN hoặc COMPLETED, mặc định: OPEN)
    """
    try:
        return service.create_goal(goal_data, current_user.id, db)
    except SessionGoalValidationException as e:
        raise session_goal_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo mục tiêu phiên học: {str(e)}")


@router.get("/", response_model=PaginatedResponse[SessionGoalResponse])
async def get_session_goals(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (OPEN, COMPLETED)"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    service: SessionGoalService = Depends(get_session_goal_service),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách mục tiêu phiên học của người dùng với phân trang
    - **status**: Lọc theo trạng thái (OPEN, COMPLETED) - optional
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bản ghi mỗi trang (mặc định: 10, tối đa: 100)
    """
    try:
        return service.get_goals(current_user.id, db, pagination, status)
    except SessionGoalValidationException as e:
        raise session_goal_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách mục tiêu phiên học: {str(e)}")


@router.get("/{goal_id}", response_model=SessionGoalResponse)
async def get_session_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SessionGoalService = Depends(get_session_goal_service),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin mục tiêu phiên học theo ID
    - **goal_id**: ID của mục tiêu phiên học
    """
    try:
        return service.get_goal_by_id(goal_id, current_user.id, db)
    except SessionGoalNotFoundException as e:
        raise session_goal_not_found_exception(goal_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy mục tiêu phiên học: {str(e)}")


@router.put("/{goal_id}", response_model=SessionGoalResponse)
async def update_session_goal(
    goal_id: int,
    goal_data: SessionGoalUpdate,
    current_user: User = Depends(get_current_active_user),
    service: SessionGoalService = Depends(get_session_goal_service),
    db: Session = Depends(get_db)
):
    """
    Cập nhật mục tiêu phiên học
    - **goal_id**: ID của mục tiêu phiên học
    - **goal**: Mục tiêu phiên học (optional)
    - **status**: Trạng thái mục tiêu (OPEN hoặc COMPLETED) (optional)
    """
    try:
        return service.update_goal(goal_id, goal_data, current_user.id, db)
    except SessionGoalNotFoundException as e:
        raise session_goal_not_found_exception(goal_id)
    except SessionGoalValidationException as e:
        raise session_goal_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật mục tiêu phiên học: {str(e)}")


@router.delete("/{goal_id}")
async def delete_session_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SessionGoalService = Depends(get_session_goal_service),
    db: Session = Depends(get_db)
):
    """
    Xóa mục tiêu phiên học (soft delete)
    - **goal_id**: ID của mục tiêu phiên học
    """
    try:
        success = service.delete_goal(goal_id, current_user.id, db)
        if success:
            return {"message": f"Đã xóa mục tiêu phiên học với ID {goal_id}"}
        else:
            raise HTTPException(status_code=500, detail="Không thể xóa mục tiêu phiên học")
    except SessionGoalNotFoundException as e:
        raise session_goal_not_found_exception(goal_id)
    except SessionGoalValidationException as e:
        raise session_goal_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa mục tiêu phiên học: {str(e)}")

