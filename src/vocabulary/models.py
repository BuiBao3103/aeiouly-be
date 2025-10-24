from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin
from datetime import datetime, timezone


class VocabularySet(Base, SoftDeleteMixin, TimestampMixin):
    """Vocabulary set model - Bộ từ vựng"""
    __tablename__ = "vocabulary_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False, nullable=False)
    total_words = Column(Integer, default=0, nullable=False)  # Tổng số từ vựng trong bộ
    
    # Relationships
    user = relationship("User", back_populates="vocabulary_sets")
    vocabulary_items = relationship("VocabularyItem", back_populates="vocabulary_set", cascade="all, delete-orphan")


class VocabularyItem(Base, SoftDeleteMixin, TimestampMixin):
    """Vocabulary item model - Từ vựng trong bộ từ vựng"""
    __tablename__ = "vocabulary_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vocabulary_set_id = Column(Integer, ForeignKey("vocabulary_sets.id"), nullable=False, index=True)
    dictionary_id = Column(Integer, ForeignKey("dictionary.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="vocabulary_items")
    vocabulary_set = relationship("VocabularySet", back_populates="vocabulary_items")
    dictionary = relationship("Dictionary", back_populates="vocabulary_items")
