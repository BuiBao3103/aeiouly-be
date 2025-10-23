from typing import List, Optional
import re
import httpx
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, case
from src.dictionary.models import Dictionary
from src.dictionary.schemas import (
    DictionarySearchRequest, DictionarySearchResponse, DictionaryResponse,
    TranslationRequest, TranslationResponse
)
from src.config import settings


class DictionaryService:
    """Service for dictionary operations"""

    def __init__(self):
        # Initialize service instance
        pass

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
        Translate text using Google Cloud Translation API REST endpoint
        """
        try:
            # Get Google Cloud Translation API key from settings
            api_key = settings.GOOGLE_TRANSLATE_API_KEY
            if not api_key:
                raise ValueError("Google Translate API key not configured")
            
            # Google Cloud Translation API endpoint
            url = "https://translation.googleapis.com/language/translate/v2"
            
            # Request parameters
            params = {
                "key": api_key,
                "q": request.text,
                "target": request.target_language,
                "format": "text"
            }
            
            # Add source language if specified
            if request.source_language:
                params["source"] = request.source_language
            
            # Headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Aeiouly-Translation-API/1.0"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extract translation from Google Cloud API response
                if "data" in result and "translations" in result["data"]:
                    translations = result["data"]["translations"]
                    if translations and len(translations) > 0:
                        translation = translations[0]
                        translated_text = translation.get("translatedText", request.text)
                        
                        return TranslationResponse(
                            original_text=request.text,
                            translated_text=translated_text,
                            source_language=request.source_language,
                            target_language=request.target_language
                        )
                
                # If no translation found, return original text
                return TranslationResponse(
                    original_text=request.text,
                    translated_text=request.text,
                    source_language=request.source_language,
                    target_language=request.target_language
                )
                
        except Exception as e:
            print(f"Translation error: {str(e)}")
            print("Please check if GOOGLE_TRANSLATE_API_KEY is configured correctly and Translation API is enabled.")
            # Raise HTTP 500 error instead of returning original text
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {str(e)}"
            )


