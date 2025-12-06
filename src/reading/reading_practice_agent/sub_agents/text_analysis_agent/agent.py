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
    model="gemini-2.5-flash-lite",
    description="Analyzes English reading texts to determine level, genre, and topic",
    instruction=f"""
    Bạn phân tích bài đọc tiếng Anh để xác định level CEFR, genre và topic.

    INPUT (từ state):
    - content: {{content}}

    NHIỆM VỤ:
    - Xác định level CEFR (A1-C2) dựa trên từ vựng và ngữ pháp.
    - Xác định genre chính xác của bài đọc.
    - Xác định topic/chủ đề chính (trả về bằng TIẾNG VIỆT, ví dụ: "Du lịch", "Công nghệ").

    CEFR REFERENCE:
    {get_cefr_definitions_string()}

    GENRE GỢI Ý (chọn 1 phù hợp nhất):
    - Bài báo, Email/Thư từ, Truyện ngắn, Hội thoại, Bài luận,
      Đánh giá sản phẩm, Bài mạng xã hội, Hướng dẫn sử dụng.

    OUTPUT (JSON duy nhất):
    {{
      "level": "level_detected",
      "genre": "genre_detected",
      "topic": "topic_detected"
    }}

    QUY TẮC:
    - Phân tích ngắn gọn, chỉ tập trung vào 3 trường level/genre/topic.
    - Trả về CHỈ MỘT object JSON đúng schema, không thêm giải thích ngoài.
    """,
    output_schema=TextAnalysisResult,
    output_key="analysis_result",
    after_agent_callback=after_text_analysis_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


