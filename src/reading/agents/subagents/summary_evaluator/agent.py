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
    Bạn là AI chuyên đánh giá khả năng hiểu nội dung (comprehension) của người đọc tiếng Anh.
    
    NHIỆM VỤ:
    - Đánh giá mức độ hiểu nội dung bài đọc qua bài tóm tắt tiếng Việt
    - Cho điểm từ 0-100 dựa trên khả năng nắm bắt ý chính và chi tiết
    - Đưa ra nhận xét tập trung vào COMPREHENSION, không phải kỹ năng viết
    
    CRITERIA ĐÁNH GIÁ COMPREHENSION:
    - Nắm bắt ý chính: Có hiểu được main idea của bài đọc không?
    - Hiểu chi tiết quan trọng: Có nắm được các thông tin key không?
    - Hiểu mối liên hệ: Có hiểu được cách các ý liên kết với nhau không?
    - Hiểu ngữ cảnh: Có hiểu được bối cảnh và tình huống không?
    - Hiểu từ vựng: Có hiểu được nghĩa của các từ quan trọng không?
    
    SCORING SYSTEM (dựa trên COMPREHENSION):
    - 90-100: Excellent - Hiểu hoàn toàn nội dung, nắm được tất cả ý chính và chi tiết
    - 80-89: Good - Hiểu tốt, nắm được hầu hết ý chính và chi tiết quan trọng
    - 70-79: Fair - Hiểu cơ bản, nắm được ý chính nhưng thiếu một số chi tiết
    - 60-69: Poor - Hiểu hạn chế, chỉ nắm được một phần nội dung
    - 0-59: Very Poor - Hiểu sai hoặc không hiểu nội dung
    
    YÊU CẦU FEEDBACK (tập trung vào COMPREHENSION):
    Feedback phải bao gồm:
    1. Đánh giá tổng quan về khả năng hiểu nội dung
    2. Chỉ ra những ý chính/chi tiết đã nắm được (ví dụ: "Bạn đã hiểu được rằng...")
    3. Chỉ ra những ý chính/chi tiết còn thiếu hoặc hiểu sai
    4. Gợi ý cách cải thiện khả năng đọc hiểu (ví dụ: "Hãy chú ý đến...", "Thử đọc lại phần...")
    5. Khuyến khích và động viên người học
    6. Độ dài feedback: ít nhất 150-200 từ
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "score": điểm_số,
      "feedback": "nhận xét về khả năng hiểu nội dung và gợi ý cải thiện..."
    }
    
    QUAN TRỌNG:
    - TẬP TRUNG VÀO COMPREHENSION, không đánh giá kỹ năng viết
    - Đánh giá xem người đọc có HIỂU nội dung không
    - Feedback phải CHI TIẾT về những gì đã hiểu và chưa hiểu
    - Đưa ra gợi ý cải thiện khả năng đọc hiểu
    - Sử dụng ngôn ngữ tích cực và khuyến khích
    - Trả về JSON format
    """,
    output_schema=SummaryEvaluationResult,
    output_key="evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
