from fastapi import HTTPException, status

class AppException(HTTPException):
    """Base exception for application errors"""
    pass

class DatabaseException(AppException):
    def __init__(self, detail: str = "Đã xảy ra lỗi cơ sở dữ liệu"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class ValidationException(AppException):
    def __init__(self, detail: str = "Lỗi xác thực dữ liệu"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class NotFoundException(AppException):
    def __init__(self, detail: str = "Không tìm thấy tài nguyên"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Chưa được xác thực"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class ForbiddenException(AppException):
    def __init__(self, detail: str = "Bị cấm truy cập"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class ConflictException(AppException):
    def __init__(self, detail: str = "Xung đột tài nguyên"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        ) 