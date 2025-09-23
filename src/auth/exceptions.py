from fastapi import HTTPException, status

class AuthException(HTTPException):
    """Base exception for authentication errors"""
    pass

class UserNotFoundException(AuthException):
    def __init__(self, detail: str = "Không tìm thấy người dùng"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class UserAlreadyExistsException(AuthException):
    def __init__(self, detail: str = "Người dùng đã tồn tại"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class InvalidCredentialsException(AuthException):
    def __init__(self,detail: str = "Thông tin đăng nhập không hợp lệ"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class InsufficientPermissionsException(AuthException):
    def __init__(self, custom_message: str = None):
        detail = custom_message if custom_message else "Không đủ quyền truy cập"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class TokenNotValidException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Token không hợp lệ hoặc đã hết hạn",
                "code": "token_not_valid",
                "action": "refresh_token"
            }
        )

class PasswordResetTokenExpiredException(AuthException):
    def __init__(self, detail: str = "Token reset password đã hết hạn"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class PasswordResetTokenInvalidException(AuthException):
    def __init__(self, detail: str = "Token reset password không hợp lệ"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class RefreshTokenExpiredException(AuthException):
    def __init__(self, detail: str = "Refresh token đã hết hạn"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class RefreshTokenRevokedException(AuthException):
    def __init__(self, detail: str = "Refresh token đã bị thu hồi"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        ) 