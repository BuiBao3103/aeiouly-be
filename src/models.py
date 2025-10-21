from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict


def datetime_to_gmt_str(dt: datetime) -> str:
    """Convert datetime to GMT string format"""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class CustomModel(BaseModel):
    """Custom base model with global configurations"""
    model_config = ConfigDict(
        json_encoders={datetime: datetime_to_gmt_str},
        populate_by_name=True,
        from_attributes=True,
    )

    def serializable_dict(self, **kwargs) -> Dict[str, Any]:
        """Return a dict which contains only serializable fields."""
        default_dict = self.model_dump()
        return jsonable_encoder(default_dict)


# Import all SQLAlchemy models to ensure they are registered with Base.metadata
# This is needed for Alembic to detect all models
from src.auth.models import UserRole, User, PasswordResetToken, RefreshToken
from src.analytics.models import LearningSession, LoginStreak
from src.posts.models import Post, PostLike
from src.dictionary.models import Dictionary
from src.writing.models import WritingSession, WritingChatMessage