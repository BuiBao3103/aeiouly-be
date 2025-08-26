from fastapi import Depends, HTTPException, status, Request, Response
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.auth.models import User, RefreshToken
from src.auth.exceptions import (
    RefreshTokenExpiredException,
    RefreshTokenRevokedException,
    TokenNotValidException
)
from src.auth.utils import is_token_expired, validate_access_token
from src.database import get_db
from src.config import settings
from typing import Optional

async def get_token_from_cookie_or_header(request: Request) -> str:
    """
    Get token from cookie (preferred) or Authorization header (fallback)
    """
    # Try to get token from cookie first
    token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
    
    # Fallback to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Không tìm thấy token xác thực",
                "code": "token_missing",
                "action": "login_required"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

async def get_current_user(
    token: str = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise TokenNotValidException()
    except JWTError:
        raise TokenNotValidException()
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise TokenNotValidException()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail={
                "message": "Tài khoản không hoạt động",
                "code": "account_inactive",
                "action": "contact_admin"
            }
        )
    return current_user

async def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Get refresh token from cookie
    """
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Không tìm thấy refresh token",
                "code": "refresh_token_missing",
                "action": "login_required"
            }
        )
    return refresh_token

async def validate_token_optional(request: Request) -> Optional[dict]:
    """
    Optional token validation - returns user info if token is valid, None if not
    Useful for endpoints that can work with or without authentication
    """
    try:
        token = await get_token_from_cookie_or_header(request)
        username = validate_access_token(token)
        if username:
            return {"username": username, "valid": True}
        return None
    except HTTPException:
        return None 