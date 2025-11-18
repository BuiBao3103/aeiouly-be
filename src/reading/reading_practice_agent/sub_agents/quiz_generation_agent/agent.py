from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class QuizQuestion(BaseModel):
    """Schema for quiz question"""
    questionEn: str = Field(..., description="Question text in English")
    questionVi: str = Field(..., description="Question text in Vietnamese")
    optionsEn: List[str] = Field(..., description="Answer options in English (plain text, no A/B/C/D prefix)")
    optionsVi: List[str] = Field(..., description="Answer options in Vietnamese (plain text, no A/B/C/D prefix)")
    correctAnswer: int = Field(..., description="Index of correct answer (0-based)")
    explanationEn: str = Field(..., description="Explanation for the correct answer in English")
    explanationVi: str = Field(..., description="Explanation for the correct answer in Vietnamese")

class QuizGenerationRequest(BaseModel):
    """Request schema for quiz generation"""
    number_of_questions: int = Field(..., ge=3, le=10, description="Number of questions")

class QuizGenerationResult(BaseModel):
    """Response schema for quiz generation"""
    questions: List[QuizQuestion] = Field(..., description="List of questions with correct answers")

quiz_generation_agent = LlmAgent(
    name="quiz_generation_agent",
    model="gemini-2.0-flash",
    description="Generates quizzes from English reading texts to test comprehension",
    instruction="""
    You are an AI that creates bilingual comprehension quizzes from the reading text stored in state.
    
    DATA AVAILABLE:
    - Reading text content: {content}
    - Number of questions: provided in the incoming request
    
    TASK:
    - Read the text from state and craft multiple-choice questions that test understanding (not memorization).
    - Provide both English and Vietnamese versions for every question, option, and explanation.
    - Ensure each question has exactly four options (A-D), one correct answer, and clear explanations.
    - Balance question types (main idea, detail, inference, vocabulary, author's purpose, tone, etc.).
    - Questions must stay faithful to the text; Vietnamese content must be accurate translations of English content.
    
    RULES:
    - `questionEn` / `questionVi` must carry identical meaning.
    - `optionsEn` / `optionsVi` must list four plain-text choices (no prefixes like "A.", "B.").
    - `correctAnswer` is a 0-based index shared by both language lists.
    - `explanationEn` / `explanationVi` must justify why the correct option is correct (Vietnamese explanation is a faithful translation).
    
    RESPONSE:
    - Fill the structured output defined by the provided schema (`QuizGenerationResult`).
    - After populating the schema, add a short English confirmation such as "Quiz created successfully.".
    """,
    output_schema=QuizGenerationResult,
    output_key="quiz_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


