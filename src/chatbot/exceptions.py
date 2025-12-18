"""Exceptions for Chatbot module"""
from fastapi import HTTPException, status


class ChatbotException(HTTPException):
    """Base exception for chatbot module errors"""
    pass


class ChatbotSessionNotFoundException(ChatbotException):
    def __init__(self, detail: str = "Không tìm thấy phiên chat"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ChatbotSessionCreationFailedException(ChatbotException):
    def __init__(self, detail: str = "Lỗi khi tạo phiên chat"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ChatbotMessageSendFailedException(ChatbotException):
    def __init__(self, detail: str = "Lỗi khi gửi tin nhắn"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ChatbotAgentException(ChatbotException):
    def __init__(self, detail: str = "Lỗi khi xử lý tin nhắn với AI agent"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

