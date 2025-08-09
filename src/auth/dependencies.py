from fastapi import Depends, HTTPException, status, Request, Response
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.auth.models import User, RefreshToken
from src.auth.exceptions import (
    RefreshTokenExpiredException,
    RefreshTokenRevokedException
)
from src.auth.utils import is_token_expired
from src.database import get_db
from src.config import settings
from src.auth.config import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME

async def get_token_from_cookie_or_header(request: Request) -> str:
    """
    Get token from cookie (preferred) or Authorization header (fallback)
    """
    # Try to get token from cookie first
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    
    # Fallback to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy token xác thực",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

async def get_current_user(
    token: str = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản không hoạt động")
    return current_user

async def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Get refresh token from cookie
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy refresh token"
        )
    return refresh_token 