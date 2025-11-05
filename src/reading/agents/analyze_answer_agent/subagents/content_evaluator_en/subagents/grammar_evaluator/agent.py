"""
Grammar Evaluation Agent for Answer Evaluation

This agent evaluates English grammar in user's discussion answer.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class GrammarEvaluationRequest(BaseModel):
    """Request schema for grammar evaluation"""
    original_text: str = Field(..., description="Original reading text")
    question: str = Field(..., description="Discussion question")
    english_answer: str = Field(..., description="English answer to evaluate")

class GrammarEvaluationResult(BaseModel):
    """Response schema for grammar evaluation"""
    score: int = Field(..., ge=0, le=100, description="Grammar score 0-100")
    feedback: str = Field(..., description="Grammar feedback and suggestions")

grammar_evaluator_agent = LlmAgent(
    name="grammar_evaluator_agent",
    model="gemini-2.0-flash",
    description="Evaluates English grammar in user's discussion answer",
    instruction="""
    Bạn là AI chuyên đánh giá ngữ pháp tiếng Anh trong câu trả lời thảo luận của người học.
    
    NHIỆM VỤ:
    - Đánh giá ngữ pháp tiếng Anh trong câu trả lời
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
    
    YÊU CẦU FEEDBACK (NGẮN GỌN, 50-80 từ):
    Feedback phải ngắn gọn, tập trung vào:
    - Đánh giá tổng quan về ngữ pháp (1-2 câu)
    - Liệt kê các lỗi ngữ pháp chính (ngắn gọn, không cần ví dụ chi tiết)
    - KHÔNG cần giải thích dài dòng về cách sửa từng lỗi
    - KHÔNG cần đưa ra câu sửa lại hoàn chỉnh
    
    OUTPUT FORMAT:
    Trả về JSON:
    {
      "score": điểm_số,
      "feedback": "nhận xét ngắn gọn về ngữ pháp (50-80 từ)..."
    }
    
    QUAN TRỌNG:
    - TẬP TRUNG VÀO NGỮ PHÁP, không đánh giá nội dung
    - Feedback NGẮN GỌN (50-80 từ), chỉ liệt kê lỗi chính
    - KHÔNG cần giải thích chi tiết cách sửa từng lỗi
    - Trả về JSON format
    """,
    output_schema=GrammarEvaluationResult,
    output_key="grammar_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

