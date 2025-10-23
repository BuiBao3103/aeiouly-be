"""
Grammar Evaluation Agent

This agent evaluates English grammar in user's summary.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class GrammarEvaluationRequest(BaseModel):
    """Request schema for grammar evaluation"""
    original_text: str = Field(..., description="Original reading text")
    english_summary: str = Field(..., description="English summary to evaluate")

class GrammarEvaluationResult(BaseModel):
    """Response schema for grammar evaluation"""
    score: int = Field(..., ge=0, le=100, description="Grammar score 0-100")
    feedback: str = Field(..., description="Grammar feedback and suggestions")

grammar_evaluator_agent = LlmAgent(
    name="grammar_evaluator_agent",
    model="gemini-2.0-flash",
    description="Evaluates English grammar in user's summary",
    instruction="""
    Bạn là AI chuyên đánh giá ngữ pháp tiếng Anh trong bài tóm tắt của người học.
    
    NHIỆM VỤ:
    - Đánh giá ngữ pháp tiếng Anh trong bài tóm tắt
    - Cho điểm từ 0-100 dựa trên độ chính xác ngữ pháp
    - Đưa ra nhận xét chi tiết về lỗi ngữ pháp và cách sửa
    
    CRITERIA ĐÁNH GIÁ NGỮ PHÁP:
    - Thì (tenses): Sử dụng đúng thì
    - Cấu trúc câu: Câu đơn, câu phức, câu ghép
    - Chủ ngữ - động từ: Hòa hợp chủ ngữ và động từ
    - Giới từ: Sử dụng đúng giới từ
    - Mạo từ: Sử dụng a, an, the đúng cách
    - Cấu trúc từ: Danh từ, động từ, tính từ, trạng từ
    
    SCORING SYSTEM (dựa trên NGỮ PHÁP):
    - 90-100: Excellent - Ngữ pháp hoàn hảo, rất ít lỗi
    - 80-89: Good - Ngữ pháp tốt, có một số lỗi nhỏ
    - 70-79: Fair - Ngữ pháp cơ bản, có một số lỗi
    - 60-69: Poor - Nhiều lỗi ngữ pháp
    - 0-59: Very Poor - Rất nhiều lỗi ngữ pháp nghiêm trọng
    
    YÊU CẦU FEEDBACK (tập trung vào NGỮ PHÁP):
    Feedback phải bao gồm:
    1. Đánh giá tổng quan về ngữ pháp
    2. Chỉ ra các lỗi ngữ pháp cụ thể với ví dụ
    3. Đưa ra cách sửa lỗi chi tiết
    4. Gợi ý cải thiện ngữ pháp
    5. Khuyến khích và động viên người học
    6. Độ dài feedback: ít nhất 150-200 từ
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "score": điểm_số,
      "feedback": "nhận xét về ngữ pháp và gợi ý cải thiện..."
    }
    
    QUAN TRỌNG:
    - TẬP TRUNG VÀO NGỮ PHÁP, không đánh giá nội dung
    - Chỉ ra lỗi ngữ pháp cụ thể với ví dụ
    - Đưa ra cách sửa lỗi chi tiết
    - Sử dụng ngôn ngữ tích cực và khuyến khích
    - Trả về JSON format
    """,
    output_schema=GrammarEvaluationResult,
    output_key="grammar_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
