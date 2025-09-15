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
            detail={
                "message": "Refresh token đã hết hạn",
                "code": "refresh_token_expired",
                "action": "login_required"
            }
        )

class RefreshTokenRevokedException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Refresh token đã bị thu hồi",
                "code": "refresh_token_revoked",
                "action": "login_required"
            }
        ) 