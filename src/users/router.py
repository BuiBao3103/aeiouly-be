"""
Router for Users module
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.users.service import UsersService
from src.users.schemas import UserCreate, UserUpdate, UserResponse, UserResetPassword
from src.users.dependencies import get_users_service
from src.users.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserValidationException,
    user_not_found_exception,
    user_already_exists_exception,
    user_validation_exception
)
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo user mới
    - Chỉ admin mới có thể tạo user
    - **username**: Tên đăng nhập (unique)
    - **email**: Email (unique)
    - **password**: Mật khẩu (tối thiểu 6 ký tự)
    - **full_name**: Họ tên (optional)
    - Tất cả users tạo qua API đều có role USER
    - Admin users phải được tạo thủ công
    """
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có thể tạo user"
        )

    try:
        return await service.create_user(user_data, db)
    except UserAlreadyExistsException as e:
        raise user_already_exists_exception(str(e))
    except UserValidationException as e:
        raise user_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo user: {str(e)}")


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách users với phân trang
    - Chỉ admin mới có thể xem danh sách users
    - **page**: Số trang (mặc định: 1)
    - **size**: Số bản ghi mỗi trang (mặc định: 10, tối đa: 100)
    """
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có thể xem danh sách users"
        )

    try:
        return await service.get_users(db, pagination)
    except UserValidationException as e:
        raise user_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách users: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thông tin user theo ID
    - Chỉ admin hoặc chính user đó mới có thể xem
    - **user_id**: ID của user
    """
    # Check if user is admin or viewing their own profile
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể xem thông tin của chính mình"
        )

    try:
        return await service.get_user_by_id(user_id, db)
    except UserNotFoundException as e:
        raise user_not_found_exception(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin user: {str(e)}")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật thông tin user
    - Chỉ admin hoặc chính user đó mới có thể cập nhật
    - **user_id**: ID của user
    - **email**: Email (optional)
    - **full_name**: Họ tên (optional)
    - **is_active**: Trạng thái hoạt động (optional, chỉ admin mới có thể thay đổi)
    - Note: role không thể thay đổi qua API
    """
    # Check if user is admin or updating their own profile
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể cập nhật thông tin của chính mình"
        )

    # Check if user trying to change is_active (only admin can do this)
    if current_user.role.value != "admin" and user_data.is_active is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thay đổi trạng thái hoạt động"
        )

    try:
        return await service.update_user(user_id, user_data, db)
    except UserNotFoundException as e:
        raise user_not_found_exception(user_id)
    except UserAlreadyExistsException as e:
        raise user_already_exists_exception(str(e))
    except UserValidationException as e:
        raise user_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật user: {str(e)}")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa user (soft delete)
    - Chỉ admin mới có thể xóa user
    - **user_id**: ID của user
    """
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có thể xóa user"
        )

    try:
        success = await service.delete_user(user_id, db)
        if not success:
            raise HTTPException(status_code=500, detail="Không thể xóa user")
    except UserNotFoundException as e:
        raise user_not_found_exception(user_id)
    except UserValidationException as e:
        raise user_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa user: {str(e)}")


@router.post("/{user_id}/reset-password", response_model=UserResponse)
async def reset_user_password(
    user_id: int,
    reset_data: UserResetPassword,
    current_user: User = Depends(get_current_active_user),
    service: UsersService = Depends(get_users_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password cho user
    - Chỉ admin mới có thể reset password của user khác
    - **user_id**: ID của user
    - **new_password**: Mật khẩu mới (tối thiểu 6 ký tự)
    """
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có thể reset password"
        )

    try:
        return await service.reset_user_password(user_id, reset_data, db)
    except UserNotFoundException as e:
        raise user_not_found_exception(user_id)
    except UserValidationException as e:
        raise user_validation_exception(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi reset password: {str(e)}")

