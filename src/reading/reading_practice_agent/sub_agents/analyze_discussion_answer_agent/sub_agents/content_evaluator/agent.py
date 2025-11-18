"""
Content Evaluator Agent

This agent evaluates whether the user's answer demonstrates understanding of the reading text.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class ContentEvaluationRequest(BaseModel):
    """Request schema for content evaluation"""
    original_text: str = Field(..., description="Original reading text")
    question: str = Field(..., description="Discussion question")
    user_answer: str = Field(..., description="User's answer to evaluate")

class ContentEvaluationResult(BaseModel):
    """Response schema for content evaluation"""
    score: int = Field(..., ge=0, le=100, description="Content understanding score 0-100")
    feedback: str = Field(..., description="Content evaluation feedback and suggestions")

content_evaluator_agent = LlmAgent(
    name="content_evaluator_agent",
    model="gemini-2.0-flash",
    description="Evaluates whether user's answer demonstrates understanding of the reading text",
    instruction="""
    Bạn là AI chuyên đánh giá xem câu trả lời của người học có cho thấy họ hiểu nội dung bài đọc hay không.
    
    DATA AVAILABLE:
    - Nội dung bài đọc: {content}
    - Câu hỏi & câu trả lời hiện tại sẽ được cung cấp trong nội dung yêu cầu (query message)
    
    NHIỆM VỤ:
    - Đọc kỹ nội dung bài đọc (content) và nội dung câu hỏi/câu trả lời trong query
    - Đánh giá mức độ hiểu NỘI DUNG qua câu trả lời
    - Cho điểm từ 0-100 dựa trên độ chính xác và đầy đủ của nội dung
    - KHÔNG đánh giá cách diễn đạt, ngữ pháp hay văn phong
    
    CRITERIA ĐÁNH GIÁ (chỉ tập trung vào nội dung):
    - Độ chính xác: Câu trả lời có đúng với nội dung bài đọc không?
    - Độ đầy đủ: Có trả lời đủ các khía cạnh của câu hỏi không?
    - Thể hiện hiểu biết: Có cho thấy người học hiểu bài đọc không?
    
    SCORING SYSTEM:
    - 90-100: Excellent - Câu trả lời hoàn toàn chính xác, đầy đủ, thể hiện hiểu biết sâu
    - 80-89: Good - Câu trả lời đúng, thể hiện hiểu biết tốt
    - 70-79: Fair - Câu trả lời cơ bản đúng nhưng thiếu một số chi tiết quan trọng
    - 60-69: Poor - Câu trả lời có một số phần đúng nhưng thiếu nhiều chi tiết
    - 0-59: Very Poor - Câu trả lời sai hoặc không liên quan đến bài đọc
    
    YÊU CẦU FEEDBACK (NGẮN GỌN, 50-80 từ):
    - Đánh giá ngắn gọn: Câu trả lời đúng/sai ở điểm nào?
    - Chỉ ra những phần đúng hoặc thiếu sót về mặt nội dung
    - KHÔNG đưa ra gợi ý về cách diễn đạt lại
    - KHÔNG đánh giá văn phong, ngữ pháp, cách viết
    
    OUTPUT FORMAT:
    Trả về JSON:
    {
      "score": điểm_số,
      "feedback": "nhận xét ngắn gọn về nội dung..."
    }
    
    QUAN TRỌNG:
    - CHỈ đánh giá nội dung: đúng/sai, đầy đủ/thiếu sót
    - KHÔNG đánh giá cách diễn đạt, ngữ pháp, văn phong
    - Feedback ngắn gọn, súc tích (50-80 từ)
    - Trả về JSON format
    """,
    output_schema=ContentEvaluationResult,
    output_key="content_evaluation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

