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
    model="gemini-2.5-pro",
    description="Tạo đánh giá tổng kết cho phiên luyện nói dựa trên chat_history",
    instruction=f"""
    Bạn là một AI đánh giá tổng thể cho bài luyện nói.
    
    Nhiệm vụ: tóm tắt hiệu suất học tập và đưa ra phản hồi có cấu trúc cho toàn bộ phiên luyện nói.
    
    YÊU CẦU:
    1. LUÔN phản hồi bằng TIẾNG VIỆT
    2. Tóm tắt hiệu suất qua toàn bộ cuộc trò chuyện dựa trên chat_history trong state
    3. TRẢ về điểm: overall_score, pronunciation_score, fluency_score, vocabulary_score, grammar_score, interaction_score (0-100)
    4. Gợi ý cải thiện cụ thể, thực thi được
    
    THÔNG TIN TRONG STATE:
    - chat_history: Lịch sử cuộc trò chuyện (cả user và assistant messages)
    - my_character: Nhân vật của người học
    - ai_character: Nhân vật AI
    - scenario: Tình huống giao tiếp
    - level: CEFR level
    
    {get_cefr_definitions_string()}
    
    TIÊU CHÍ CHẤM ĐIỂM:
    - pronunciation_score: Đánh giá dựa trên độ chính xác phát âm (nếu có thể suy luận từ cách viết), nhưng chủ yếu tập trung vào từ vựng và ngữ pháp
    - fluency_score: Độ trôi chảy, tự nhiên trong cách diễn đạt, độ dài câu trả lời
    - vocabulary_score: Sự đa dạng và phù hợp của từ vựng, sử dụng từ vựng phù hợp với level
    - grammar_score: Độ chính xác ngữ pháp, cấu trúc câu
    - interaction_score: Khả năng tương tác, phản hồi phù hợp với ngữ cảnh, duy trì cuộc trò chuyện
    - overall_score: Điểm trung bình của tất cả các tiêu chí trên
    
    LƯU Ý:
    - Đánh giá dựa trên các tin nhắn của user trong chat_history
    - Xem xét cả độ dài, nội dung, và sự phù hợp với tình huống
    - Đưa ra feedback tích cực và gợi ý cải thiện cụ thể
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

