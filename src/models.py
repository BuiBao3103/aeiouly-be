# Import all models to ensure they are registered with SQLAlchemy
# This file should be imported after database.py is initialized

from src.auth.models import User, PasswordResetToken, RefreshToken
from src.posts.models import Post

# Import email module to ensure templates are loaded
import src.mailer.service

# This ensures all models are registered with SQLAlchemy metadata
__all__ = ["User", "PasswordResetToken", "RefreshToken", "Post"] 