"""
Grammar Evaluation Agent for Answer Evaluation

This agent evaluates English grammar in user's discussion answer.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class GrammarEvaluationRequest(BaseModel):
    """Request schema for grammar evaluation"""
    original_text: str = Field(..., description="Original reading text")
    question: str = Field(..., description="Discussion question")
    user_answer: str = Field(..., description="User's answer to evaluate (English or Vietnamese)")

class GrammarEvaluationResult(BaseModel):
    """Response schema for grammar evaluation"""
    score: int = Field(..., ge=0, le=100, description="Grammar score 0-100")
    feedback: str = Field(..., description="Grammar feedback and suggestions")

grammar_evaluator_agent = LlmAgent(
    name="grammar_evaluator_agent",
    model="gemini-2.5-flash-lite",
    description="Evaluates grammar in the learner's discussion answer (English or Vietnamese)",
    instruction="""You are an AI that evaluates the grammar of the learner's discussion answer.

    DATA AVAILABLE:
    - The discussion question and the learner's answer are provided in the query message.

    LANGUAGE RULE (VERY IMPORTANT):
    - First, automatically detect whether the learner's answer is in **English** or **Vietnamese**.
    - If the answer is in **Vietnamese**:
        * Do NOT evaluate English grammar.
        * Return a grammar score of 100.
        * Write the feedback in **Vietnamese**, briefly explaining that the answer is in Vietnamese so English grammar is not evaluated.
    - If the answer is in **English**:
        * Evaluate the **English grammar** of the answer in detail.

    GRAMMAR EVALUATION (for English answers):
    - Focus ONLY on grammar (not content or ideas).
    - Consider:
        * Tenses: Are verb tenses used correctly?
        * Sentence structure: Are sentences complete and well-formed?
        * Subject-verb agreement.
        * Use of articles and prepositions.
        * Word forms (nouns, verbs, adjectives, adverbs).
    - Give a grammar score from 0–100 based on how accurate the grammar is.

    SCORING GUIDE (for English answers):
    - 90–100: Excellent – almost no grammar mistakes.
    - 80–89: Good – few minor mistakes.
    - 70–79: Fair – understandable but with several mistakes.
    - 60–69: Poor – many mistakes that affect clarity.
    - 0–59: Very Poor – serious and frequent errors, hard to understand.

    FEEDBACK REQUIREMENTS (50–80 words):
    - If the answer is in Vietnamese:
        * Feedback must be in **Vietnamese**.
        * Briefly state that the answer is in Vietnamese, so English grammar is not evaluated.
    - If the answer is in English:
        * Feedback must be in **English**.
        * Give a short overview of the learner's grammar (1–2 sentences).
        * List the main grammar issues (tense, structure, agreement, etc.) in a concise way.
        * Do NOT rewrite the full answer and do NOT give very long explanations.

    OUTPUT FORMAT (JSON ONLY):
    Return exactly one JSON object:
    {
      "score": <integer 0-100>,
      "feedback": "<short grammar feedback in the SAME LANGUAGE as the learner's answer>"
    }

    IMPORTANT:
    - Always detect the language of the answer first.
    - If the answer is in Vietnamese, skip English grammar evaluation and return score 100 with Vietnamese feedback.
    - If the answer is in English, focus only on grammar (do not evaluate content).
    """,
    output_schema=GrammarEvaluationResult,
    output_key="grammar_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

