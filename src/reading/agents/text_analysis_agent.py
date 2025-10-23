from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from src.constants.cefr import CEFRLevel, get_cefr_definitions_string
from src.reading.models import ReadingGenre

# Use CEFRLevel from constants
ReadingLevel = CEFRLevel

class TextAnalysisRequest(BaseModel):
    """Request schema for text analysis"""
    content: str = Field(..., description="Text content to analyze")

class TextAnalysisResult(BaseModel):
    """Response schema for text analysis"""
    level: ReadingLevel = Field(..., description="Detected reading level")
    genre: ReadingGenre = Field(..., description="Detected genre")
    topic: str = Field(..., description="Detected topic")
    word_count: int = Field(..., description="Word count")
    key_themes: List[str] = Field(..., description="Key themes in the text")
    difficulty_factors: List[str] = Field(..., description="Factors that make it difficult")

text_analysis_agent = LlmAgent(
    name="text_analysis_agent",
    model="gemini-2.0-flash",
    description="Analyzes English reading texts to determine level, genre, and topic",
    instruction=f"""
    Bạn là AI chuyên phân tích bài đọc tiếng Anh để xác định level CEFR, genre và topic.
    
    NHIỆM VỤ:
    - Phân tích độ khó của bài đọc và xác định level CEFR (A1-C2)
    - Xác định genre của bài đọc
    - Xác định topic/chủ đề chính
    - Đếm số từ chính xác
    - Xác định các chủ đề chính và yếu tố khó
    
    {get_cefr_definitions_string()}
    
    GENRE DETECTION:
    - Bài báo: Tin tức, sự kiện, phong cách báo chí
    - Email/Thư từ: Thư cá nhân, công việc, trang trọng
    - Truyện ngắn: Có cốt truyện, nhân vật, kết thúc
    - Hội thoại: Đối thoại giữa các nhân vật
    - Bài luận: Luận điểm, lập luận, kết luận
    - Đánh giá sản phẩm: Nhận xét, ưu nhược điểm
    - Bài mạng xã hội: Phong cách informal, hashtag
    - Hướng dẫn sử dụng: Các bước, lưu ý, cách làm
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {{
      "level": "level_detected",
      "genre": "genre_detected",
      "topic": "topic_detected",
      "word_count": số_từ,
      "key_themes": ["chủ đề 1", "chủ đề 2"],
      "difficulty_factors": ["yếu tố khó 1", "yếu tố khó 2"]
    }}
    
    QUAN TRỌNG:
    - Phân tích chính xác level dựa trên từ vựng và ngữ pháp (sử dụng định nghĩa CEFR ở trên)
    - Xác định đúng genre và topic
    - Đếm từ chính xác (không tính dấu câu)
    - Trả về JSON format
    """,
    output_schema=TextAnalysisResult,
    output_key="analysis_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
