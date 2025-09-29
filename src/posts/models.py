from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin

class Post(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    is_published = Column(Boolean, default=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(String(512), nullable=True)
    # moved to TimestampMixin

    # Relationship
    author = relationship("User", back_populates="posts")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")

class PostLike(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    # moved to TimestampMixin

    # Relationships
    user = relationship("User", back_populates="liked_posts")
    post = relationship("Post", back_populates="likes")

    # Constraint để đảm bảo 1 user chỉ like 1 post 1 lần
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),) 