from fastapi import HTTPException, status

class ListeningException(HTTPException):
    """Base exception for listening module errors"""
    pass

class LessonNotFoundException(ListeningException):
    def __init__(self, detail: str = "Không tìm thấy bài học"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class LessonAlreadyExistsException(ListeningException):
    def __init__(self, detail: str = "Bài học đã tồn tại"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class SessionNotFoundException(ListeningException):
    def __init__(self, detail: str = "Không tìm thấy phiên học"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class SessionAlreadyCompletedException(ListeningException):
    def __init__(self, detail: str = "Phiên học đã hoàn thành"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class InvalidSRTContentException(ListeningException):
    def __init__(self, detail: str = "Nội dung SRT không hợp lệ"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class TranslationFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi dịch câu"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class DifficultyAnalysisFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi phân tích độ khó"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class LessonCreationFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi tạo bài học"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class SessionCreationFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi tạo phiên học"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class ProgressUpdateFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi cập nhật tiến độ"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class SessionCompletionFailedException(ListeningException):
    def __init__(self, detail: str = "Lỗi khi hoàn thành phiên học"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
