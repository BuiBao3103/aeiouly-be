"""Router for Speaking module"""
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from src.database import get_db
from sqlalchemy.orm import Session
from src.auth.dependencies import get_current_active_user
from src.users.models import User

from src.speaking.schemas import SpeechToTextResponse
from src.speaking.service import SpeakingService
from src.speaking.dependencies import get_speaking_service
from src.speaking.exceptions import SpeechToTextException, speech_to_text_exception


router = APIRouter(
    prefix="/speaking",
    tags=["Speaking Practice"]
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

