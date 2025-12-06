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
    model="gemini-2.5-flash-lite",
    description="Generates quizzes from English reading texts to test comprehension",
    instruction="""
    You create bilingual multiple-choice quizzes from the reading text stored in state.

    DATA:
    - Reading content: {content}
    - Number of questions: from the request.

    TASK:
    - Write questions that test comprehension (not memorization).
    - Every question, option, and explanation must have English and Vietnamese versions.
    - Each question must have exactly 4 options, 1 correct answer, and clear explanations.

    RULES:
    - `questionEn` and `questionVi` must have the same meaning.
    - `optionsEn` / `optionsVi`: 4 plain-text options (no "A.", "B." prefixes).
    - `correctAnswer`: 0-based index, shared for both language lists.
    - `explanationEn` / `explanationVi`: explain why the correct option is right; Vietnamese is a faithful translation.

    OUTPUT:
    - Return ONLY one JSON object that matches `QuizGenerationResult` schema.
    - No extra commentary or markdown, only the JSON payload.
    """,
    output_schema=QuizGenerationResult,
    output_key="quiz_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


