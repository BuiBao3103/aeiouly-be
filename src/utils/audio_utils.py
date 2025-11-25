import os
import tempfile
from typing import List, Tuple, Type

import mutagen
from fastapi import UploadFile
from pydub import AudioSegment


def get_audio_file_extension(
    audio_file: UploadFile,
    supported_formats: List[str],
    exception_cls: Type[Exception],
) -> str:
    """Resolve file extension from filename or content-type."""
    filename = audio_file.filename or ""
    content_type = audio_file.content_type or ""

    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_formats:
            return ext

    content_type_map = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/flac": ".flac",
        "audio/aac": ".aac",
        "audio/aacp": ".aac",
    }

    for mime_type, ext in content_type_map.items():
        if mime_type in content_type.lower():
            return ext

    raise exception_cls(
        "Định dạng file không được hỗ trợ. "
        f"Chỉ chấp nhận: {', '.join(supported_formats)}"
    )


def validate_audio_file(
    audio_file: UploadFile,
    supported_formats: List[str],
    max_size_bytes: int,
    max_duration_seconds: int,
    exception_cls: Type[Exception],
) -> Tuple[str, str]:
    """Validate audio file size/duration and persist to temp file."""
    file_ext = get_audio_file_extension(audio_file, supported_formats, exception_cls)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    try:
        audio_file.file.seek(0)
        content = audio_file.file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    finally:
        temp_file.close()

    file_size = os.path.getsize(temp_file_path)
    if file_size > max_size_bytes:
        os.unlink(temp_file_path)
        raise exception_cls("Kích thước file không được vượt quá 10MB")

    try:
        audio_info = mutagen.File(temp_file_path)
        if audio_info and hasattr(audio_info.info, "length"):
            if audio_info.info.length > max_duration_seconds:
                os.unlink(temp_file_path)
                raise exception_cls("Độ dài file âm thanh không được vượt quá 60 giây")
    except Exception:
        # Allow downstream speech-to-text to handle duration errors
        pass

    return temp_file_path, file_ext


def convert_audio_to_wav(
    input_file_path: str,
    output_file_path: str,
    target_sample_rate: int,
    exception_cls: Type[Exception],
) -> str:
    """Convert arbitrary audio file to mono LINEAR16 WAV."""
    try:
        audio = AudioSegment.from_file(input_file_path)

        if audio.channels > 1:
            audio = audio.set_channels(1)

        if audio.frame_rate != target_sample_rate:
            audio = audio.set_frame_rate(target_sample_rate)

        audio.export(
            output_file_path,
            format="wav",
            parameters=["-acodec", "pcm_s16le"],
        )
        return output_file_path
    except Exception as exc:
        raise exception_cls(f"Không thể chuyển đổi file âm thanh sang WAV: {exc}") from exc

