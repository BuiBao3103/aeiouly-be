"""
Final Evaluator Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List
from src.constants.cefr import get_cefr_definitions_string


class FinalEvaluationResult(BaseModel):
    overall_score: float = Field(ge=0, le=100, description="Tổng điểm tổng thể từ 0-100")
    accuracy_score: float = Field(ge=0, le=100, description="Điểm chính xác ngữ nghĩa từ 0-100")
    fluency_score: float = Field(ge=0, le=100, description="Điểm trôi chảy và tự nhiên từ 0-100")
    vocabulary_score: float = Field(ge=0, le=100, description="Điểm từ vựng từ 0-100")
    grammar_score: float = Field(ge=0, le=100, description="Điểm ngữ pháp từ 0-100")
    feedback: str = Field(description="Nhận xét tổng thể bằng tiếng Việt")
    suggestions: List[str] = Field(description="Danh sách gợi ý cải thiện")


final_evaluator_agent = LlmAgent(
    name="final_evaluator",
    model="gemini-2.5-flash",
    description="Tạo đánh giá tổng kết cho phiên luyện viết dựa trên evaluation_history",
    instruction=f"""
    You are the AI Final Evaluator for a writing practice session.

    IMPORTANT: All of your natural-language output MUST be in VIETNAMESE (tiếng Việt tự nhiên, dễ hiểu cho học viên).
    
    Evaluation history: {{evaluation_history}}
    - Topic: {{topic}}
    - Level: {{level}}
    - Full text: {{vietnamese_sentences["full_text"]}}
    
    GOALS:
    - Accurately summarize the learner's progress across the whole session using evaluation_history.
    - Assign 0–100 scores for accuracy, fluency, vocabulary, and grammar that closely reflect the REAL performance.
      If the learner performs very well on one aspect, the score for that aspect MUST be high.
      Only reduce scores when there are concrete errors recorded in evaluation_history.
    - overall_score should be a justified holistic score, not lower than the sub-scores without a clear reason.
    - Provide overall feedback plus at least 2 specific, actionable suggestions.
    
    RULES:
    1. ALWAYS respond in NATURAL VIETNAMESE
    2. Base everything strictly on evaluation_history. If there are no evaluated sentences or errors yet,
       explain that there is not enough data to fairly evaluate.
    3. If most sentences are fully correct, give high scores (>= 90) for the relevant criteria.
    4. If there are recurring issues (e.g., tense, vocabulary choice), reflect them in the scores
       and call them out clearly in the feedback.
    5. Cross-check topic, level, and CEFR descriptions to judge how appropriate the writing is for that level.
    
    STATE INFORMATION:
    - evaluation_history, total_sentences, current_sentence_index, topic, level, sentences, full_text
    
    {get_cefr_definitions_string()}
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
     disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


