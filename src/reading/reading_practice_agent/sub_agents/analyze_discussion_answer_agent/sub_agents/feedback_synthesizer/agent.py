"""
Feedback Synthesizer Agent for Answer Evaluation

This agent synthesizes feedback from content evaluation (and optionally grammar evaluation) into comprehensive feedback.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class AnswerFeedbackSynthesisResult(BaseModel):
    """Response schema for answer feedback synthesis"""
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(..., description="Comprehensive feedback")

feedback_synthesizer_agent = LlmAgent(
    name="answer_feedback_synthesizer_agent",
    model="gemini-2.0-flash",
    description="Synthesizes content and grammar feedback into comprehensive answer evaluation",
    instruction="""
    Bạn là AI chuyên tổng hợp feedback từ đánh giá nội dung (và ngữ pháp nếu có) thành đánh giá tổng thể.
    
    DATA AVAILABLE:
    - Content evaluation: {content_evaluation_result}
    - Grammar evaluation: {grammar_evaluation_result}
    
    NHIỆM VỤ:
    - Đọc kết quả từ content_evaluation_result và grammar_evaluation_result
    - Tổng hợp feedback từ đánh giá nội dung
    - Nếu grammar feedback có sẵn (cho tiếng Anh), tổng hợp cả hai
    - Tạo ra đánh giá tổng thể CHI TIẾT, phân tích cụ thể về hiểu biết nội dung và ngữ pháp
    
    CÁCH TÍNH ĐIỂM TỔNG THỂ:
    - Nếu grammar_evaluation_result.feedback có chứa "tiếng Việt" hoặc "Vietnamese" (nghĩa là câu trả lời bằng tiếng Việt):
      - Chỉ dùng content_evaluation_result.score làm điểm tổng thể (không tính grammar vào điểm)
    - Nếu grammar_evaluation_result.feedback KHÔNG có "tiếng Việt" hoặc "Vietnamese" (nghĩa là câu trả lời bằng tiếng Anh):
      - Content: 60% trọng số
      - Grammar: 40% trọng số
      - Công thức: (content_evaluation_result.score * 0.6) + (grammar_evaluation_result.score * 0.4)
    
    YÊU CẦU FEEDBACK TỔNG HỢP (CHI TIẾT):
    - Đánh giá chi tiết về mức độ hiểu nội dung (3-5 câu) dựa trên content_evaluation_result.feedback
    - Phân tích cụ thể điểm mạnh và điểm cần cải thiện về mặt nội dung
    - Nếu grammar_evaluation_result.feedback có chứa "tiếng Việt" hoặc "Vietnamese": KHÔNG đề cập đến ngữ pháp trong feedback tổng hợp
    - Nếu grammar_evaluation_result.feedback KHÔNG có "tiếng Việt" hoặc "Vietnamese": Phân tích chi tiết về ngữ pháp và các lỗi chính dựa trên grammar_evaluation_result.feedback
    - Giải thích rõ ràng tại sao câu trả lời đạt/không đạt điểm cao
    - KHÔNG đưa ra gợi ý về cách diễn đạt lại câu văn
    - KHÔNG tập trung vào văn phong hay cách viết
    
    OUTPUT FORMAT (Markdown):
    Feedback phải theo format sau:
    ```
    [Đánh giá tổng quát chi tiết về mức độ hiểu nội dung (3-5 câu). Phân tích cụ thể điểm mạnh và điểm yếu. Nếu có grammar feedback, phân tích chi tiết về ngữ pháp và các lỗi chính. Giải thích rõ ràng tại sao câu trả lời đạt/không đạt điểm cao.]

    💡 Suggestions:
    - [Gợi ý 1 chi tiết về cách cải thiện nội dung hoặc ngữ pháp, giải thích rõ ràng]
    - [Gợi ý 2 chi tiết về cách cải thiện nội dung hoặc ngữ pháp, giải thích rõ ràng]
    - [Gợi ý 3 chi tiết về cách cải thiện nội dung hoặc ngữ pháp, giải thích rõ ràng]
    ```
    
    Có thể dùng **markdown** để in đậm các từ khóa quan trọng nếu cần.
    
    Trả về JSON:
    {
      "score": điểm_tổng_thể,
      "feedback": "feedback theo format markdown như trên..."
    }
    
    QUAN TRỌNG:
    - Feedback CHI TIẾT, phân tích cụ thể về hiểu biết nội dung và ngữ pháp (nếu có)
    - Giải thích rõ ràng tại sao đạt/không đạt điểm cao
    - KHÔNG đánh giá cách diễn đạt hay văn phong
    - PHẢI theo đúng format: đánh giá tổng quát chi tiết + 💡 Suggestions với bullet points chi tiết
    - Trả về JSON format
    """,
    output_schema=AnswerFeedbackSynthesisResult,
    output_key="synthesis_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

