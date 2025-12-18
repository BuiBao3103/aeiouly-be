from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
from datetime import datetime, timezone
import enum


class SessionGoalsStatus(str, enum.Enum):
    """Session goal status enum"""
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"


class BackgroundVideoType(Base, SoftDeleteMixin, TimestampMixin):
    """Background video type model - Loại video nền"""
    __tablename__ = "background_video_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # Relationships
    videos = relationship("BackgroundVideo", back_populates="type")


class BackgroundVideo(Base, SoftDeleteMixin, TimestampMixin):
    """Background video model - Video nền"""
    __tablename__ = "background_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    youtube_url = Column(String(500), nullable=False)
    image_url = Column(String(500))  # Thay thế CloudinaryField bằng URL string
    type_id = Column(Integer, ForeignKey("background_video_types.id"), nullable=False)
    
    # Relationships
    type = relationship("BackgroundVideoType", back_populates="videos")


class SessionGoal(Base, SoftDeleteMixin, TimestampMixin):
    """Session goal model - Mục tiêu phiên học"""
    __tablename__ = "session_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    goal = Column(String(255), nullable=False)
    status = Column(Enum(SessionGoalsStatus), default=SessionGoalsStatus.OPEN, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="session_goals")


class UserFavoriteVideo(Base, SoftDeleteMixin, TimestampMixin):
    """User favorite video model - Video yêu thích của user"""
    __tablename__ = "user_favorite_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    youtube_url = Column(String(500), nullable=False)
    image_url = Column(String(500))  # Thay thế image field bằng URL string
    name = Column(String(255), default="")
    author_name = Column(String(255), default="")
    author_url = Column(String(500), default="")
    
    # Relationships
    user = relationship("User", back_populates="favorite_videos")
    
    # Unique constraint sẽ được thêm trong migration
    __table_args__ = (
        # Unique constraint cho user_id và youtube_url
        # Sẽ được implement trong migration
    )


class Sound(Base, SoftDeleteMixin, TimestampMixin):
    """Sound model - Nhạc nền"""
    __tablename__ = "sounds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sound_file_url = Column(String(500), nullable=True)  # Thay thế FileField bằng URL string
    file_size = Column(Integer)  # Kích thước file (bytes)
    duration = Column(Integer)  # Thời lượng (seconds)
    
    def __str__(self):
        return self.name
