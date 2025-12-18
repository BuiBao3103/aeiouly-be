from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
from src.constants.cefr import CEFRLevel
import enum

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel

class ReadingGenre(str, enum.Enum):
    ARTICLE = "Bài báo"
    EMAIL = "Email/Thư từ"
    SHORT_STORY = "Truyện ngắn"
    CONVERSATION = "Hội thoại"
    ESSAY = "Bài luận"
    PRODUCT_REVIEW = "Đánh giá sản phẩm"
    SOCIAL_MEDIA = "Bài mạng xã hội"
    USER_GUIDE = "Hướng dẫn sử dụng"

class ReadingSession(Base, SoftDeleteMixin, TimestampMixin):
    """Reading session for English practice"""
    __tablename__ = "reading_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    level = Column(String(2), nullable=False, index=True)  # A1, A2, B1, B2, C1, C2
    genre = Column(String(50), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    is_custom = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="reading_sessions")
