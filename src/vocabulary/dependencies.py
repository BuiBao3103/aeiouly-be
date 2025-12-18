from fastapi import Depends
from src.vocabulary.service import VocabularyService

def get_vocabulary_service() -> VocabularyService:
    """Get VocabularyService instance"""
    return VocabularyService()
