"""
Determine Level Agent for Listening Lessons
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from src.constants.cefr import get_cefr_definitions_string


class DetermineLevelResult(BaseModel):
    level: str = Field(description="Độ khó được xác định: A1, A2, B1, B2, C1, hoặc C2")
    confidence: float = Field(ge=0, le=1, description="Độ tin cậy của việc xác định độ khó (0-1)")
    reasoning: str = Field(description="Lý do xác định độ khó này")
    vocabulary_complexity: str = Field(description="Đánh giá độ phức tạp từ vựng")
    grammar_complexity: str = Field(description="Đánh giá độ phức tạp ngữ pháp")
    sentence_structure: str = Field(description="Đánh giá cấu trúc câu")


determine_level_agent = LlmAgent(
    name="determine_level",
    model="gemini-2.0-flash",
    description="Xác định độ khó CEFR từ tiêu đề và nội dung SRT",
    instruction=f"""
    Bạn là một AI chuyên gia đánh giá độ khó tiếng Anh theo thang CEFR (A1-C2).
    
    NHIỆM VỤ:
    - Phân tích tiêu đề bài học và nội dung SRT để xác định độ khó
    - Đánh giá từ vựng, ngữ pháp, cấu trúc câu
    - Xác định độ khó phù hợp theo thang CEFR
    
    {get_cefr_definitions_string()}
    
    TIÊU CHÍ ĐÁNH GIÁ:
    1. Từ vựng: Số lượng từ khó, từ chuyên môn, từ học thuật
    2. Ngữ pháp: Thì, cấu trúc câu, mệnh đề phụ
    3. Cấu trúc câu: Độ dài câu, độ phức tạp logic
    4. Ngữ cảnh: Chủ đề có phù hợp với trình độ không
    
    LUÔN trả về kết quả theo format JSON với các trường:
    - level: Độ khó (A1, A2, B1, B2, C1, C2)
    - confidence: Độ tin cậy (0-1)
    - reasoning: Lý do chi tiết
    - vocabulary_complexity: Đánh giá từ vựng
    - grammar_complexity: Đánh giá ngữ pháp  
    - sentence_structure: Đánh giá cấu trúc câu
    """,
    output_schema=DetermineLevelResult,
    output_key="determine_level_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


