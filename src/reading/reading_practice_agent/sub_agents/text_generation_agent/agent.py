from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from src.constants.cefr import CEFRLevel, get_cefr_definitions_string
from src.reading.models import ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel


class TextGenerationResult(BaseModel):
    """Response schema for text generation"""
    content: str = Field(..., description="Generated reading text content")


def create_cefr_instruction() -> str:
    """Create instruction with dynamic CEFR level information"""
    instruction = """
    Bạn là AI chuyên tạo bài đọc tiếng Anh cho việc luyện tập theo thang CEFR (A1-C2).
    
    DỮ LIỆU ĐẦU VÀO (TỪ STATE):
    - level: {level}
    - genre: {genre}
    - topic: {topic}
    - target_word_count: {target_word_count}
    
    NHIỆM VỤ:
    - Tạo bài đọc tiếng Anh phù hợp với level được yêu cầu
    - Đảm bảo nội dung phù hợp với genre và topic
    - Kiểm soát độ dài theo word_count yêu cầu (xấp xỉ ±10%)
    - Sử dụng từ vựng và ngữ pháp phù hợp với level
    
    """
    
    # Add CEFR definitions
    instruction += get_cefr_definitions_string()
    
    instruction += """
    GENRE REQUIREMENTS:
    - Bài báo: Tin tức, sự kiện, phong cách báo chí
    - Email/Thư từ: Thư cá nhân, công việc, trang trọng
    - Truyện ngắn: Có cốt truyện, nhân vật, kết thúc
    - Hội thoại: Đối thoại giữa các nhân vật
    - Bài luận: Luận điểm, lập luận, kết luận
    - Đánh giá sản phẩm: Nhận xét, ưu nhược điểm
    - Bài mạng xã hội: Phong cách informal, hashtag
    - Hướng dẫn sử dụng: Các bước, lưu ý, cách làm
    
    QUAN TRỌNG:
    - Nội dung phù hợp với level CEFR (sử dụng định nghĩa chi tiết ở trên)
    - Đúng genre và topic
    - Độ dài xấp xỉ word_count (±10%)
    
    OUTPUT FORMAT:
    Trả về JSON:
    {
      "content": "Toàn bộ nội dung bài đọc..."
    }
    """
    
    return instruction


class TextGenerationRequest(BaseModel):
    """Request schema for text generation"""
    level: ReadingLevel = Field(..., description="Reading level (A1-C2)")
    genre: ReadingGenre = Field(..., description="Reading genre")
    word_count: int = Field(..., description="Target word count")
    topic: str = Field(..., description="Reading topic")


def after_text_generation_callback(callback_context: CallbackContext) -> Optional[None]:
    """Persist generated content into state for later use."""
    state = callback_context.state or {}
    result = state.get("text_generation_result", {})
    if isinstance(result, dict) and result.get("content"):
        state["content"] = result["content"]
    return None


text_generation_agent = LlmAgent(
    name="text_generation_agent",
    model="gemini-2.0-flash",
    description="Generates English reading texts for practice based on level, genre, and topic",
    instruction=create_cefr_instruction(),
    output_schema=TextGenerationResult,
    output_key="text_generation_result",
    after_agent_callback=after_text_generation_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

