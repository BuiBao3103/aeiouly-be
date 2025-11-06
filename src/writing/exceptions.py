from fastapi import HTTPException, status


class WritingException(HTTPException):
    """Base exception for writing module errors"""
    pass


class WritingSessionNotFoundException(WritingException):
    def __init__(self, detail: str = "Không tìm thấy phiên luyện viết"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class WritingSessionCreationFailedException(WritingException):
    def __init__(self, detail: str = "Lỗi khi tạo phiên luyện viết"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class NoCurrentSentenceException(WritingException):
    def __init__(self, detail: str = "Không có câu hiện tại để gợi ý"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AgentSessionNotFoundException(WritingException):
    def __init__(self, detail: str = "Không tìm thấy phiên làm việc của agent"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AgentSessionInitFailedException(WritingException):
    def __init__(self, detail: str = "Khởi tạo phiên làm việc của agent thất bại"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class HintNotAvailableException(WritingException):
    def __init__(self, detail: str = "Không có gợi ý hợp lệ được tạo bởi AI"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class ChatSendFailedException(WritingException):
    def __init__(self, detail: str = "Lỗi khi gửi tin nhắn"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class FinalEvaluationFailedException(WritingException):
    def __init__(self, detail: str = "Lỗi khi lấy đánh giá cuối"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


