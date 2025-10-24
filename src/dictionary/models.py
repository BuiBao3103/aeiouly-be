from sqlalchemy import Column, BigInteger, Text, Index
from sqlalchemy.orm import relationship
from src.database import Base
from src.orm_mixins import SoftDeleteMixin, TimestampMixin


class Dictionary(Base, SoftDeleteMixin, TimestampMixin):
    """English-Vietnamese dictionary table"""
    __tablename__ = "dictionary"

    id = Column(BigInteger, primary_key=True, index=True)
    expression = Column(Text, nullable=False)  # headword
    definitions = Column(Text, nullable=False)  # raw glossary text

    # Relationships
    vocabulary_items = relationship("VocabularyItem", back_populates="dictionary")

    # Basic indexes (only on expression, definitions too large for btree index)
    __table_args__ = (
        Index('ix_dictionary_expression', 'expression'),
    )
