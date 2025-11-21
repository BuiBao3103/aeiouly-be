"""
FastAPI router for Listening module
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.listening.service import ListeningService
from src.listening.schemas import (
    LessonUpload, LessonUpdate, LessonResponse, LessonDetailResponse,
    SessionCreate, SessionResponse, SessionDetailResponse, SessionNextResponse,
    ProgressSubmit, ProgressStats, SessionCompleteResponse,
    LessonFilter, UserSessionResponse
)
from src.pagination import PaginationParams, PaginatedResponse
from src.listening.exceptions import (
    LessonNotFoundException, LessonCreationFailedException,
    SessionNotFoundException, SessionAlreadyCompletedException,
    InvalidSRTContentException, TranslationFailedException,
    DifficultyAnalysisFailedException, SessionCreationFailedException,
    ProgressUpdateFailedException, SessionCompletionFailedException
)

router = APIRouter(prefix="", tags=["Listening Practice"])

LESSON_NOT_FOUND = "Không tìm thấy bài học"
LESSON_CREATE_ERROR = "Lỗi khi tạo bài học"
LESSON_UPDATE_ERROR = "Lỗi khi cập nhật bài học"
LESSON_DELETE_ERROR = "Lỗi khi xóa bài học"
LESSON_GET_ERROR = "Lỗi khi lấy danh sách bài học"
LESSON_DETAIL_ERROR = "Lỗi khi lấy chi tiết bài học"
SESSION_CREATE_ERROR = "Lỗi khi tạo phiên học"
SESSION_GET_ERROR = "Lỗi khi lấy thông tin phiên học"
SESSION_PROGRESS_ERROR = "Lỗi khi cập nhật tiến độ"
SESSION_COMPLETE_ERROR = "Lỗi khi hoàn thành phiên học"

def get_listening_service() -> ListeningService:
    return ListeningService()

# Lesson endpoints
@router.post("/listen-lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    title: str = Form(...),
    youtube_url: str = Form(...),
    srt_file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Upload SRT file and create listening lesson"""
    try:
        # Read SRT file content
        srt_content = await srt_file.read()
        srt_content = srt_content.decode('utf-8')
        
        # Create lesson data
        lesson_data = LessonUpload(
            lesson_data={
                "title": title,
                "youtube_url": youtube_url
            },
            srt_content=srt_content
        )
        
        lesson = await service.create_lesson(lesson_data, db)
        return lesson
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo bài học: {str(e)}"
        )

@router.get("/listen-lessons", response_model=PaginatedResponse[LessonResponse])
def get_lessons(
    level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Get paginated list of lessons with filters"""
    try:
        filters = LessonFilter(
            level=level,
            search=search
        )
        
        pagination = PaginationParams(page=page, size=size)
        
        result = service.get_lessons(filters, pagination, db)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách bài học: {str(e)}"
        )

@router.put("/listen-lessons/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Update a listening lesson"""
    try:
        lesson = service.update_lesson(lesson_id, lesson_data, db)
        return lesson
    except LessonNotFoundException as e:
        raise e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi cập nhật bài học: {str(e)}"
        )

@router.delete("/listen-lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Delete a listening lesson"""
    try:
        success = service.delete_lesson(lesson_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=LESSON_NOT_FOUND
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa bài học: {str(e)}"
        )

@router.get("/listen-lessons/{lesson_id}", response_model=LessonDetailResponse)
def get_lesson_detail(
    lesson_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Get lesson detail with all sentences"""
    lesson = service.get_lesson_detail(lesson_id, db)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return lesson

# Session endpoints (renamed to /listening-sessions)
@router.post("/listening-sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Create a new listening session"""
    try:
        session = service.create_session(current_user.id, session_data, db)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo phiên học: {str(e)}"
        )

@router.get("/listening-sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Get session detail with current sentence"""
    session = service.get_session(session_id, current_user.id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session

@router.post("/listening-sessions/{session_id}/next", response_model=SessionNextResponse)
def get_next_sentence(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Move to next sentence and return session detail with current sentence"""
    try:
        session_detail = service.get_next_sentence(session_id, current_user.id, db)
        return session_detail
    except SessionNotFoundException as e:
        raise e
    except SessionAlreadyCompletedException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chuyển sang câu tiếp theo: {str(e)}"
        )

@router.get("/listening-sessions", response_model=PaginatedResponse[UserSessionResponse])
def get_user_sessions(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_active_user),
    service: ListeningService = Depends(get_listening_service),
    db: Session = Depends(get_db)
):
    """Get all active sessions for the current user with pagination"""
    try:
        pagination = PaginationParams(page=page, size=size)
        sessions = service.get_user_sessions(current_user.id, pagination, db)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách phiên học: {str(e)}"
        )

