from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base

# Import all models here to ensure they are registered with SQLAlchemy
from src.auth.models import User
from src.posts.models import Post

# Add relationship to User model
User.posts = relationship("Post", back_populates="author") 