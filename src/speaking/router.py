"""Router for Speaking module"""
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from typing import Optional
from src.database import get_db
from sqlalchemy.orm import Session
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from typing import List

from src.speaking.schemas import (
    SpeechToTextResponse,
    SpeakingSessionCreate,
    SpeakingSessionResponse,
    SpeakingSessionListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    HintResponse,
    FinalEvaluationResponse
)
from src.speaking.service import SpeakingService
from src.speaking.dependencies import get_speaking_service
from src.speaking.exceptions import SpeechToTextException, speech_to_text_exception
from src.pagination import PaginationParams, paginate, get_offset

# Constants
SESSION_NOT_FOUND_MSG = "Không tìm thấy phiên luyện nói"

router = APIRouter(
    prefix="/speaking-sessions",
    tags=["Speaking Practice"]
)


@router.post("/", response_model=SpeakingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_speaking_session(
    session_data: SpeakingSessionCreate,
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Tạo phiên luyện nói mới"""
    try:
        return await service.create_speaking_session(current_user.id, session_data, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo phiên luyện nói: {str(e)}"
        )


@router.get("/{session_id}", response_model=SpeakingSessionResponse)
async def get_speaking_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Lấy thông tin phiên luyện nói"""
    session = await service.get_speaking_session(session_id, current_user.id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_MSG
        )
    return session


@router.get("/")
async def get_speaking_sessions(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các phiên luyện nói (có phân trang)"""
    try:
        sessions = service.get_user_speaking_sessions(current_user.id, db)
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
async def delete_speaking_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Xóa phiên luyện nói"""
    success = service.delete_speaking_session(session_id, current_user.id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SESSION_NOT_FOUND_MSG
        )


@router.post("/{session_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: int,
    content: Optional[str] = Form(None, description="Text content (required if audio_file is not provided)"),
    audio_file: Optional[UploadFile] = File(None, description="File âm thanh (max 10MB, max 60s) - required if content is not provided"),
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """
    Gửi tin nhắn (text hoặc audio) và nhận phản hồi từ AI (tiếng Anh)
    
    **Yêu cầu:**
    - Phải cung cấp một trong hai: `content` (text) hoặc `audio_file` (file âm thanh)
    - File âm thanh: tối đa 10MB, tối đa 60 giây
    
    **Định dạng hỗ trợ:** WebM, OGG, WAV, MP3, M4A, FLAC
    
    **Tham số:**
    - **content**: Nội dung text (bắt buộc nếu không có audio_file)
    - **audio_file**: File âm thanh (bắt buộc nếu không có content)
    
    **Trả về:** Phản hồi từ AI bằng tiếng Anh
    """
    try:
        # Validate that at least one is provided
        if not content and not audio_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phải cung cấp 'content' (text) hoặc 'audio_file' (file âm thanh)"
            )
        
        # Create message data object
        from src.speaking.schemas import ChatMessageCreate
        message_data = ChatMessageCreate(
            content=content,
            audio_file=None  # Will be passed separately
        )
        
        return await service.send_chat_message(session_id, current_user.id, message_data, audio_file, db)
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
    service: SpeakingService = Depends(get_speaking_service),
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
async def get_conversation_hint(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Lấy gợi ý cho câu trả lời dựa trên tin nhắn cuối của AI (tiếng Việt)"""
    try:
        return await service.get_conversation_hint(session_id, current_user.id, db)
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
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """Lấy đánh giá tổng thể của phiên luyện nói"""
    try:
        return await service.get_final_evaluation(session_id, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy đánh giá: {str(e)}"
        )


@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def convert_speech_to_text(
    audio_file: UploadFile = File(..., description="File âm thanh (max 10MB, max 60s)"),
    language_code: str = Form(default="en-US", description="Language code (default: en-US)"),
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """
    Chuyển đổi giọng nói sang văn bản bằng Google Cloud Speech-to-Text API
    
    **Yêu cầu:**
    - Cần đăng nhập
    - File âm thanh: tối đa 10MB, tối đa 60 giây
    
    **Định dạng hỗ trợ:** WebM, OGG, WAV, MP3, M4A, FLAC
    
    **Tham số:**
    - **audio_file**: File âm thanh cần chuyển đổi
    - **language_code**: Mã ngôn ngữ (mặc định: en-US)
    
    **Trả về:** Văn bản đã chuyển đổi
    """
    try:
        return service.speech_to_text(
            audio_file=audio_file,
            language_code=language_code
        )
    except SpeechToTextException as e:
        raise speech_to_text_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")

