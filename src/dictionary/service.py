from typing import List, Optional
import re
import os
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, case
from google.cloud import translate_v2 as translate
from src.dictionary.models import Dictionary
from src.dictionary.schemas import (
    DictionarySearchRequest, DictionarySearchResponse, DictionaryResponse,
    TranslationRequest, TranslationResponse
)
from src.config import settings


class DictionaryService:
    """Service for dictionary operations"""

    def __init__(self):
        """Initialize DictionaryService with Google Cloud Translation client"""
        # Set credentials if provided
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            # Resolve relative path to absolute path
            cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
            if not os.path.isabs(cred_path):
                # Get project root (2 levels up from src/dictionary/service.py)
                project_root = Path(__file__).resolve().parent.parent.parent
                cred_path = project_root / cred_path
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(cred_path)
        
        # Initialize Translation client
        try:
            self.translate_client = translate.Client()
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Translation client: {e}")
            self.translate_client = None

    def _get_base_forms(self, word: str) -> List[str]:
        """Get base forms of a word by removing common suffixes"""
        base_forms = [word]
        
        # Common English suffixes
        suffixes = [
            'ed', 'ing', 's', 'es', 'er', 'est', 'ly', 'tion', 'sion', 
            'ness', 'ment', 'able', 'ible', 'ful', 'less', 'ive', 'ous',
            'ize', 'ise', 'ify', 'en', 'al', 'ic', 'ical', 'ous', 'eous',
            'ious', 'ary', 'ory', 'ty', 'ity', 'cy', 'sy', 'fy', 'my'
        ]
        
        # Try removing suffixes
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                base_form = word[:-len(suffix)]
                if base_form not in base_forms:
                    base_forms.append(base_form)
        
        # Special cases for common patterns
        if word.endswith('ied'):
            base_forms.append(word[:-3] + 'y')
        if word.endswith('ies'):
            base_forms.append(word[:-3] + 'y')
        if word.endswith('ied'):
            base_forms.append(word[:-3] + 'y')
        
        return base_forms

    async def search_words(
        self, 
        db: Session, 
        request: DictionarySearchRequest
    ) -> DictionarySearchResponse:
        """
        Search for words in dictionary using PostgreSQL full-text search
        """
        query = request.query.strip().lower()
        limit = request.limit or 10

        # Build search query with multiple strategies
        search_conditions = []
        
        # Strategy 1: Exact match
        search_conditions.append(Dictionary.expression.ilike(f"%{query}%"))
        
        # Strategy 2: Remove common suffixes and search
        base_forms = self._get_base_forms(query)
        for base_form in base_forms:
            search_conditions.append(Dictionary.expression.ilike(f"%{base_form}%"))
        
        # Strategy 3: Search for words that start with the base form
        for base_form in base_forms:
            search_conditions.append(Dictionary.expression.ilike(f"{base_form}%"))
        
        search_query = db.query(Dictionary).filter(
            or_(*search_conditions)
        ).order_by(
            # Prioritize exact matches first
            case(
                (Dictionary.expression.ilike(f"%{query}%"), 1),
                else_=2
            ),
            Dictionary.expression.asc()
        ).limit(limit)

        # Get results
        results = search_query.all()
        
        # Convert to response format
        dictionary_results = [
            DictionaryResponse(
                id=result.id,
                expression=result.expression,
                definitions=result.definitions
            )
            for result in results
        ]

        # Get total count for the same query (without limit)
        total_query = db.query(Dictionary).filter(
            or_(*search_conditions)
        )
        total = total_query.count()

        return DictionarySearchResponse(
            results=dictionary_results,
            total=total,
            query=request.query,
            limit=limit
        )

    async def get_word_by_id(self, db: Session, word_id: int) -> Optional[DictionaryResponse]:
        """
        Get a specific word by ID
        """
        result = db.query(Dictionary).filter(Dictionary.id == word_id).first()
        
        if not result:
            return None
            
        return DictionaryResponse(
            id=result.id,
            expression=result.expression,
            definitions=result.definitions
        )

    async def get_word_by_expression(self, db: Session, expression: str) -> Optional[DictionaryResponse]:
        """
        Get a specific word by exact expression match
        """
        result = db.query(Dictionary).filter(
            Dictionary.expression.ilike(expression.strip())
        ).first()
        
        if not result:
            return None
            
        return DictionaryResponse(
            id=result.id,
            expression=result.expression,
            definitions=result.definitions
        )

    async def find_single_word_with_suffixes(self, db: Session, word: str) -> Optional[DictionaryResponse]:
        """
        Find a single word with suffix support (stemming)
        Returns the first match found
        """
        word = word.strip().lower()
        
        # Build search conditions with suffix support
        search_conditions = []
        
        # Strategy 1: Exact match
        search_conditions.append(Dictionary.expression.ilike(word))
        
        # Strategy 2: Remove suffixes and search
        base_forms = self._get_base_forms(word)
        for base_form in base_forms:
            search_conditions.append(Dictionary.expression.ilike(base_form))
        
        # Strategy 3: Search for words that start with the base form
        for base_form in base_forms:
            search_conditions.append(Dictionary.expression.ilike(f"{base_form}%"))
        
        # Find the first match with priority order
        result = db.query(Dictionary).filter(
            or_(*search_conditions)
        ).order_by(
            # Prioritize exact matches first
            case(
                (Dictionary.expression.ilike(word), 1),
                else_=2
            ),
            Dictionary.expression.asc()
        ).first()
        
        if not result:
            return None
            
        return DictionaryResponse(
            id=result.id,
            expression=result.expression,
            definitions=result.definitions
        )

    async def get_random_words(self, db: Session, limit: int = 10) -> List[DictionaryResponse]:
        """
        Get random words from dictionary
        """
        results = db.query(Dictionary).order_by(func.random()).limit(limit).all()
        
        return [
            DictionaryResponse(
                id=result.id,
                expression=result.expression,
                definitions=result.definitions
            )
            for result in results
        ]

    async def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text using Google Cloud Translation API
        """
        if not self.translate_client:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail="Google Cloud Translation client chưa được khởi tạo"
            )
        
        try:
            # Translate text using google-cloud-translate v2 client
            # Signature: translate(values, target_language=None, format_=None, source_language=None, ...)
            if request.source_language:
                result = self.translate_client.translate(
                    request.text,
                    target_language=request.target_language,
                    source_language=request.source_language,
                    format_="text",
                )
            else:
                result = self.translate_client.translate(
                    request.text,
                    target_language=request.target_language,
                    format_="text",
                )
            
            # Extract translated text
            translated_text = result.get('translatedText', request.text)
            
            return TranslationResponse(
                original_text=request.text,
                translated_text=translated_text,
                source_language=request.source_language,
                target_language=request.target_language
            )
                
        except Exception as e:
            print(f"Translation error: {str(e)}")
            print("Please check if GOOGLE_APPLICATION_CREDENTIALS is configured correctly and Translation API is enabled.")
            # Raise HTTP 500 error instead of returning original text
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {str(e)}"
            )


