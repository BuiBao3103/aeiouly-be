from fastapi import HTTPException


class SoundException(Exception):
    """Base exception for Sound operations"""
    pass


class SoundNotFoundException(SoundException):
    """Raised when sound is not found"""
    pass


class SoundValidationException(SoundException):
    """Raised when sound validation fails"""
    pass


class SoundUploadException(SoundException):
    """Raised when sound upload fails"""
    pass


class SoundDeleteException(SoundException):
    """Raised when sound deletion fails"""
    pass


# HTTP Exceptions
def sound_not_found_exception(sound_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy âm thanh với ID {sound_id}"
    )


def sound_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation âm thanh: {message}"
    )


def sound_upload_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=f"Lỗi upload âm thanh: {message}"
    )


def sound_delete_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=f"Lỗi xóa âm thanh: {message}"
    )
