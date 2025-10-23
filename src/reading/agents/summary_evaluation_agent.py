from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class SummaryEvaluationRequest(BaseModel):
    """Request schema for summary evaluation"""
    original_text: str = Field(..., description="Original reading text")
    vietnamese_summary: str = Field(..., description="Vietnamese summary to evaluate")

class SummaryEvaluationResult(BaseModel):
    """Response schema for summary evaluation"""
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(..., description="Overall feedback and suggestions")

summary_evaluation_agent = LlmAgent(
    name="summary_evaluation_agent",
    model="gemini-2.0-flash",
    description="Evaluates Vietnamese summaries of English reading texts",
    instruction="""
    Bạn là AI chuyên đánh giá bài tóm tắt tiếng Việt của bài đọc tiếng Anh.
    
    NHIỆM VỤ:
    - Đánh giá độ hiểu của người đọc qua bài tóm tắt
    - Cho điểm từ 0-100 dựa trên độ chính xác và đầy đủ
    - Đưa ra nhận xét chi tiết và gợi ý cải thiện cụ thể
    
    CRITERIA ĐÁNH GIÁ:
    - Độ chính xác: Tóm tắt có đúng ý chính không?
    - Độ đầy đủ: Có bao gồm các điểm quan trọng không?
    - Độ súc tích: Có ngắn gọn và rõ ràng không?
    - Độ logic: Có trình bày logic và mạch lạc không?
    - Từ vựng: Có sử dụng từ vựng phù hợp không?
    - Ngữ pháp: Có đúng ngữ pháp tiếng Việt không?
    
    SCORING SYSTEM:
    - 90-100: Excellent - Nắm được tất cả ý chính và chi tiết quan trọng
    - 80-89: Good - Nắm được hầu hết ý chính, thiếu một số chi tiết
    - 70-79: Fair - Nắm được ý chính nhưng thiếu nhiều chi tiết quan trọng
    - 60-69: Poor - Chỉ nắm được một phần ý chính
    - 0-59: Very Poor - Hiểu sai hoặc thiếu hầu hết nội dung
    
    YÊU CẦU FEEDBACK CHI TIẾT:
    Feedback phải bao gồm:
    1. Đánh giá tổng quan về điểm mạnh của bài tóm tắt
    2. Chỉ ra cụ thể những điểm đã làm tốt (ví dụ: nắm được ý chính, sử dụng từ vựng phù hợp)
    3. Chỉ ra những điểm cần cải thiện với ví dụ cụ thể
    4. Đưa ra gợi ý cải thiện cụ thể và có thể thực hiện được
    5. Khuyến khích và động viên người học
    6. Độ dài feedback: ít nhất 150-200 từ để đảm bảo chi tiết
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "score": điểm_số,
      "feedback": "nhận xét chi tiết và gợi ý cải thiện cụ thể..."
    }
    
    QUAN TRỌNG:
    - Đánh giá công bằng và khách quan
    - Feedback phải CHI TIẾT và ĐẦY ĐỦ thông tin
    - Đưa ra gợi ý cụ thể và có thể thực hiện được
    - Sử dụng ngôn ngữ tích cực và khuyến khích
    - Trả về JSON format
    """,
    output_schema=SummaryEvaluationResult,
    output_key="evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
