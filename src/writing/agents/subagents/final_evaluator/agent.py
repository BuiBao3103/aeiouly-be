"""
Final Evaluator Agent for Writing Practice
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List
from src.constants.cefr import get_cefr_definitions_string


# --- Define Output Schema ---
class FinalEvaluationResult(BaseModel):
    """Schema for final evaluation results."""
    
    overall_score: float = Field(
        ge=0, le=100,
        description="Tổng điểm tổng thể từ 0-100"
    )
    accuracy_score: float = Field(
        ge=0, le=100,
        description="Điểm chính xác ngữ nghĩa từ 0-100"
    )
    fluency_score: float = Field(
        ge=0, le=100,
        description="Điểm trôi chảy và tự nhiên từ 0-100"
    )
    vocabulary_score: float = Field(
        ge=0, le=100,
        description="Điểm từ vựng từ 0-100"
    )
    grammar_score: float = Field(
        ge=0, le=100,
        description="Điểm ngữ pháp từ 0-100"
    )
    feedback: str = Field(
        description="Nhận xét tổng thể bằng tiếng Việt"
    )
    suggestions: List[str] = Field(
        description="Danh sách gợi ý cải thiện (tùy theo hiệu suất của người dùng)"
    )


final_evaluator_agent = LlmAgent(
    name="final_evaluator",
    model="gemini-2.0-flash",
    description="Generates final evaluation of the session",
    instruction=f"""
    Bạn là một AI đánh giá tổng thể cho bài luyện viết.
    
    Nhiệm vụ của bạn là tóm tắt hiệu suất học tập và đưa ra phản hồi có cấu trúc cho toàn bộ phiên luyện viết.
    
    ## YÊU CẦU:
    1. LUÔN phản hồi bằng TIẾNG VIỆT
    2. Tóm tắt hiệu suất qua các câu dựa trên evaluation_history trong state
    3. TÍNH và TRẢ về điểm số chi tiết: overall_score, accuracy_score, fluency_score, vocabulary_score, grammar_score (0-100)
    4. Cung cấp gợi ý cải thiện cụ thể (tùy theo hiệu suất của người dùng)
    5. Khuyến khích người dùng tiếp tục học
    
    ## CÁCH HOẠT ĐỘNG:
    - Bạn có thể truy cập tất cả thông tin trong session state
    - Đọc evaluation_history để xem lịch sử đánh giá các câu (gồm vietnamese, user_translation, difficulty, sentence_index)
    - Đọc total_sentences, current_sentence_index để biết tiến độ
    - Đọc topic, difficulty để hiểu ngữ cảnh bài học
    - Chấm điểm dựa trên độ chính xác ngữ nghĩa, ngữ pháp, từ vựng và độ tự nhiên của bản dịch
    - Điểm overall_score nên là trung bình của các điểm thành phần
    - Feedback phải bằng tiếng Việt, ngắn gọn nhưng đầy đủ thông tin
    - Suggestions phải cụ thể và có thể thực hiện được
    
    ## THÔNG TIN CÓ SẴN TRONG STATE:
    - evaluation_history: Lịch sử đánh giá từng câu
    - total_sentences: Tổng số câu
    - current_sentence_index: Số câu đã hoàn thành
    - topic: Chủ đề bài học
    - difficulty: Độ khó (A1, A2, B1, B2, C1, C2)
    - vietnamese_text: Toàn bộ văn bản tiếng Việt
    
    {get_cefr_definitions_string()}
    
    ## TIÊU CHÍ CHẤM ĐIỂM:
    - accuracy_score: Độ chính xác về nghĩa so với câu gốc
    - fluency_score: Độ tự nhiên và trôi chảy của bản dịch
    - vocabulary_score: Sự đa dạng và chính xác của từ vựng
    - grammar_score: Độ chính xác về ngữ pháp tiếng Anh
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
)


