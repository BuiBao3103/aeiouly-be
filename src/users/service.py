"""
Service layer for Users management
"""
import bcrypt
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.users.models import User, UserRole
from src.users.schemas import UserCreate, UserUpdate, UserResponse, UserResetPassword
from src.users.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserValidationException
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from src.config import settings


class UsersService:
    def __init__(self):
        """Initialize UsersService"""
        pass

    def get_password_hash(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def create_user(self, user_data: UserCreate, db: Session) -> UserResponse:
        """Create a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(
            User.username == user_data.username,
            User.deleted_at.is_(None)
        ).first()
        if existing_user:
            raise UserAlreadyExistsException("Tên đăng nhập đã tồn tại")

        # Check if email already exists
        existing_email = db.query(User).filter(
            User.email == user_data.email,
            User.deleted_at.is_(None)
        ).first()
        if existing_email:
            raise UserAlreadyExistsException("Email đã được sử dụng")

        try:
            # Hash password
            hashed_password = self.get_password_hash(user_data.password)

            # Create new user (always with USER role, admin can only be created manually)
            db_user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                role=UserRole.USER,  # All new users are regular users
                avatar_url=settings.DEFAULT_AVATAR_URL  # Set default avatar
            )

            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            return UserResponse.from_orm(db_user)
        except Exception as e:
            db.rollback()
            raise UserValidationException(f"Lỗi khi tạo user: {str(e)}")

    def get_users(self, db: Session, pagination: PaginationParams) -> PaginatedResponse[UserResponse]:
        """Get all users with pagination"""
        try:
            # Get total count
            total = db.query(User).filter(User.deleted_at.is_(None)).count()

            # Get paginated results
            offset = (pagination.page - 1) * pagination.size
            users = db.query(User).filter(
                User.deleted_at.is_(None)
            ).offset(offset).limit(pagination.size).all()

            # Convert to response objects
            user_responses = [UserResponse.from_orm(user) for user in users]

            # Return paginated response
            return paginate(user_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise UserValidationException(f"Lỗi khi lấy danh sách users: {str(e)}")

    def get_user_by_id(self, user_id: int, db: Session) -> UserResponse:
        """Get user by ID"""
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        return UserResponse.from_orm(user)

    def get_user_by_username(self, username: str, db: Session) -> UserResponse:
        """Get user by username"""
        user = db.query(User).filter(
            User.username == username,
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với username {username}")

        return UserResponse.from_orm(user)

    def update_user(self, user_id: int, user_data: UserUpdate, db: Session) -> UserResponse:
        """Update user"""
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Update fields
            if user_data.email is not None:
                # Check if email is already used by another user
                existing_email = db.query(User).filter(
                    and_(
                        User.email == user_data.email,
                        User.id != user_id,
                        User.deleted_at.is_(None)
                    )
                ).first()
                if existing_email:
                    raise UserAlreadyExistsException("Email đã được sử dụng bởi user khác")
                user.email = user_data.email

            if user_data.full_name is not None:
                user.full_name = user_data.full_name

            # Note: role cannot be changed via API
            # Admin users must be created manually

            if user_data.is_active is not None:
                user.is_active = user_data.is_active

            db.commit()
            db.refresh(user)

            return UserResponse.from_orm(user)
        except Exception as e:
            db.rollback()
            raise UserValidationException(f"Lỗi khi cập nhật user: {str(e)}")

    def delete_user(self, user_id: int, db: Session) -> bool:
        """Soft delete user"""
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Soft delete the record
            user.deleted_at = datetime.now(timezone.utc)

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise UserValidationException(f"Lỗi khi xóa user: {str(e)}")

    def reset_user_password(self, user_id: int, reset_data: UserResetPassword, db: Session) -> UserResponse:
        """Reset user password"""
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Hash new password
            hashed_password = self.get_password_hash(reset_data.new_password)

            # Update password
            user.hashed_password = hashed_password

            db.commit()
            db.refresh(user)

            return UserResponse.from_orm(user)
        except Exception as e:
            db.rollback()
            raise UserValidationException(f"Lỗi khi reset password: {str(e)}")

