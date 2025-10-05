"""
Service layer for Auth module with instance methods
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from jose import jwt
from sqlalchemy.orm import Session
from fastapi import Response
from src.auth.models import User, PasswordResetToken, RefreshToken
from src.auth.schemas import UserRole
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
from src.analytics.streak_service import LoginStreakService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        self.email_service = EmailService()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
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

    async def register_user(self, user_data: UserCreate, db: Session) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(
            User.username == user_data.username).first()
        if existing_user:
            raise UserAlreadyExistsException("Tên đăng nhập đã tồn tại")

        # Check if email already exists
        existing_email = db.query(User).filter(
            User.email == user_data.email).first()
        if existing_email:
            raise UserAlreadyExistsException("Email đã được sử dụng")

        # Create new user
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=UserRole.USER  # Default role for new users
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Send welcome email
        try:
            await self.email_service.send_welcome_email(db_user.email, db_user.username)
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send welcome email: {e}")

        return db_user

    async def authenticate_user(self, username: str, password: str, db: Session) -> Optional[User]:
        """Authenticate user with username and password"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, username: str, password: str, db: Session) -> Token:
        """Login user and return tokens"""
        user = await self.authenticate_user(username, password, db)
        if not user:
            raise InvalidCredentialsException(
                "Tên đăng nhập hoặc mật khẩu không đúng")

        # Record login streak
        try:
            streak_service = LoginStreakService()
            await streak_service.record_login(user.id, db)
        except Exception as e:
            print(f"Error recording login streak: {e}")
            # Don't fail login if streak recording fails

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
        db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    async def refresh_access_token(self, refresh_token: str, db: Session) -> Token:
        """Refresh access token using refresh token"""
        # Find refresh token in database
        db_refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token).first()
        if not db_refresh_token:
            raise RefreshTokenRevokedException("Refresh token không hợp lệ")

        # Check if refresh token is expired
        if is_token_expired(db_refresh_token.expires_at):
            # Remove expired token
            db.delete(db_refresh_token)
            db.commit()
            raise RefreshTokenExpiredException("Refresh token đã hết hạn")

        # Get user
        user = db.query(User).filter(
            User.id == db_refresh_token.user_id).first()
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
        db.commit()

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    async def logout(self, refresh_token: str, db: Session) -> bool:
        """Logout user by revoking refresh token"""
        db_refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token).first()
        if db_refresh_token:
            db.delete(db_refresh_token)
            db.commit()
            return True
        return False

    async def request_password_reset(self, email: str, db: Session) -> bool:
        """Request password reset for user"""
        user = db.query(User).filter(User.email == email).first()
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
        db.commit()

        # Send reset email
        reset_url = f"{settings.CLIENT_SIDE_URL}/reset-password"
        await self.email_service.send_password_reset_email(user.email, user.full_name, reset_token, reset_url)

        return True

    async def reset_password(self, reset_data: PasswordResetConfirm, db: Session) -> bool:
        """Reset user password using reset token"""
        # Find reset token
        reset_token_obj = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == reset_data.token).first()
        if not reset_token_obj:
            raise PasswordResetTokenInvalidException(
                "Token reset password không hợp lệ")

        # Check if token is expired
        if is_token_expired(reset_token_obj.expires_at):
            # Remove expired token
            db.delete(reset_token_obj)
            db.commit()
            raise PasswordResetTokenExpiredException(
                "Token reset password đã hết hạn")

        # Get user
        user = db.query(User).filter(
            User.email == reset_token_obj.email).first()
        if not user:
            raise UserNotFoundException("Không tìm thấy người dùng")

        # Update password
        user.hashed_password = self.get_password_hash(reset_data.new_password)
        db.commit()

        # Remove reset token
        db.delete(reset_token_obj)
        db.commit()

        return True

    async def change_password(self, user: User, current_password: str, new_password: str, db: Session) -> bool:
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
        db.commit()

        # Revoke existing refresh tokens
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.commit()

        return True

    async def get_user_by_id(self, user_id: int, db: Session) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    async def get_user_by_username(self, username: str, db: Session) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    async def get_user_by_email(self, email: str, db: Session) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    async def deactivate_user(self, user: User, db: Session) -> bool:
        """Soft delete account: set is_active=False and revoke all refresh tokens"""
        try:
            user.is_active = False
            db.commit()
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user.id).delete()
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    async def update_user_profile(self, user: User, update_data: dict, db: Session) -> User:
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
            
            db.commit()
            db.refresh(user)
            return user
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi cập nhật profile: {str(e)}")

    async def upload_user_avatar(self, user: User, image: UploadFile, db: Session) -> User:
        """Upload avatar for user"""
        from src.storage import S3StorageService
        
        # Validate content-type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File phải là hình ảnh")
        
        try:
            storage_service = S3StorageService()
            
            # Delete old avatar if exists
            if user.avatar_url:
                storage_service.delete_file(user.avatar_url)
            
            # Upload new avatar to S3
            url = storage_service.upload_fileobj(
                image.file, 
                image.content_type, 
                key_prefix="avatars/"
            )
            
            # Update user with new avatar URL
            user.avatar_url = url
            db.commit()
            db.refresh(user)
            
            return user
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi upload avatar: {str(e)}")
