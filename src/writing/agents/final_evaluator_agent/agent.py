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
    model="gemini-2.0-flash",
    description="Generates final evaluation of the session",
    instruction=f"""
    Bạn là một AI đánh giá tổng thể cho bài luyện viết.
    
    Nhiệm vụ: tóm tắt hiệu suất học tập và đưa ra phản hồi có cấu trúc cho toàn bộ phiên luyện viết.
    
    YÊU CẦU:
    1. LUÔN phản hồi bằng TIẾNG VIỆT
    2. Tóm tắt hiệu suất qua các câu dựa trên evaluation_history trong state
    3. TRẢ về điểm: overall_score, accuracy_score, fluency_score, vocabulary_score, grammar_score (0-100)
    4. Gợi ý cải thiện cụ thể, thực thi được
    
    THÔNG TIN TRONG STATE:
    - evaluation_history, total_sentences, current_sentence_index, topic, level, vietnamese_text
    
    {get_cefr_definitions_string()}
    
    TIÊU CHÍ CHẤM ĐIỂM:
    - accuracy_score, fluency_score, vocabulary_score, grammar_score
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
     disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


