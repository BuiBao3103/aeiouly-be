from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin

# Import User and UserRole from users module
from src.users.models import User, UserRole

class PasswordResetToken(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    # moved to TimestampMixin

class RefreshToken(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    # moved to TimestampMixin

    # Relationship
    user = relationship("User", back_populates="refresh_tokens") 