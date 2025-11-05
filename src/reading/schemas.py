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
    word_count: Optional[int] = Field(None, ge=100, le=1000, description="Word count (100-1000)")
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

class ReadingSessionSummary(CustomModel):
    """Summary schema for reading session list"""
    id: int
    level: ReadingLevel
    genre: ReadingGenre
    topic: str
    word_count: int
    is_custom: bool

class ReadingSessionDetail(CustomModel):
    """Detail schema for reading session"""
    id: int
    content: str
    level: ReadingLevel
    genre: ReadingGenre
    topic: str
    word_count: int
    is_custom: bool

# Answer evaluation schemas
class AnswerSubmission(CustomModel):
    """Request schema for answer submission"""
    question: str = Field(..., description="Discussion question (in English or Vietnamese)")
    answer: str = Field(..., min_length=20, max_length=2000, description="User's answer in Vietnamese or English")

class AnswerFeedback(CustomModel):
    """Response schema for answer feedback"""
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(..., description="Overall feedback and suggestions")

# Quiz schemas
class QuizGenerationRequest(CustomModel):
    """Request schema for quiz generation"""
    number_of_questions: Optional[int] = Field(5, ge=3, le=10, description="Number of questions (3-10)")
    question_language: Optional[str] = Field("vietnamese", description="Language for questions: 'vietnamese' or 'english'")

class QuizQuestion(CustomModel):
    """Schema for quiz question"""
    question: str = Field(..., description="Question text in specified language")
    options: List[str] = Field(..., description="Answer options (plain text, no A/B/C/D prefix) in specified language")
    correctAnswer: int = Field(..., description="Index of correct answer (0-based)")
    explanation: str = Field(..., description="Explanation for the correct answer in specified language")

class QuizResponse(CustomModel):
    """Response schema for quiz generation"""
    questions: List[QuizQuestion] = Field(..., description="List of questions with correct answers")

# Discussion schemas
class DiscussionGenerationRequest(CustomModel):
    """Request schema for discussion generation"""
    number_of_questions: int = Field(3, ge=1, le=10, description="Number of discussion questions (1-10)")

class DiscussionQuestion(CustomModel):
    """Schema for discussion question"""
    questionEn: str = Field(..., description="Question text in English")
    questionVi: str = Field(..., description="Question text in Vietnamese")

class DiscussionResponse(CustomModel):
    """Response schema for discussion generation"""
    questions: List[DiscussionQuestion] = Field(..., description="List of discussion questions in both English and Vietnamese")

# Filter schemas
class ReadingSessionFilter(CustomModel):
    """Filter schema for reading sessions"""
    level: Optional[ReadingLevel] = None
    genre: Optional[ReadingGenre] = None
    is_custom: Optional[bool] = None
