from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from src.constants.cefr import CEFRLevel, get_cefr_definitions_string
from src.reading.models import ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel


class TextAnalysisResult(BaseModel):
    """Response schema for text analysis"""
    level: ReadingLevel = Field(..., description="Detected reading level")
    genre: ReadingGenre = Field(..., description="Detected genre")
    topic: str = Field(..., description="Detected topic")

def after_text_analysis_callback(callback_context: CallbackContext) -> Optional[None]:
    """Store analysis outputs into state for downstream use."""
    state = callback_context.state or {}
    result = state.get("analysis_result", {})
    if isinstance(result, dict):
        if result.get("level"):
            state["level"] = result["level"]
        if result.get("genre"):
            state["genre"] = result["genre"]
        if result.get("topic"):
            state["topic"] = result["topic"]
    return None


text_analysis_agent = LlmAgent(
    name="text_analysis_agent",
    model="gemini-2.0-flash",
    description="Analyzes English reading texts to determine level, genre, and topic",
    instruction=f"""
    Bạn là AI chuyên phân tích bài đọc tiếng Anh để xác định level CEFR, genre và topic.
    
    DỮ LIỆU ĐẦU VÀO (TỪ STATE):
    - content: {{content}}
    
    NHIỆM VỤ:
    - Phân tích độ khó của bài đọc và xác định level CEFR (A1-C2)
    - Xác định genre của bài đọc
    - Xác định topic/chủ đề chính
    
    {get_cefr_definitions_string()}
    
    GENRE DETECTION (PHẢI XÁC ĐỊNH CHÍNH XÁC):
    Phân tích kỹ cấu trúc, phong cách và mục đích của văn bản để xác định genre một cách chính xác:
    
    - Bài báo: Có tiêu đề báo chí, cấu trúc tin tức (5W1H), phong cách khách quan, báo cáo sự kiện/thời sự
    - Email/Thư từ: Có phần chào hỏi/kết thúc, địa chỉ người nhận, mục đích giao tiếp cá nhân/công việc
    - Truyện ngắn: Có cốt truyện, nhân vật, bối cảnh, diễn biến và kết thúc rõ ràng
    - Hội thoại: Chủ yếu là đối thoại trực tiếp giữa các nhân vật, có dấu ngoặc kép hoặc dấu gạch ngang
    - Bài luận: Có luận điểm, lập luận, ví dụ, kết luận; mang tính phân tích/argumentative
    - Đánh giá sản phẩm: Nhận xét về sản phẩm/dịch vụ, liệt kê ưu/nhược điểm, đánh giá tổng thể
    - Bài mạng xã hội: Phong cách informal, có hashtag, emoji, @mention, hoặc cấu trúc như post/blog
    - Hướng dẫn sử dụng: Có các bước/lệnh, mệnh lệnh (imperative), số thứ tự, lưu ý/cảnh báo
    
    LƯU Ý: Chỉ chọn MỘT genre phù hợp nhất. Nếu văn bản có nhiều đặc điểm, chọn đặc điểm NỔI BẬT NHẤT.
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {{
      "level": "level_detected",
      "genre": "genre_detected",
      "topic": "topic_detected",
    }}
    
    QUAN TRỌNG:
    - Phân tích chính xác level dựa trên từ vựng và ngữ pháp (sử dụng định nghĩa CEFR ở trên)
    - Xác định đúng genre dựa trên phân tích kỹ cấu trúc và phong cách văn bản (xem hướng dẫn chi tiết ở trên)
    - Topic phải được trả về BẰNG TIẾNG VIỆT (ví dụ: "Du lịch", "Công nghệ", "Giáo dục", "Sức khỏe")
    - Trả về JSON format
    """,
    output_schema=TextAnalysisResult,
    output_key="analysis_result",
    after_agent_callback=after_text_analysis_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


