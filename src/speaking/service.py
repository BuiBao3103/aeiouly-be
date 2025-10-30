"""Service layer for Speaking module"""
import os
import tempfile
from typing import Optional
from fastapi import UploadFile
import mutagen
from google.cloud import speech_v1
from google.cloud.speech_v1.types import RecognitionConfig, RecognitionAudio

from src.speaking.schemas import SpeechToTextResponse
from src.speaking.exceptions import SpeechToTextException
from src.config import settings


class SpeakingService:
    """Service for speech-to-text conversion"""
    
    def __init__(self):
        """Initialize SpeakingService with Google Cloud Speech client"""
        # Set credentials if provided
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        # Initialize Speech client
        try:
            self.client = speech_v1.SpeechClient()
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Speech client: {e}")
            self.client = None
    
    def _get_audio_duration(self, file_path: str) -> Optional[int]:
        """Extract duration from audio file in seconds"""
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration = int(audio_file.info.length)
                return duration
        except Exception as e:
            print(f"Warning: Could not extract duration from {file_path}: {e}")
        return None
    
    def _get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            print(f"Warning: Could not get file size: {e}")
        return None
    
    def _validate_audio_file(self, audio_file: UploadFile) -> tuple[str, int, int]:
        """
        Validate audio file format, duration, and size
        Returns: (temp_file_path, duration, file_size)
        """
        # Validate content-type
        if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
            raise SpeechToTextException("File phải là âm thanh (audio/*)")
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        try:
            # Read and write file content
            audio_file.file.seek(0)
            content = audio_file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        finally:
            temp_file.close()
        
        # Validate file size (max 10MB)
        file_size = self._get_file_size(temp_file_path)
        if file_size is None:
            os.unlink(temp_file_path)
            raise SpeechToTextException("Không thể đọc kích thước file")
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            os.unlink(temp_file_path)
            raise SpeechToTextException("Kích thước file không được vượt quá 10MB")
        
        # Validate duration (max 60 seconds)
        duration = self._get_audio_duration(temp_file_path)
        if duration is None:
            os.unlink(temp_file_path)
            raise SpeechToTextException("Không thể đọc độ dài file âm thanh")
        
        if duration > 60:
            os.unlink(temp_file_path)
            raise SpeechToTextException("Độ dài file âm thanh không được vượt quá 60 giây")
        
        return temp_file_path, duration, file_size
    
    def speech_to_text(
        self, 
        audio_file: UploadFile,
        language_code: str = "en-US",
        sample_rate_hertz: int = 16000,
        encoding: str = "LINEAR16"
    ) -> SpeechToTextResponse:
        """
        Convert audio to text using Google Cloud Speech-to-Text API
        
        Args:
            audio_file: Audio file to transcribe
            language_code: Language code (default: en-US)
            sample_rate_hertz: Sample rate in Hz (default: 16000)
            encoding: Audio encoding (default: LINEAR16)
        
        Returns:
            SpeechToTextResponse with transcribed text
        """
        if not self.client:
            raise SpeechToTextException("Google Cloud Speech client chưa được khởi tạo")
        
        # Validate audio file
        temp_file_path, _, _ = self._validate_audio_file(audio_file)
        
        try:
            # Read audio file
            with open(temp_file_path, 'rb') as audio_content:
                audio_data = audio_content.read()
            
            # Configure recognition
            config = RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=sample_rate_hertz,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model='latest_long'
            )
            
            audio = RecognitionAudio(content=audio_data)
            
            # Perform speech recognition
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract transcribed text
            transcribed_text = ""
            for result in response.results:
                transcribed_text += result.alternatives[0].transcript
            
            if not transcribed_text:
                raise SpeechToTextException("Không thể nhận dạng giọng nói từ file âm thanh")
            
            return SpeechToTextResponse(text=transcribed_text.strip())
            
        except SpeechToTextException:
            raise
        except Exception as e:
            raise SpeechToTextException(f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

