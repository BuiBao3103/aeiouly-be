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
    tags=["speaking"]
)


@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def convert_speech_to_text(
    audio_file: UploadFile = File(..., description="File âm thanh (max 10MB, max 60s)"),
    language_code: str = Form(default="en-US", description="Language code (default: en-US)"),
    sample_rate_hertz: int = Form(default=16000, description="Sample rate in Hz (default: 16000)"),
    encoding: str = Form(default="LINEAR16", description="Audio encoding (default: LINEAR16)"),
    current_user: User = Depends(get_current_active_user),
    service: SpeakingService = Depends(get_speaking_service),
    db: Session = Depends(get_db)
):
    """
    Convert speech to text using Google Cloud Speech-to-Text API
    
    **Requirements:**
    - Authentication required
    - File must be audio format (audio/*)
    - File size: max 10MB
    - Duration: max 60 seconds
    
    **Parameters:**
    - **audio_file**: Audio file to transcribe (WAV, MP3, FLAC, etc.)
    - **language_code**: Language code (default: en-US)
    - **sample_rate_hertz**: Sample rate in Hz (default: 16000)
    - **encoding**: Audio encoding (default: LINEAR16)
    
    **Returns:**
    - Transcribed text in English
    """
    try:
        return service.speech_to_text(
            audio_file=audio_file,
            language_code=language_code,
            sample_rate_hertz=sample_rate_hertz,
            encoding=encoding
        )
    except SpeechToTextException as e:
        raise speech_to_text_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")

