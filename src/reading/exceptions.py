from fastapi import HTTPException, status

class ReadingException(HTTPException):
    """Base exception for reading module errors"""
    def __init__(self, detail: str = "Lỗi khi xử lý bài đọc", status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)

class ReadingSessionNotFoundException(ReadingException):
    """Exception for reading session not found"""
    def __init__(self, detail: str = "Không tìm thấy phiên đọc"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class TextGenerationFailedException(ReadingException):
    """Exception for AI text generation failure"""
    def __init__(self, detail: str = "Lỗi khi tạo bài đọc"):
        super().__init__(detail=detail)

class TextAnalysisFailedException(ReadingException):
    """Exception for AI text analysis failure"""
    def __init__(self, detail: str = "Lỗi khi phân tích bài đọc"):
        super().__init__(detail=detail)

class QuizGenerationFailedException(ReadingException):
    """Exception for quiz generation failure"""
    def __init__(self, detail: str = "Lỗi khi tạo bài trắc nghiệm"):
        super().__init__(detail=detail)
