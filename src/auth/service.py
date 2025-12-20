"""
Service layer for Auth module with instance methods
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import Response
from src.users.models import User, UserRole
from src.auth.models import PasswordResetToken, RefreshToken
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
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        self.email_service = EmailService()

    def verify_password(self, plain_password: str, hashed_password: Optional[str]) -> bool:
        if not hashed_password:
            return False
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    def get_password_hash(self, password: str) -> str:
        try:
            return pwd_context.hash(password)
        except Exception:
            # Fallback to simple hash if bcrypt fails
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(ZoneInfo("UTC")) + expires_delta
        else:
            expire = datetime.now(
                ZoneInfo("UTC")) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self) -> str:
        """Create a refresh token for the user"""
        return generate_refresh_token()

    async def register_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        """Register a new user"""
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise UserAlreadyExistsException("Tên đăng nhập đã tồn tại")

        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise UserAlreadyExistsException("Email đã được sử dụng")

        # Create new user
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=UserRole.USER,  # Default role for new users
            avatar_url=settings.DEFAULT_AVATAR_URL  # Set default avatar
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # Send welcome email
        try:
            await self.email_service.send_welcome_email(db_user.email, db_user.username)
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send welcome email: {e}")

        return db_user

    async def authenticate_user(self, username: str, password: str, db: AsyncSession) -> Optional[User]:
        """Authenticate user with username and password"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, username: str, password: str, db: AsyncSession) -> Token:
        """Login user and return tokens"""
        user = await self.authenticate_user(username, password, db)
        if not user:
            raise InvalidCredentialsException(
                "Tên đăng nhập hoặc mật khẩu không đúng")

        # Create access token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = self.create_refresh_token()

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=datetime.now(
                ZoneInfo("UTC")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(db_refresh_token)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    async def refresh_access_token(self, refresh_token: str, db: AsyncSession) -> Token:
        """Refresh access token using refresh token"""
        # Find refresh token in database
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        db_refresh_token = result.scalar_one_or_none()
        if not db_refresh_token:
            raise RefreshTokenRevokedException("Refresh token không hợp lệ")

        # Check if refresh token is expired
        if is_token_expired(db_refresh_token.expires_at):
            # Remove expired token
            await db.delete(db_refresh_token)
            await db.commit()
            raise RefreshTokenExpiredException("Refresh token đã hết hạn")

        # Get user
        result = await db.execute(
            select(User).where(User.id == db_refresh_token.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundException("Không tìm thấy người dùng")

        # Create new access token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires
        )

        # Create new refresh token
        new_refresh_token = self.create_refresh_token()

        # Update refresh token in database
        db_refresh_token.token = new_refresh_token
        db_refresh_token.expires_at = datetime.now(
            ZoneInfo("UTC")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    async def login_with_google(self, google_id_token_str: str, db: AsyncSession) -> Token:
        """Verify Google ID token, upsert user, and issue our tokens."""
        try:
            idinfo = google_id_token.verify_oauth2_token(
                google_id_token_str,
                google_requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID or None,
            )
        except Exception:
            raise InvalidCredentialsException("Google token không hợp lệ")

        sub = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name") or ""

        if not sub or not email:
            raise InvalidCredentialsException("Thiếu thông tin từ Google")

        # Find existing user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user:
            # Create a new user with a generated username
            base_username = email.split("@")[0]
            username = base_username
            suffix = 1
            while True:
                result = await db.execute(
                    select(User).where(User.username == username)
                )
                if result.scalar_one_or_none() is None:
                    break
                username = f"{base_username}{suffix}"
                suffix += 1

            user = User(
                username=username,
                email=email,
                full_name=name,
                # Mark OAuth-created account: no local password
                hashed_password=None,
                role=UserRole.USER,
                avatar_url=settings.DEFAULT_AVATAR_URL  # Set default avatar
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Issue tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )

        refresh_token = self.create_refresh_token()
        db_refresh_token = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(db_refresh_token)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str, db: AsyncSession) -> bool:
        """Logout user by revoking refresh token"""
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        db_refresh_token = result.scalar_one_or_none()
        if db_refresh_token:
            await db.delete(db_refresh_token)
            await db.commit()
            return True
        return False

    async def request_password_reset(self, email: str, db: AsyncSession) -> bool:
        """Request password reset for user"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user:
            # Don't reveal if email exists or not
            return False

        # Generate reset token
        reset_token = generate_secure_token(
            settings.PASSWORD_RESET_TOKEN_LENGTH)

        # Store reset token in database
        reset_token_obj = PasswordResetToken(
            token=reset_token,
            email=user.email,
            expires_at=datetime.now(ZoneInfo(
                "UTC")) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        )
        db.add(reset_token_obj)
        await db.commit()

        # Send reset email
        reset_url = f"{settings.CLIENT_SIDE_URL}/reset-password"
        await self.email_service.send_password_reset_email(user.email, user.full_name, reset_token, reset_url)

        return True

    async def reset_password(self, reset_data: PasswordResetConfirm, db: AsyncSession) -> bool:
        """Reset user password using reset token"""
        # Find reset token
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == reset_data.token)
        )
        reset_token_obj = result.scalar_one_or_none()
        if not reset_token_obj:
            raise PasswordResetTokenInvalidException(
                "Token reset password không hợp lệ")

        # Check if token is expired
        if is_token_expired(reset_token_obj.expires_at):
            # Remove expired token
            await db.delete(reset_token_obj)
            await db.commit()
            raise PasswordResetTokenExpiredException(
                "Token reset password đã hết hạn")

        # Get user
        result = await db.execute(
            select(User).where(User.email == reset_token_obj.email)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundException("Không tìm thấy người dùng")

        # Update password
        user.hashed_password = self.get_password_hash(reset_data.new_password)
        await db.commit()

        # Remove reset token
        await db.delete(reset_token_obj)
        await db.commit()

        return True

    async def change_password(self, user: User, current_password: str, new_password: str, db: AsyncSession) -> bool:
        """Change password for authenticated user and revoke existing refresh tokens"""
        # Verify current password
        if not self.verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException("Mật khẩu hiện tại không đúng")

        # Basic validation: new password length
        if not new_password or len(new_password) < 6:
            raise InvalidCredentialsException(
                "Mật khẩu mới không hợp lệ (tối thiểu 6 ký tự)")

        # Avoid same password
        if self.verify_password(new_password, user.hashed_password):
            raise InvalidCredentialsException(
                "Mật khẩu mới phải khác mật khẩu hiện tại")

        # Update password
        user.hashed_password = self.get_password_hash(new_password)
        await db.commit()

        # Revoke existing refresh tokens
        await db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        await db.commit()

        return True

    async def get_user_by_id(self, user_id: int, db: AsyncSession) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str, db: AsyncSession) -> Optional[User]:
        """Get user by username"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def deactivate_user(self, user: User, db: AsyncSession) -> bool:
        """Soft delete account: set is_active=False and revoke all refresh tokens"""
        try:
            user.is_active = False
            await db.commit()
            await db.execute(
                delete(RefreshToken).where(RefreshToken.user_id == user.id)
            )
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            return False

    async def update_user_profile(self, user: User, update_data: dict, db: AsyncSession) -> User:
        """Update user profile (username, full_name)"""
        try:
            # Check if username is being updated and if it's unique
            if 'username' in update_data and update_data['username'] != user.username:
                existing_user = await self.get_user_by_username(update_data['username'], db)
                if existing_user:
                    raise HTTPException(
                        status_code=400, 
                        detail="Username đã được sử dụng"
                    )
                user.username = update_data['username']
            
            # Update full_name if provided
            if 'full_name' in update_data:
                user.full_name = update_data['full_name']
            
            await db.commit()
            await db.refresh(user)
            return user
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi cập nhật profile: {str(e)}")

    async def upload_user_avatar(self, user: User, image: UploadFile, db: AsyncSession) -> User:
        """Upload avatar for user"""
        from src.storage import S3StorageService
        
        # Validate content-type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File phải là hình ảnh")
        
        try:
            storage_service = S3StorageService()
            
            # Delete old avatar if exists and it's not the default avatar
            if user.avatar_url and user.avatar_url != settings.DEFAULT_AVATAR_URL:
                storage_service.delete_file(user.avatar_url)
            
            # Upload new avatar to S3
            url = storage_service.upload_fileobj(
                image.file, 
                image.content_type, 
                key_prefix="avatars/"
            )
            
            # Update user with new avatar URL
            user.avatar_url = url
            await db.commit()
            await db.refresh(user)
            
            return user
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi upload avatar: {str(e)}")
