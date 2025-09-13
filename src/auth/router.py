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
    db: Session = Depends(get_db)
):
    """Register a new user"""
    auth_service = AuthService()
    return await auth_service.register_user(user_data, db)

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login user and return access token with cookies"""
    auth_service = AuthService()
    return await auth_service.authenticate_user(
        login_data.username, 
        login_data.password, 
        db,
        response
    )

@router.post("/refresh", response_model=Token, responses={
    401: {"model": AuthErrorResponse}
})
async def refresh_token(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    auth_service = AuthService()
    return await auth_service.refresh_access_token(refresh_token, db, response)

@router.post("/logout", responses={
    401: {"model": AuthErrorResponse}
})
async def logout(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    db: Session = Depends(get_db)
):
    """Logout user and revoke refresh token"""
    auth_service = AuthService()
    await auth_service.logout(refresh_token, db, response)
    return {"message": "Đăng xuất thành công"}

@router.post("/password-reset-request")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request password reset via email"""
    auth_service = AuthService()
    
    # Get reset URL from request
    reset_url = f"{settings.CLIENT_SIDE_URL}/password-reset"

    success = await auth_service.request_password_reset(
        reset_data.email, 
        db, 
        reset_url
    )
    
    return {
        "message": "Nếu email tồn tại, bạn sẽ nhận được hướng dẫn đặt lại mật khẩu"
    }

@router.post("/password-reset-confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    auth_service = AuthService()
    success = await auth_service.confirm_password_reset(
        reset_data.token, 
        reset_data.new_password, 
        db
    )
    
    return {"message": "Đặt lại mật khẩu thành công"}

@router.post("/change-password", responses={
    401: {"model": AuthErrorResponse}
})
async def change_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    auth_service = AuthService()
    success = await auth_service.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password,
        db
    )
    
    return {"message": "Đổi mật khẩu thành công"}

@router.get("/me", response_model=UserResponse, responses={
    401: {"model": AuthErrorResponse}
})
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@router.get("/verify-token", responses={
    401: {"model": AuthErrorResponse}
})
async def verify_token(current_user = Depends(get_current_active_user)):
    """Verify if current token is valid"""
    return {"valid": True, "user_id": current_user.id}

@router.get("/test-token", responses={
    401: {"model": AuthErrorResponse}
})
async def test_token_validation(
    request: Request,
    token_validation = Depends(validate_token_optional)
):
    """
    Test endpoint to demonstrate token validation with error codes
    Returns different responses based on token validity
    """
    if token_validation:
        return {
            "valid": True,
            "username": token_validation["username"],
            "message": "Token hợp lệ"
        }
    else:
        # This will be caught by the dependency and return structured error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Token không hợp lệ hoặc đã hết hạn",
                "code": "token_not_valid",
                "action": "refresh_token"
            }
        ) 
@router.delete("/delete-account", responses={
    401: {"model": AuthErrorResponse}
})
async def delete_account(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete current user account"""
    auth_service = AuthService()
    await auth_service.delete_account(current_user.id, db)
    return {"message": "Xóa tài khoản thành công"}