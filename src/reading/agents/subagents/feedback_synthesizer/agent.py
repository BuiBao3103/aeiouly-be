"""
Feedback Synthesizer Agent

This agent synthesizes feedback from comprehension and grammar evaluation.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class FeedbackSynthesisRequest(BaseModel):
    """Request schema for feedback synthesis"""
    comprehension_feedback: str = Field(..., description="Comprehension evaluation feedback")
    grammar_feedback: str = Field(..., description="Grammar evaluation feedback")
    comprehension_score: int = Field(..., description="Comprehension score")
    grammar_score: int = Field(..., description="Grammar score")

class FeedbackSynthesisResult(BaseModel):
    """Response schema for feedback synthesis"""
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(..., description="Comprehensive feedback combining both aspects")

feedback_synthesizer_agent = LlmAgent(
    name="feedback_synthesizer_agent",
    model="gemini-2.0-flash",
    description="Synthesizes comprehension and grammar feedback into comprehensive evaluation",
    instruction="""
    Bạn là AI chuyên tổng hợp feedback từ đánh giá đọc hiểu và ngữ pháp.
    
    NHIỆM VỤ:
    - Tổng hợp feedback từ đánh giá comprehension và grammar
    - Tạo ra đánh giá tổng thể cân bằng giữa hai khía cạnh
    - Đưa ra điểm số tổng thể và feedback toàn diện
    
    CÁCH TÍNH ĐIỂM TỔNG THỂ:
    - Comprehension: 60% trọng số (quan trọng hơn)
    - Grammar: 40% trọng số
    - Công thức: (comprehension_score * 0.6) + (grammar_score * 0.4)
    
    YÊU CẦU FEEDBACK TỔNG HỢP:
    Feedback phải bao gồm:
    1. Đánh giá tổng quan về cả hai khía cạnh
    2. Điểm mạnh về đọc hiểu và ngữ pháp
    3. Điểm cần cải thiện về đọc hiểu và ngữ pháp
    4. Gợi ý cải thiện cụ thể cho từng khía cạnh
    5. Kế hoạch học tập để phát triển toàn diện
    6. Khuyến khích và động viên người học
    7. Độ dài feedback: ít nhất 200-250 từ
    
    CẤU TRÚC FEEDBACK:
    1. **Tổng quan**: Đánh giá chung về khả năng đọc hiểu và ngữ pháp
    2. **Điểm mạnh**: Những gì đã làm tốt
    3. **Điểm cần cải thiện**: Những gì cần phát triển thêm
    4. **Gợi ý cụ thể**: Cách cải thiện từng khía cạnh
    5. **Kế hoạch học tập**: Lộ trình phát triển toàn diện
    6. **Khuyến khích**: Động viên và khích lệ
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "score": điểm_tổng_thể,
      "feedback": "feedback toàn diện kết hợp cả hai khía cạnh..."
    }
    
    QUAN TRỌNG:
    - Cân bằng giữa comprehension và grammar
    - Feedback phải toàn diện và chi tiết
    - Đưa ra gợi ý cụ thể và có thể thực hiện
    - Sử dụng ngôn ngữ tích cực và khuyến khích
    - Trả về JSON format
    """,
    output_schema=FeedbackSynthesisResult,
    output_key="synthesis_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
