from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from jose import jwt
from sqlalchemy.orm import Session
from fastapi import Response
from src.auth.models import User, PasswordResetToken, RefreshToken
from src.auth.schemas import UserCreate, Token, PasswordResetRequest, PasswordResetConfirm
from src.auth.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException,
    RefreshTokenExpiredException,
    RefreshTokenRevokedException,
    PasswordResetTokenExpiredException,
    PasswordResetTokenInvalidException
)
from src.auth.utils import generate_secure_token, generate_refresh_token, is_token_expired
from src.mailer.service import EmailService
from src.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.email_service = EmailService()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        try:
            return pwd_context.hash(password)
        except Exception as e:
            # Fallback to simple hash if bcrypt fails
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(ZoneInfo("UTC")) + expires_delta
        else:
            expire = datetime.now(ZoneInfo("UTC")) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        return generate_refresh_token()

    def set_auth_cookies(self, response: Response, access_token: str, refresh_token: str):
        """Set authentication cookies"""
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE_NAME,
            value=access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=settings.COOKIE_SECURE,
            httponly=settings.COOKIE_HTTPONLY,
            samesite=settings.COOKIE_SAMESITE
        )
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            secure=settings.COOKIE_SECURE,
            httponly=settings.COOKIE_HTTPONLY,
            samesite=settings.COOKIE_SAMESITE
        )

    def clear_auth_cookies(self, response: Response):
        """Clear authentication cookies"""
        response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)

    async def register_user(self, user_data: UserCreate, db: Session) -> User:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            raise UserAlreadyExistsException()

        # Create new user
        hashed_password = AuthService.get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Send welcome email
        await self.email_service.send_welcome_email(db_user.email, db_user.username)

        return db_user

    async def authenticate_user(
        self, 
        username: str, 
        password: str, 
        db: Session,
        response: Response
    ) -> Token:
        user = db.query(User).filter(User.username == username).first()
        if not user or not AuthService.verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        refresh_token = AuthService.create_refresh_token(user.id)
        
        # Store refresh token in database
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(db_refresh_token)
        db.commit()

        # Set cookies
        self.set_auth_cookies(response, access_token, refresh_token)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def refresh_access_token(
        self, 
        refresh_token: str, 
        db: Session,
        response: Response
    ) -> Token:
        # Find refresh token in database
        db_refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token
        ).first()
        
        if not db_refresh_token:
            raise RefreshTokenRevokedException()
        
        if is_token_expired(db_refresh_token.expires_at):
            raise RefreshTokenExpiredException()
        
        if db_refresh_token.is_revoked:
            raise RefreshTokenRevokedException()

        # Get user
        user = db.query(User).filter(User.id == db_refresh_token.user_id).first()
        if not user:
            raise UserNotFoundException()

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = AuthService.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Create new refresh token
        new_refresh_token = AuthService.create_refresh_token(user.id)
        
        # Revoke old refresh token
        db_refresh_token.is_revoked = True
        
        # Store new refresh token
        new_db_refresh_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(new_db_refresh_token)
        db.commit()

        # Set new cookies
        self.set_auth_cookies(response, new_access_token, new_refresh_token)
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def logout(self, refresh_token: str, db: Session, response: Response):
        """Logout user by revoking refresh token"""
        if refresh_token:
            db_refresh_token = db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token
            ).first()
            
            if db_refresh_token:
                db_refresh_token.is_revoked = True
                db.commit()

        # Clear cookies
        self.clear_auth_cookies(response)

    async def request_password_reset(
        self, 
        email: str, 
        db: Session, 
        reset_url: str
    ) -> bool:
        """Request password reset"""
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if email exists or not
            return True

        # Generate reset token
        reset_token = generate_secure_token()
        expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        # Store reset token
        db_reset_token = PasswordResetToken(
            email=email,
            token=reset_token,
            expires_at=expires_at
        )
        db.add(db_reset_token)
        db.commit()

        # Send email
        return await self.email_service.send_password_reset_email(
            email, user.username, reset_token, reset_url
        )

    async def confirm_password_reset(
        self, 
        token: str, 
        new_password: str, 
        db: Session
    ) -> bool:
        """Confirm password reset with token"""
        # Find reset token
        db_reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used == False
        ).first()
        
        if not db_reset_token:
            raise PasswordResetTokenInvalidException()
        
        if is_token_expired(db_reset_token.expires_at):
            raise PasswordResetTokenExpiredException()

        # Find user
        user = db.query(User).filter(User.email == db_reset_token.email).first()
        if not user:
            raise UserNotFoundException()

        # Update password
        user.hashed_password = AuthService.get_password_hash(new_password)
        db_reset_token.used = True
        
        # Revoke all refresh tokens for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({
            RefreshToken.is_revoked: True
        })
        
        db.commit()
        return True

    async def change_password(
        self, 
        user_id: int, 
        current_password: str, 
        new_password: str, 
        db: Session
    ) -> bool:
        """Change password for authenticated user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()

        if not AuthService.verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException()

        # Update password
        user.hashed_password = AuthService.get_password_hash(new_password)
        
        # Revoke all refresh tokens for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({
            RefreshToken.is_revoked: True
        })
        
        db.commit()
        return True

    @staticmethod
    async def get_user_by_id(user_id: int, db: Session) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user

    @staticmethod
    async def get_user_by_username(username: str, db: Session) -> User:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise UserNotFoundException()
        return user 
    
    @staticmethod
    async def delete_account(user_id: int, db: Session) -> bool:
        """Delete user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        
        # Revoke all refresh tokens for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({
            RefreshToken.is_revoked: True
        })
        
        db.delete(user)
        db.commit()
        return True