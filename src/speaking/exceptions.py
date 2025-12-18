"""Exceptions for Speaking module"""
from fastapi import HTTPException, status


class SpeakingException(HTTPException):
    """Base exception for speaking module errors"""
    pass


class SpeakingSessionNotFoundException(SpeakingException):
    def __init__(self, detail: str = "Không tìm thấy phiên luyện nói"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class SpeakingSessionCreationFailedException(SpeakingException):
    def __init__(self, detail: str = "Lỗi khi tạo phiên luyện nói"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class SpeechToTextException(SpeakingException):
    def __init__(self, detail: str = "Lỗi khi chuyển đổi speech-to-text"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AgentSessionNotFoundException(SpeakingException):
    def __init__(self, detail: str = "Không tìm thấy phiên làm việc của agent"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AgentSessionInitFailedException(SpeakingException):
    def __init__(self, detail: str = "Khởi tạo phiên làm việc của agent thất bại"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class HintNotAvailableException(SpeakingException):
    def __init__(self, detail: str = "Không có gợi ý hợp lệ được tạo bởi AI"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class ChatSendFailedException(SpeakingException):
    def __init__(self, detail: str = "Lỗi khi gửi tin nhắn"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


def speech_to_text_exception(message: str) -> HTTPException:
    """HTTP exception for speech-to-text errors"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def audio_validation_exception(message: str) -> HTTPException:
    """HTTP exception for audio validation errors"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )

