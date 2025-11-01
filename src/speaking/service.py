"""Service layer for Speaking module"""
import os
import tempfile
import sys
from fastapi import UploadFile
import mutagen
# Fix for Python 3.13+: ensure audioop-lts is used if available
try:
    import audioop_lts as audioop
    sys.modules['audioop'] = audioop
except ImportError:
    try:
        import audioop
    except ImportError:
        pass  # Let pydub handle the error
from pydub import AudioSegment
from google.cloud import speech

from src.speaking.schemas import SpeechToTextResponse
from src.speaking.exceptions import SpeechToTextException
from src.config import settings


class SpeakingService:
    """Service for speech-to-text conversion"""
    
    # Target format: always convert to WAV with LINEAR16 encoding at 16000 Hz
    TARGET_SAMPLE_RATE = 16000
    TARGET_ENCODING = speech.RecognitionConfig.AudioEncoding.LINEAR16
    
    # Supported input formats (will be converted to WAV)
    SUPPORTED_INPUT_FORMATS = ['.webm', '.ogg', '.opus', '.wav', '.mp3', '.m4a', '.flac', '.aac', '.mpeg']
    
    def __init__(self):
        """Initialize SpeakingService with Google Cloud Speech client"""
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        try:
            self.client = speech.SpeechClient()
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Speech client: {e}")
            self.client = None
    
    def _get_file_extension(self, audio_file: UploadFile) -> str:
        """Get file extension from filename or content type"""
        filename = audio_file.filename or ""
        content_type = audio_file.content_type or ""
        
        # Try to get extension from filename
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in self.SUPPORTED_INPUT_FORMATS:
                return ext
        
        # Try to get from content type
        content_type_map = {
            'audio/webm': '.webm',
            'audio/ogg': '.ogg',
            'audio/opus': '.opus',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/x-wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/mp4': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/flac': '.flac',
            'audio/aac': '.aac',
            'audio/aacp': '.aac',
        }
        
        for mime_type, ext in content_type_map.items():
            if mime_type in content_type.lower():
                return ext
        
        raise SpeechToTextException(
            f"Định dạng file không được hỗ trợ. "
            f"Chỉ chấp nhận: {', '.join(self.SUPPORTED_INPUT_FORMATS)}"
        )
    
    def _convert_to_wav(self, input_file_path: str, output_file_path: str) -> str:
        """
        Convert audio file to WAV format (LINEAR16, 16000 Hz, mono)
        Returns: output_file_path
        """
        try:
            # Load audio file using pydub
            audio = AudioSegment.from_file(input_file_path)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to target sample rate if different
            if audio.frame_rate != self.TARGET_SAMPLE_RATE:
                audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
            
            # Export as WAV (LINEAR16 PCM)
            audio.export(
                output_file_path,
                format="wav",
                parameters=["-acodec", "pcm_s16le"]  # 16-bit PCM
            )
            
            return output_file_path
        except Exception as e:
            raise SpeechToTextException(f"Không thể chuyển đổi file âm thanh sang WAV: {str(e)}")
    
    def _validate_audio_file(self, audio_file: UploadFile) -> tuple[str, str]:
        """
        Validate audio file and save to temp file
        Returns: (temp_file_path, file_extension)
        """
        # Get and validate file extension
        file_ext = self._get_file_extension(audio_file)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        try:
            audio_file.file.seek(0)
            content = audio_file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        finally:
            temp_file.close()
        
        # Check file size (max 10MB)
        file_size = os.path.getsize(temp_file_path)
        if file_size > 10 * 1024 * 1024:
            os.unlink(temp_file_path)
            raise SpeechToTextException("Kích thước file không được vượt quá 10MB")
        
        # Check duration (max 60 seconds)
        try:
            audio_info = mutagen.File(temp_file_path)
            if audio_info and hasattr(audio_info.info, 'length'):
                if audio_info.info.length > 60:
                    os.unlink(temp_file_path)
                    raise SpeechToTextException("Độ dài file âm thanh không được vượt quá 60 giây")
        except Exception as e:
            # If we can't read duration, continue anyway (let Google API handle it)
            print(f"Warning: Could not validate duration: {e}")
        
        return temp_file_path, file_ext
    
    def speech_to_text(
        self,
        audio_file: UploadFile,
        language_code: str = "en-US",
    ) -> SpeechToTextResponse:
        """
        Convert audio to text using Google Cloud Speech-to-Text API
        All audio formats are converted to WAV (LINEAR16, 16000 Hz) before sending to Google Cloud
        Supports: WebM, OGG, WAV, MP3, M4A, FLAC, AAC
        """
        if not self.client:
            raise SpeechToTextException("Google Cloud Speech client chưa được khởi tạo")
        
        # Validate and save audio file
        input_file_path, file_ext = self._validate_audio_file(audio_file)
        wav_file_path = None

        try:
            # Optimize: Only convert if necessary
            # Check if file is already in correct format (WAV, 16000 Hz, mono, LINEAR16)
            needs_conversion = True
            if file_ext == '.wav':
                try:
                    audio_seg = AudioSegment.from_file(input_file_path)
                    # Only convert if format doesn't match target
                    if (audio_seg.frame_rate == self.TARGET_SAMPLE_RATE and 
                        audio_seg.channels == 1):
                        # File is already in correct format, skip conversion
                        needs_conversion = False
                        final_file_path = input_file_path
                except Exception:
                    # If can't read, we'll convert to be safe
                    pass
            
            # Convert to WAV only if needed
            if needs_conversion:
                wav_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                self._convert_to_wav(input_file_path, wav_file_path)
                final_file_path = wav_file_path
            
            # Read converted WAV file
            with open(final_file_path, 'rb') as f:
                audio_data = f.read()
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Build config with fixed WAV format (LINEAR16, 16000 Hz)
            config = speech.RecognitionConfig(
                encoding=self.TARGET_ENCODING,
                sample_rate_hertz=self.TARGET_SAMPLE_RATE,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            
            # Perform speech recognition
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract text from results
            transcribed_text = ""
            for result in response.results:
                transcribed_text += result.alternatives[0].transcript + " "
            
            transcribed_text = transcribed_text.strip()
            
            if not transcribed_text:
                raise SpeechToTextException("Không thể nhận dạng giọng nói từ file âm thanh")
            
            return SpeechToTextResponse(text=transcribed_text)
            
        except SpeechToTextException:
            raise
        except Exception as e:
            raise SpeechToTextException(f"Lỗi khi chuyển đổi speech-to-text: {str(e)}")
        finally:
            # Clean up temporary files
            if os.path.exists(input_file_path):
                os.unlink(input_file_path)
            if wav_file_path and os.path.exists(wav_file_path):
                os.unlink(wav_file_path)