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

class InsufficientPermissionsException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không đủ quyền truy cập"
        )

class PasswordResetTokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset password đã hết hạn"
        )

class PasswordResetTokenInvalidException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset password không hợp lệ"
        )

class RefreshTokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã hết hạn"
        )

class RefreshTokenRevokedException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã bị thu hồi"
        ) 