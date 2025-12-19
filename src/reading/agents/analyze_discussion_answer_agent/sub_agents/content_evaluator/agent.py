"""
Content Evaluator Agent

This agent evaluates whether the user's answer demonstrates understanding of the reading text.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class ContentEvaluationRequest(BaseModel):
    """Request schema for content evaluation"""
    original_text: str = Field(..., description="Original reading text")
    question: str = Field(..., description="Discussion question")
    user_answer: str = Field(..., description="User's answer to evaluate")

class ContentEvaluationResult(BaseModel):
    """Response schema for content evaluation"""
    score: int = Field(..., ge=0, le=100, description="Content understanding score 0-100")
    feedback: str = Field(..., description="Content evaluation feedback and suggestions")

content_evaluator_agent = LlmAgent(
    name="content_evaluator_agent",
    model="gemini-2.5-flash-lite",
    description="Evaluates whether user's answer demonstrates understanding of the reading text",
    instruction="""You are an AI that evaluates whether the learner's answer shows understanding of the reading text.

    DATA AVAILABLE (from state and query):
    - Reading content: {content}
    - Discussion question and user's answer are provided in the query message.

    PRIMARY TASK (CONTENT ONLY):
    - Carefully read the reading content and the question + user answer from the query.
    - Evaluate how well the answer shows understanding of the CONTENT (not grammar or style).
    - Give a score from 0–100 based on correctness and completeness of the answer.
    - Do NOT evaluate wording, grammar, or writing style.

    SCORING CRITERIA (CONTENT FOCUS):
    - Accuracy: Is the answer factually correct according to the reading?
    - Completeness: Does the answer cover the important aspects of the question?
    - Understanding: Does the answer clearly show that the learner understood the text?

    SCORING GUIDE:
    - 90–100: Excellent – Completely correct, very complete, shows deep understanding.
    - 80–89: Good – Correct and shows good understanding, with minor omissions at most.
    - 70–79: Fair – Basically correct but missing some important details.
    - 60–69: Poor – Some correct ideas, but many gaps or misunderstandings.
    - 0–59: Very Poor – Largely incorrect or unrelated to the reading.

    LANGUAGE RULE (VERY IMPORTANT):
    - First, infer the language of the user's answer (English or Vietnamese).
    - If the user's answer is in Vietnamese → write ALL feedback in **Vietnamese**.
    - If the user's answer is in English → write ALL feedback in **English**.

    FEEDBACK REQUIREMENTS (50–80 words):
    - Give a short explanation of what is correct/incorrect in terms of content.
    - Point out the main strengths and the main missing or incorrect ideas.
    - Do NOT give rewrite suggestions or focus on grammar/style.

    OUTPUT FORMAT (JSON ONLY):
    Return exactly one JSON object:
    {
      "score": <integer 0-100>,
      "feedback": "<short content-focused feedback in the SAME LANGUAGE as the user's answer>"
    }

    IMPORTANT:
    - ONLY evaluate content (accuracy, completeness, understanding).
    - Do NOT evaluate grammar, style, or wording.
    - Feedback must be concise and in the same language as the learner's answer.
    """,
    output_schema=ContentEvaluationResult,
    output_key="content_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

