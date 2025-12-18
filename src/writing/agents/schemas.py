"""
Schemas and constants for sub-agents.
"""
from typing import List
from pydantic import BaseModel, Field


class ChatAgentResponse(BaseModel):
    response_text: str = Field(
        description="Final message for learner in Vietnamese"
    )


class TranslationEvaluationResponse(BaseModel):
    response_text: str = Field(
        description="Final message for learner in Vietnamese"
    )
    is_correct: bool = Field(
        description="Whether the translation is correct (True) or has errors (False)"
    )


class VietnameseTextResult(BaseModel):
    sentences: List[str] = Field(
        description="Array of individual Vietnamese sentences"
    )


class HintResult(BaseModel):
    hint_text: str = Field(
        description="Vietnamese Markdown hint (vocabulary + grammar) using '- ' list syntax per line"
    )


class FinalEvaluationResult(BaseModel):
    overall_score: float = Field(
        ge=0, le=100, description="Tổng điểm tổng thể từ 0-100")
    accuracy_score: float = Field(
        ge=0, le=100, description="Điểm chính xác ngữ nghĩa từ 0-100")
    fluency_score: float = Field(
        ge=0, le=100, description="Điểm trôi chảy và tự nhiên từ 0-100")
    vocabulary_score: float = Field(
        ge=0, le=100, description="Điểm từ vựng từ 0-100")
    grammar_score: float = Field(
        ge=0, le=100, description="Điểm ngữ pháp từ 0-100")
    feedback: str = Field(description="Nhận xét tổng thể bằng tiếng Việt")
    suggestions: List[str] = Field(description="Danh sách gợi ý cải thiện")
