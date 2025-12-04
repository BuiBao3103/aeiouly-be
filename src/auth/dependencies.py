from fastapi import Depends, HTTPException, status, Request, Response, WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.users.models import User
from src.auth.models import RefreshToken
from src.auth.exceptions import (
    RefreshTokenExpiredException,
    RefreshTokenRevokedException,
    TokenNotValidException
)
from src.auth.utils import is_token_expired, validate_access_token
from src.database import get_db
from src.config import settings
from typing import Optional
from src.auth.service import AuthService


def get_auth_service() -> AuthService:
    """Get AuthService instance"""
    return AuthService()

def get_token_from_cookie_or_header(request: Request) -> str:
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

    user = resolve_user_from_token(token, db)
    if user is None:
        raise TokenNotValidException()
    return user

def resolve_user_from_token(token: str, db: Session) -> Optional[User]:
    """Decode JWT and resolve to a User or return None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        username_claim = payload.get("username")
    except JWTError:
        return None

    user: Optional[User] = None
    if username_claim:
        user = db.query(User).filter(User.username == username_claim).first()
    elif subject is not None:
        try:
            user_id = int(subject)
            user = db.query(User).filter(User.id == user_id).first()
        except (TypeError, ValueError):
            user = db.query(User).filter(User.username == str(subject)).first()
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
        token = get_token_from_cookie_or_header(request)
        username = validate_access_token(token)
        if username:
            return {"username": username, "valid": True}
        return None
    except HTTPException:
        return None

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user optionally - returns User if authenticated, None if not
    """
    try:
        # Try to get token from cookie first
        token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        
        # Fallback to Authorization header
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return None
            
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        username_claim = payload.get("username")

        user: Optional[User] = None
        if username_claim:
            user = db.query(User).filter(User.username == username_claim).first()
        elif subject is not None:
            try:
                user_id = int(subject)
                user = db.query(User).filter(User.id == user_id).first()
            except (TypeError, ValueError):
                user = db.query(User).filter(User.username == str(subject)).first()

        if user is None or not user.is_active:
            return None
            
        return user
    except JWTError:
        return None


def resolve_user_from_websocket(websocket: WebSocket, db: Session) -> Optional[User]:
    """Resolve user from WebSocket connection (token from cookies or query params).
    
    Note: Some browsers may not send cookies in WebSocket handshake.
    Fallback to query params if cookies are not available.
    """
    token = None
    
    # Try to get token from cookies first
    cookie_header = websocket.headers.get("cookie") or websocket.headers.get("Cookie")
    
    if cookie_header:
        # Parse cookies
        cookies = {}
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                key, value = cookie.strip().split("=", 1)
                cookies[key] = value
        
        # Get access_token from cookies
        token = cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
    
    # Fallback to query params if no token in cookies
    if not token:
        token = websocket.query_params.get("token")
    
    # If no token found, return None
    if not token:
        return None
    
    # Resolve user from token
    try:
        # Validate token
        try:
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return None
        
        # Resolve user from token
        return resolve_user_from_token(token, db)
    except Exception:
        return None
