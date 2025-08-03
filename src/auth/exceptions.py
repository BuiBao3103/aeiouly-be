from fastapi import HTTPException, status

class AuthException(HTTPException):
    """Base exception for authentication errors"""
    pass

class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )

class UserAlreadyExistsException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng đã tồn tại"
        )

class InvalidCredentialsException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không hợp lệ"
        )

class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn"
        )

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ"
        )

class InsufficientPermissionsException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không đủ quyền truy cập"
        ) 