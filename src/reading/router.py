from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.reading.service import ReadingService
from src.reading.schemas import (
    ReadingSessionCreate, ReadingSessionResponse, ReadingSessionSummary,
    ReadingSessionDetail, ReadingSessionFilter, SummarySubmission,
    SummaryFeedback, QuizGenerationRequest, QuizResponse,
    DiscussionGenerationRequest, DiscussionResponse
)
from src.reading.dependencies import get_reading_service
from src.reading.exceptions import (
    ReadingSessionNotFoundException, TextGenerationFailedException,
    TextAnalysisFailedException, SummaryEvaluationFailedException,
    QuizGenerationFailedException
)
from src.reading.models import ReadingLevel, ReadingGenre
from src.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="", tags=["Reading Practice"])

@router.post("/reading-sessions", response_model=ReadingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_reading_session(
    session_data: ReadingSessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Create a new reading session"""
    try:
        # Validate request
        if session_data.custom_text:
            # Custom text mode
            if session_data.level or session_data.genre or session_data.topic:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Khi sử dụng custom_text, không được cung cấp các trường khác"
                )
        else:
            # AI generation mode
            if not session_data.level or not session_data.genre:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Level và genre là bắt buộc cho AI generation"
                )
        
        session = await service.create_reading_session(current_user.id, session_data, db)
        return session
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TextGenerationFailedException as e:
        raise e
    except TextAnalysisFailedException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo phiên đọc: {str(e)}"
        )

@router.get("/reading-sessions", response_model=PaginatedResponse[ReadingSessionSummary])
async def get_reading_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    level: Optional[ReadingLevel] = Query(None, description="Filter by reading level"),
    genre: Optional[ReadingGenre] = Query(None, description="Filter by genre"),
    is_custom: Optional[bool] = Query(None, description="Filter by custom text"),
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Get paginated list of reading sessions"""
    try:
        filters = ReadingSessionFilter(
            level=level,
            genre=genre,
            is_custom=is_custom
        )
        
        pagination = PaginationParams(page=page, size=limit)
        
        sessions = service.get_reading_sessions(current_user.id, filters, pagination, db)
        return sessions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách phiên đọc: {str(e)}"
        )

@router.get("/reading-sessions/{session_id}", response_model=ReadingSessionDetail)
async def get_reading_session_detail(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Get reading session detail"""
    try:
        session = service.get_reading_session_detail(session_id, current_user.id, db)
        return session
        
    except ReadingSessionNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy chi tiết phiên đọc: {str(e)}"
        )

@router.post("/reading-sessions/{session_id}/submit-summary", response_model=SummaryFeedback)
async def submit_summary(
    session_id: int,
    summary_data: SummarySubmission,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Submit summary for evaluation (Vietnamese or English)"""
    try:
        feedback = await service.evaluate_summary(session_id, current_user.id, summary_data, db)
        return feedback
        
    except ReadingSessionNotFoundException as e:
        raise e
    except SummaryEvaluationFailedException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đánh giá bài tóm tắt: {str(e)}"
        )

@router.post("/reading-sessions/{session_id}/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    session_id: int,
    quiz_request: QuizGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Generate quiz from reading session"""
    try:
        quiz = await service.generate_quiz(session_id, current_user.id, quiz_request, db)
        return quiz
        
    except ReadingSessionNotFoundException as e:
        raise e
    except QuizGenerationFailedException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo bài trắc nghiệm: {str(e)}"
        )

@router.post("/reading-sessions/{session_id}/generate-discussion", response_model=DiscussionResponse)
async def generate_discussion(
    session_id: int,
    discussion_request: DiscussionGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Generate discussion questions from reading session"""
    try:
        discussion = await service.generate_discussion(session_id, current_user.id, discussion_request, db)
        return discussion
        
    except ReadingSessionNotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo câu hỏi thảo luận: {str(e)}"
        )

@router.delete("/reading-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ReadingService = Depends(get_reading_service),
    db: Session = Depends(get_db)
):
    """Soft delete a reading session"""
    success = service.delete_reading_session(session_id, current_user.id, db)
    if not success:
        raise ReadingSessionNotFoundException(f"Không tìm thấy phiên đọc {session_id}")
