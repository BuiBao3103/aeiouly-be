from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.models import CustomModel
from src.constants.cefr import CEFRLevel
from src.reading.models import ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel

# Request schemas
class ReadingSessionCreateAI(CustomModel):
    """Request schema for AI-generated reading session"""
    level: ReadingLevel = Field(..., description="Reading level (A1-C2)")
    genre: ReadingGenre = Field(..., description="Reading genre")
    word_count: Optional[int] = Field(None, ge=100, le=1000, description="Word count (100-1000)")
    topic: Optional[str] = Field(None, max_length=200, description="Reading topic")

class ReadingSessionCreateCustom(CustomModel):
    """Request schema for custom text reading session"""
    custom_text: str = Field(..., min_length=100, max_length=5000, description="Custom reading text")

class ReadingSessionCreate(CustomModel):
    """Union schema for reading session creation"""
    # AI generation fields
    level: Optional[ReadingLevel] = None
    genre: Optional[ReadingGenre] = None
    topic: Optional[str] = Field(None, max_length=200)
    
    # Custom text field
    custom_text: Optional[str] = Field(None, min_length=100, max_length=5000)

# Response schemas
class ReadingSessionResponse(CustomModel):
    """Response schema for reading session"""
    id: int
    content: str
    word_count: int
    level: ReadingLevel
    genre: ReadingGenre
    topic: str
    is_custom: bool
    created_at: datetime

class ReadingSessionSummary(CustomModel):
    """Summary schema for reading session list"""
    session_id: int
    level: ReadingLevel
    genre: ReadingGenre
    topic: str
    word_count: int
    is_custom: bool
    created_at: datetime

class ReadingSessionDetail(CustomModel):
    """Detail schema for reading session"""
    session_id: int
    content: str
    level: ReadingLevel
    genre: ReadingGenre
    topic: str
    word_count: int
    is_custom: bool
    created_at: datetime

# Summary evaluation schemas
class SummarySubmission(CustomModel):
    """Request schema for summary submission"""
    vietnamese_summary: str = Field(..., min_length=50, max_length=2000, description="Vietnamese summary")

class SummaryFeedback(CustomModel):
    """Response schema for summary feedback"""
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(..., description="Overall feedback and suggestions")

# Quiz schemas
class QuizGenerationRequest(CustomModel):
    """Request schema for quiz generation"""
    number_of_questions: Optional[int] = Field(5, ge=3, le=10, description="Number of questions (3-10)")

class CorrectAnswer(CustomModel):
    """Schema for correct answer"""
    correct_option: str = Field(..., description="Correct answer option")
    explanation: str = Field(..., description="Explanation for the answer")

class QuizQuestion(CustomModel):
    """Schema for quiz question"""
    id: str = Field(..., description="Question ID")
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., description="Answer options")
    type: str = Field(..., description="Question type: multiple_choice or true_false")
    correct_answer: CorrectAnswer = Field(..., description="Correct answer with explanation")

class QuizResponse(CustomModel):
    """Response schema for quiz generation"""
    questions: List[QuizQuestion] = Field(..., description="List of questions with correct answers")

# Filter schemas
class ReadingSessionFilter(CustomModel):
    """Filter schema for reading sessions"""
    level: Optional[ReadingLevel] = None
    genre: Optional[ReadingGenre] = None
    is_custom: Optional[bool] = None
