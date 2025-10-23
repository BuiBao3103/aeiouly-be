from pydantic import Field
from typing import Optional, List
from src.models import CustomModel


class DictionaryResponse(CustomModel):
    """Response schema for dictionary lookup"""
    id: int
    expression: str = Field(..., description="Từ vựng tiếng Anh")
    definitions: str = Field(..., description="Định nghĩa tiếng Việt")


class DictionarySearchRequest(CustomModel):
    """Request schema for dictionary search"""
    query: str = Field(..., min_length=1, max_length=100, description="Từ khóa tìm kiếm")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Số lượng kết quả tối đa")


class DictionarySearchResponse(CustomModel):
    """Response schema for dictionary search"""
    results: List[DictionaryResponse] = Field(..., description="Danh sách kết quả tìm kiếm")
    total: int = Field(..., description="Tổng số kết quả tìm được")
    query: str = Field(..., description="Từ khóa tìm kiếm")
    limit: int = Field(..., description="Số lượng kết quả trả về")


class TranslationRequest(CustomModel):
    """Request schema for translation"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate")
    source_language: str = Field("vi", description="Source language code (vi, en, etc.)")
    target_language: str = Field("en", description="Target language code (vi, en, etc.)")


class TranslationResponse(CustomModel):
    """Response schema for translation"""
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    source_language: str = Field(..., description="Source language")
    target_language: str = Field(..., description="Target language")