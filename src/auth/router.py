"""
Router for Auth module with DI pattern
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from src.auth.schemas import (
    UserCreate, 
    UserResponse, 
    Token, 
    PasswordResetRequest, 
    PasswordResetConfirm,
    PasswordChange,
    LoginRequest,
    AuthErrorResponse
)
from src.auth.service import AuthService
from src.auth.dependencies import (
    get_current_user, 
    get_current_active_user,
    get_refresh_token_from_cookie
)
from src.database import get_db
from src.config import settings
from src.auth.dependencies import validate_token_optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, 
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Register a new user"""
    return await service.register_user(user_data, db)

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    login_data: LoginRequest,
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
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
        samesite=settings.COOKIE_SAMESITE
    )
    
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    
    return token_data

@router.post("/refresh", response_model=Token, responses={
    401: {"model": AuthErrorResponse}
})
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    refresh_token = await get_refresh_token_from_cookie(request)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    token_data = await service.refresh_access_token(refresh_token, db)
    
    # Set new cookies
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=token_data.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    
    return token_data

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Logout user and revoke refresh token"""
    refresh_token = await get_refresh_token_from_cookie(request)
    if refresh_token:
        await service.logout(refresh_token, db)
    
    # Clear cookies
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)
    
    return {"message": "Đăng xuất thành công"}

@router.post("/request-password-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Request password reset via email"""
    await service.request_password_reset(reset_request.email, db)
    return {"message": "Nếu tài khoản tồn tại, email đặt lại mật khẩu đã được gửi"}

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    await service.reset_password(reset_data, db)
    return {"message": "Mật khẩu đã được đặt lại thành công"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_active_user),
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    await service.change_password(current_user, password_data.current_password, password_data.new_password, db)
    return {"message": "Đổi mật khẩu thành công"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

@router.delete("/account")
async def delete_account(
    response: Response,
    current_user = Depends(get_current_active_user),
    service: AuthService = Depends(AuthService),
    db: Session = Depends(get_db)
):
    """Soft delete: set is_active=False, revoke refresh tokens, clear cookies"""
    ok = await service.deactivate_user(current_user, db)
    if not ok:
        raise HTTPException(status_code=500, detail="Không thể vô hiệu hóa tài khoản")

    # Clear cookies
    from src.config import settings
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)
    return {"message": "Tài khoản đã được vô hiệu hóa"}
