"""
Service layer for Users management
"""
import bcrypt
import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func

from src.users.models import User, UserRole
from src.users.schemas import UserCreate, UserUpdate, UserResponse, UserResetPassword
from src.users.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserValidationException
)
from src.pagination import PaginationParams, PaginatedResponse, paginate
from src.vocabulary.models import VocabularySet
from src.config import settings
from src.mailer.service import EmailService

logger = logging.getLogger(__name__)


class UsersService:
    def __init__(self):
        """Initialize UsersService"""
        self.email_service = EmailService()

    def get_password_hash(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> UserResponse:
        """Create a new user"""
        # Check if user already exists
        result = await db.execute(
            select(User).where(
                User.username == user_data.username,
                User.deleted_at.is_(None)
            )
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise UserAlreadyExistsException("Tên đăng nhập đã tồn tại")

        # Check if email already exists
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.deleted_at.is_(None)
            )
        )
        existing_email = result.scalar_one_or_none()
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

            # Flush to assign ID without committing the transaction yet
            await db.flush()

            # Create default vocabulary set for the new user
            default_vocabulary_set = VocabularySet(
                user_id=db_user.id,
                name="Từ vựng của tôi",
                description="Bộ từ vựng mặc định của bạn",
                is_default=True
            )
            db.add(default_vocabulary_set)

            await db.commit()
            await db.refresh(db_user)

            return UserResponse.from_orm(db_user)
        except Exception as e:
            await db.rollback()
            raise UserValidationException(f"Lỗi khi tạo user: {str(e)}")

    async def get_users(self, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[UserResponse]:
        """Get all users with pagination"""
        try:
            # Get total count
            count_result = await db.execute(
                select(func.count(User.id)).where(User.deleted_at.is_(None))
            )
            total = count_result.scalar() or 0

            # Get paginated results
            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(User).where(
                    User.deleted_at.is_(None)
                ).offset(offset).limit(pagination.size)
            )
            users = result.scalars().all()

            # Convert to response objects
            user_responses = [UserResponse.from_orm(user) for user in users]

            # Return paginated response
            return paginate(user_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise UserValidationException(f"Lỗi khi lấy danh sách users: {str(e)}")

    async def get_user_by_id(self, user_id: int, db: AsyncSession) -> UserResponse:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        return UserResponse.from_orm(user)

    async def get_user_by_username(self, username: str, db: AsyncSession) -> UserResponse:
        """Get user by username"""
        result = await db.execute(
            select(User).where(
                User.username == username,
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với username {username}")

        return UserResponse.from_orm(user)

    async def update_user(self, user_id: int, user_data: UserUpdate, db: AsyncSession) -> UserResponse:
        """Update user"""
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Update fields
            if user_data.email is not None:
                # Check if email is already used by another user
                result = await db.execute(
                    select(User).where(
                        and_(
                            User.email == user_data.email,
                            User.id != user_id,
                            User.deleted_at.is_(None)
                        )
                    )
                )
                existing_email = result.scalar_one_or_none()
                if existing_email:
                    raise UserAlreadyExistsException("Email đã được sử dụng bởi user khác")
                user.email = user_data.email

            if user_data.full_name is not None:
                user.full_name = user_data.full_name

            # Note: role cannot be changed via API
            # Admin users must be created manually

            if user_data.is_active is not None:
                user.is_active = user_data.is_active

            await db.commit()
            await db.refresh(user)

            return UserResponse.from_orm(user)
        except Exception as e:
            await db.rollback()
            raise UserValidationException(f"Lỗi khi cập nhật user: {str(e)}")

    async def delete_user(self, user_id: int, db: AsyncSession) -> bool:
        """Soft delete user"""
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Soft delete the record
            user.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise UserValidationException(f"Lỗi khi xóa user: {str(e)}")

    async def reset_user_password(self, user_id: int, reset_data: UserResetPassword, db: AsyncSession) -> UserResponse:
        """Reset user password"""
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"Không tìm thấy user với ID {user_id}")

        try:
            # Hash new password
            hashed_password = self.get_password_hash(reset_data.new_password)

            # Update password
            user.hashed_password = hashed_password

            await db.commit()
            await db.refresh(user)

            if user.email:
                try:
                    display_name = user.username or user.full_name or "bạn"
                    await self.email_service.send_password_changed_email(
                        to_email=user.email,
                        username=display_name,
                        new_password=reset_data.new_password
                    )
                except Exception as email_error:
                    logger.warning(
                        "Failed to send password change email to %s: %s",
                        user.email,
                        email_error,
                    )

            return UserResponse.from_orm(user)
        except Exception as e:
            await db.rollback()
            raise UserValidationException(f"Lỗi khi reset password: {str(e)}")

