"""
Router for Writing Practice module
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.writing.schemas import (
    WritingSessionCreate,
    WritingSessionResponse,
    WritingSessionListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    HintResponse,
    FinalEvaluationResponse,
    SessionCompleteRequest
)
from src.writing.service import WritingService
from src.writing.dependencies import get_writing_service
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.database import get_db
from src.pagination import PaginationParams, paginate, get_offset

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện viết"

router = APIRouter(prefix="/writing-sessions", tags=["Writing Practice"])

@router.post("/", response_model=WritingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_writing_session(
    session_data: WritingSessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Tạo phiên luyện viết mới"""
    try:
        return await service.create_writing_session(current_user.id, session_data, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo phiên luyện viết: {str(e)}"
        )

@router.get("/{session_id}", response_model=WritingSessionResponse)
async def get_writing_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Lấy thông tin phiên luyện viết"""
    session = await service.get_writing_session(session_id, current_user.id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_MSG
        )
    return session

@router.get("/")
async def get_writing_sessions(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các phiên luyện viết (có phân trang)"""
    try:
        sessions = service.get_user_writing_sessions(current_user.id, db)
        total = len(sessions)
        offset = get_offset(pagination.page, pagination.size)
        items = sessions[offset: offset + pagination.size]
        return paginate(items, total, pagination.page, pagination.size)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách phiên: {str(e)}"
        )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_writing_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Xóa phiên luyện viết"""
    success = service.delete_writing_session(session_id, current_user.id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_MSG
        )

@router.post("/{session_id}/complete", status_code=status.HTTP_200_OK)
async def complete_writing_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Kết thúc phiên luyện viết sớm"""
    success = service.complete_writing_session(session_id, current_user.id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_MSG
        )
    return {"message": "Phiên luyện viết đã được kết thúc"}

@router.post("/{session_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Gửi tin nhắn và nhận phản hồi từ chatbot"""
    try:
        return await service.send_chat_message(session_id, current_user.id, message_data, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi tin nhắn: {str(e)}"
        )

@router.get("/{session_id}/chat", response_model=List[ChatMessageResponse])
async def get_chat_history(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Lấy lịch sử chat của phiên"""
    try:
        return service.get_chat_history(session_id, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy lịch sử chat: {str(e)}"
        )

@router.get("/{session_id}/hint", response_model=HintResponse)
async def get_translation_hint(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Lấy gợi ý dịch cho câu hiện tại"""
    try:
        return await service.get_translation_hint(session_id, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy gợi ý: {str(e)}"
        )

@router.get("/{session_id}/final-evaluation", response_model=FinalEvaluationResponse)
async def get_final_evaluation(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Lấy đánh giá tổng thể của phiên"""
    try:
        return await service.get_final_evaluation(session_id, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy đánh giá: {str(e)}"
        )

@router.post("/{session_id}/skip", response_model=WritingSessionResponse)
async def skip_current_sentence(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: WritingService = Depends(get_writing_service),
    db: Session = Depends(get_db)
):
    """Bỏ qua câu hiện tại và chuyển sang câu tiếp theo"""
    try:
        return await service.skip_current_sentence(session_id, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi bỏ qua câu: {str(e)}"
        )
