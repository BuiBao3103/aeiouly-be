"""
Initial Text Generator Agent

This agent generates the initial reading text before refinement.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from src.constants.cefr import get_cefr_definitions_string

# Constants
GEMINI_MODEL = "gemini-2.5-flash"


class TextGenerationResult(BaseModel):
    """Response schema for text generation"""
    content: str = Field(..., description="Generated reading text content")


def create_generator_instruction() -> str:
    """Create instruction for initial text generator"""
    instruction = """
    Bạn là AI chuyên tạo bài đọc tiếng Anh cho việc luyện tập theo thang CEFR (A1-C2).
    
    DỮ LIỆU ĐẦU VÀO (TỪ STATE):
    - level: {level}
    - genre: {genre}
    - topic: {topic}
    - target_word_count: {target_word_count}
    - user_evaluation_history: {user_evaluation_history}
    
    NHIỆM VỤ:
    - Tạo bài đọc tiếng Anh phù hợp với level được yêu cầu
    - Đảm bảo nội dung phù hợp với genre và topic
    - Cố gắng đạt độ dài gần với target_word_count (sẽ được kiểm tra và tinh chỉnh sau)
    - Sử dụng từ vựng và ngữ pháp phù hợp với level
    - Để đếm từ, hệ thống sẽ tách các từ bằng khoảng trắng. Các dấu câu sẽ không được tính là một từ.
    - Tránh các ký tự đặc biệt hoặc định dạng phức tạp có thể ảnh hưởng đến việc đếm từ.
    
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
    
    OUTPUT FORMAT:
    Trả về JSON:
    {{
      "content": "Toàn bộ nội dung bài đọc..."
    }}
    """
    
    return instruction


def after_generator_callback(callback_context: CallbackContext) -> Optional[None]:
    """Store generated content into state for review and refinement."""
    state = callback_context.state or {}
    result = state.get("text_generation_result", {})
    if isinstance(result, dict) and result.get("content"):
        state["current_text"] = result["content"]
    return None


# Define the Initial Text Generator Agent
initial_text_agent = LlmAgent(
    name="initial_text_agent",
    model=GEMINI_MODEL,
    instruction=create_generator_instruction(),
    description="Generates the initial reading text to start the refinement process",
    output_schema=TextGenerationResult,
    output_key="text_generation_result",
    after_agent_callback=after_generator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

