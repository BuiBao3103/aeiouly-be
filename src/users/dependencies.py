"""
Dependencies for Users module
"""
from src.users.service import UsersService


def get_users_service() -> UsersService:
    """Dependency to get UsersService instance"""
    return UsersService()

