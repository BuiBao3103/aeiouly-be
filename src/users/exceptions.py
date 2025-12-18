"""
Exceptions for Users module
"""
from fastapi import HTTPException


class UserException(Exception):
    """Base exception for User operations"""
    pass


class UserNotFoundException(UserException):
    """Raised when user is not found"""
    pass


class UserAlreadyExistsException(UserException):
    """Raised when user already exists"""
    pass


class UserValidationException(UserException):
    """Raised when user validation fails"""
    pass


# HTTP Exceptions
def user_not_found_exception(user_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy user với ID {user_id}"
    )


def user_already_exists_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=message
    )


def user_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=message
    )

