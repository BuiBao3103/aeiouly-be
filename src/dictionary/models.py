from sqlalchemy import Column, BigInteger, Text, Index
from src.database import Base


class Dictionary(Base):
    """English-Vietnamese dictionary table"""
    __tablename__ = "dictionary"

    id = Column(BigInteger, primary_key=True, index=True)
    expression = Column(Text, nullable=False)  # headword
    definitions = Column(Text, nullable=False)  # raw glossary text


    # Basic indexes (only on expression, definitions too large for btree index)
    __table_args__ = (
        Index('ix_dictionary_expression', 'expression'),
    )
