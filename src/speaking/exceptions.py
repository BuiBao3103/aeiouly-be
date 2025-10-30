"""Exceptions for Speaking module"""
from fastapi import HTTPException, status


class SpeakingException(Exception):
    """Base exception for speaking module"""
    pass


class SpeechToTextException(SpeakingException):
    """Exception for speech-to-text conversion errors"""
    pass


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

