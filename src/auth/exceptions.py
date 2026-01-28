from fastapi import HTTPException, status

class AuthException(HTTPException):
    """Base exception for authentication errors"""
    pass

class UserNotFoundException(AuthException):
    def __init__(self, detail: str = "Không tìm thấy người dùng"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": detail,
                "code": "USER_NOT_FOUND"
            }
        )

class UserAlreadyExistsException(AuthException):
    def __init__(self, detail: str = "Người dùng đã tồn tại"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": detail,
                "code": "USER_ALREADY_EXISTS"
            }
        )

class InvalidCredentialsException(AuthException):
    def __init__(self,detail: str = "Thông tin đăng nhập không hợp lệ",code: str = "INVALID_CREDENTIALS"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": detail,
                "code": code
            }
        )

class InsufficientPermissionsException(AuthException):
    def __init__(self, custom_message: str = None):
        detail = custom_message if custom_message else "Không đủ quyền truy cập"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": detail,
                "code": "INSUFFICIENT_PERMISSIONS"
            }
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
            detail={
                "message": detail,
                "code": "PASSWORD_RESET_TOKEN_EXPIRED"
            }
        )

class PasswordResetTokenInvalidException(AuthException):
    def __init__(self, detail: str = "Token reset password không hợp lệ"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": detail,
                "code": "PASSWORD_RESET_TOKEN_INVALID"
            }
        )

class RefreshTokenExpiredException(AuthException):
    def __init__(self, detail: str = "Refresh token đã hết hạn"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": detail,
                "code": "REFRESH_TOKEN_EXPIRED"
            }
        )

class RefreshTokenRevokedException(AuthException):
    def __init__(self, detail: str = "Refresh token đã bị thu hồi"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": detail,
                "code": "REFRESH_TOKEN_REVOKED"
            }
        ) 