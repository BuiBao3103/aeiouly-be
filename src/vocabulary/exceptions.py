from fastapi import HTTPException, status

class VocabularyException(HTTPException):
    """Base exception for vocabulary module errors"""
    def __init__(self, detail: str = "Lỗi khi xử lý từ vựng", status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)

class VocabularySetNotFoundException(VocabularyException):
    """Exception for vocabulary set not found"""
    def __init__(self, detail: str = "Không tìm thấy bộ từ vựng"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class VocabularyItemNotFoundException(VocabularyException):
    """Exception for vocabulary item not found"""
    def __init__(self, detail: str = "Không tìm thấy từ vựng"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class DictionaryWordNotFoundException(VocabularyException):
    """Exception for dictionary word not found"""
    def __init__(self, detail: str = "Không tìm thấy từ trong từ điển"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class VocabularyItemAlreadyExistsException(VocabularyException):
    """Exception for vocabulary item already exists"""
    def __init__(self, detail: str = "Từ vựng đã tồn tại trong bộ"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)

class InsufficientVocabularyException(VocabularyException):
    """Exception for insufficient vocabulary for study session"""
    def __init__(self, detail: str = "Không đủ từ vựng để tạo phiên học"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)
