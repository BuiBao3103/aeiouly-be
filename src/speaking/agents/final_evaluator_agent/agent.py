"""
Final Evaluator Agent for Speaking Practice
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List
from src.constants.cefr import get_cefr_definitions_string


class FinalEvaluationResult(BaseModel):
    overall_score: float = Field(ge=0, le=100, description="Tổng điểm tổng thể từ 0-100")
    pronunciation_score: float = Field(ge=0, le=100, description="Điểm phát âm từ 0-100")
    fluency_score: float = Field(ge=0, le=100, description="Điểm trôi chảy và tự nhiên từ 0-100")
    vocabulary_score: float = Field(ge=0, le=100, description="Điểm từ vựng từ 0-100")
    grammar_score: float = Field(ge=0, le=100, description="Điểm ngữ pháp từ 0-100")
    interaction_score: float = Field(ge=0, le=100, description="Điểm tương tác và phản hồi từ 0-100")
    feedback: str = Field(description="Nhận xét tổng thể bằng tiếng Việt")
    suggestions: List[str] = Field(description="Danh sách gợi ý cải thiện")


final_evaluator_agent = LlmAgent(
    name="final_evaluator",
    model="gemini-2.5-flash",
    description="Đánh giá tổng kết phiên luyện nói.",
    instruction=f"""
    Đánh giá tổng thể phiên luyện nói. Phản hồi bằng TIẾNG VIỆT.
    
    CONTEXT: chat_history={{chat_history?}}, Learner={{my_character}}, AI={{ai_character}}, Scenario={{scenario}}, Level={{level}}
    
    YÊU CẦU:
    - Điểm 0-100: overall_score, pronunciation_score, fluency_score, vocabulary_score, grammar_score, interaction_score
    - feedback: Nhận xét tổng thể (tiếng Việt)
    - suggestions: Danh sách gợi ý cải thiện
    
    TIÊU CHÍ:
    - pronunciation_score: Phát âm (suy luận từ cách viết), tập trung vào từ vựng/ngữ pháp
    - fluency_score: Độ trôi chảy, tự nhiên, độ dài câu
    - vocabulary_score: Đa dạng, phù hợp với level
    - grammar_score: Chính xác ngữ pháp, cấu trúc câu
    - interaction_score: Tương tác, phản hồi phù hợp ngữ cảnh
    - overall_score: Trung bình các tiêu chí
    
    Đánh giá dựa trên tin nhắn user trong chat_history. Feedback tích cực, gợi ý cụ thể.
    
    {get_cefr_definitions_string()}
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

