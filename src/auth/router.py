"""
Router for Auth module with DI pattern
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserUpdateResponse,
    Token,
    GoogleLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
    LoginRequest,
    AuthErrorResponse
)
from src.auth.service import AuthService
from src.base_response import BaseResponse, create_response
from src.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_refresh_token_from_cookie
)
from src.users.models import User
from src.database import get_db
from src.config import settings
from src.auth.dependencies import validate_token_optional

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=BaseResponse[UserResponse])
async def register(
    user_data: UserCreate,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    user = await service.register_user(user_data, db)
    return create_response(
        data=UserResponse.model_validate(user),
        message="Đăng ký thành công",
        code="REGISTER_SUCCESSFULLY"
    )


@router.post("/login", response_model=BaseResponse[Token])
async def login(
    response: Response,
    login_data: LoginRequest,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token with cookies"""
    token_data = await service.login(
        login_data.username,
        login_data.password,
        db
    )

    # Set cookies
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=token_data.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"  # Important: set path so cookies are sent for all paths
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"  # Important: set path so cookies are sent for all paths
    )

    return create_response(
        data=token_data,
        message="Đăng nhập thành công",
        code="LOGIN_SUCCESSFULLY"
    )


@router.post("/google", response_model=BaseResponse[Token])
async def login_with_google(
    response: Response,
    payload: GoogleLoginRequest,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Login via Google ID token, then issue our tokens and set cookies."""
    token_data = await service.login_with_google(payload.id_token, db)

    # Set cookies like normal login
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=token_data.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )

    return create_response(
        data=token_data,
        message="Đăng nhập Google thành công",
        code="GOOGLE_LOGIN_SUCCESSFULLY"
    )


@router.post("/refresh", response_model=BaseResponse[Token], responses={
    401: {"model": AuthErrorResponse}
})
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    refresh_token = await get_refresh_token_from_cookie(request)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Refresh token not found",
                "code": "REFRESH_TOKEN_NOT_FOUND"
            }
        )

    token_data = await service.refresh_access_token(refresh_token, db)

    # Set new cookies
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=token_data.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )

    return create_response(
        data=token_data,
        message="Làm mới token thành công",
        code="REFRESH_SUCCESSFULLY"
    )


@router.post("/logout", response_model=BaseResponse[None])
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and revoke refresh token"""
    refresh_token = await get_refresh_token_from_cookie(request)
    if refresh_token:
        await service.logout(refresh_token, db)

    # Clear cookies (must match attributes used when setting)
    cookie_kwargs = {
        "domain": settings.COOKIE_DOMAIN,
        "path": "/",
        "samesite": settings.COOKIE_SAMESITE,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
    }
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME, **cookie_kwargs)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, **cookie_kwargs)

    return create_response(
        data=None,
        message="Đăng xuất thành công",
        code="LOGOUT_SUCCESS"
    )


@router.post("/request-password-reset", response_model=BaseResponse[None])
async def request_password_reset(
    reset_request: PasswordResetRequest,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Request password reset via email"""
    await service.request_password_reset(reset_request.email, db)
    return create_response(
        data=None,
        message="Nếu email tồn tại, liên kết đặt lại mật khẩu đã được gửi",
        code="PASSWORD_RESET_REQUEST_SUCCESS"
    )


@router.post("/reset-password", response_model=BaseResponse[None])
async def reset_password(
    reset_data: PasswordResetConfirm,
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token"""
    await service.reset_password(reset_data, db)
    return create_response(
        data=None,
        message="Đặt lại mật khẩu thành công",
        code="PASSWORD_RESET_SUCCESS"
    )


@router.post("/change-password", response_model=BaseResponse[None])
async def change_password(
    password_data: PasswordChange,
    current_user=Depends(get_current_active_user),
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Change password for authenticated user"""
    await service.change_password(current_user, password_data.current_password, password_data.new_password, db)
    return create_response(
        data=None,
        message="Đổi mật khẩu thành công",
        code="PASSWORD_CHANGE_SUCCESS"
    )


@router.get("/me", response_model=BaseResponse[UserResponse])
async def get_current_user_info(
    current_user=Depends(get_current_active_user)
):
    """Get current user information"""
    return create_response(
        data=UserResponse.model_validate(current_user),
        message="Lấy thông tin người dùng thành công",
        code="USER_INFO_SUCCESS"
    )


@router.delete("/account", response_model=BaseResponse[None])
async def delete_account(
    response: Response,
    current_user=Depends(get_current_active_user),
    service: AuthService = Depends(AuthService),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete: set is_active=False, revoke refresh tokens, clear cookies"""
    ok = await service.deactivate_user(current_user, db)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Không thể vô hiệu hóa tài khoản",
                "code": "ACCOUNT_DELETE_FAILED"
            }
        )

    # Clear cookies (must use same attributes as when setting them)
    cookie_kwargs = {
        "domain": settings.COOKIE_DOMAIN,
        "path": "/",
        "samesite": settings.COOKIE_SAMESITE,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
    }
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME, **cookie_kwargs)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, **cookie_kwargs)
    return create_response(
        data=None,
        message="Tài khoản đã được xóa thành công",
        code="ACCOUNT_DELETE_SUCCESS"
    )


@router.put("/me", response_model=BaseResponse[UserUpdateResponse])
async def update_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(AuthService)
):
    """Update current user's profile (username, full_name)"""
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_unset=True)

        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Không có dữ liệu để cập nhật",
                    "code": "NO_DATA_TO_UPDATE"
                }
            )

        updated_user = await service.update_user_profile(current_user, update_dict, db)

        return create_response(
            data=UserUpdateResponse(
                id=updated_user.id,
                email=updated_user.email,
                username=updated_user.username,
                full_name=updated_user.full_name,
                role=updated_user.role,
                is_active=updated_user.is_active,
                avatar_url=updated_user.avatar_url,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at,
            ),
            message="Cập nhật hồ sơ thành công",
            code="PROFILE_UPDATE_SUCCESSFULLY"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Lỗi cập nhật profile: {str(e)}",
                "code": "PROFILE_UPDATE_FAILED"
            }
        )


@router.post("/me/avatar", response_model=BaseResponse[UserUpdateResponse])
async def upload_user_avatar(
    image: UploadFile,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(AuthService)
):
    """Upload avatar for current user"""
    try:
        updated_user = await service.upload_user_avatar(current_user, image, db)

        return create_response(
            data=UserUpdateResponse(
                id=updated_user.id,
                email=updated_user.email,
                username=updated_user.username,
                full_name=updated_user.full_name,
                role=updated_user.role,
                is_active=updated_user.is_active,
                avatar_url=updated_user.avatar_url,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at,
            ),
            message="Tải lên avatar thành công",
            code="AVATAR_UPLOAD_SUCCESSFULLY"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Lỗi upload avatar: {str(e)}",
                "code": "AVATAR_UPLOAD_FAILED"
            }
        )
