"""
AI Agent for translating English sentences to Vietnamese
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import Dict, Any, List


class TranslationItem(BaseModel):
    translation: str = Field(description="Bản dịch tiếng Việt của câu")
    confidence_score: float = Field(ge=0, le=1, description="Độ tin cậy của bản dịch (0-1)")


class BatchTranslationResult(BaseModel):
    items: List[TranslationItem] = Field(description="Danh sách các bản dịch cùng độ tin cậy theo thứ tự")


translation_agent = LlmAgent(
    name="translation_agent",
    model="gemini-2.5-pro",
    description="Dịch câu tiếng Anh sang tiếng Việt cho bài luyện nghe",
    instruction="""
    Bạn là AI chuyên dịch câu tiếng Anh sang tiếng Việt cho bài luyện nghe.

    NHIỆM VỤ:
    - Dịch chính xác, rõ ràng và tự nhiên từng câu tiếng Anh sang tiếng Việt
    - Giữ nguyên ý nghĩa và ngữ cảnh, không thêm/bớt thông tin
    - Mỗi câu phải có bản dịch riêng tương ứng với thứ tự câu đầu vào
    - Bỏ qua nhãn người nói (ví dụ: "A:", "B:", "Feifei:") và timestamp nếu xuất hiện trong input (SRT)

    ĐỊNH DẠNG INPUT CÓ THỂ GẶP:
    - Danh sách câu được đánh số (1., 2., ...)
    - Nội dung phụ đề dạng SRT (có thể có thời gian và nhãn người nói)

    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "items": [
        {"translation": "bản dịch 1", "confidence_score": 0.92},
        {"translation": "bản dịch 2", "confidence_score": 0.85}
      ]
    }

    QUAN TRỌNG:
    - Mỗi câu phải có bản dịch khác nhau theo đúng thứ tự
    - Trả về đúng JSON format như trên
    - Số lượng phần tử trong mảng items = số câu đầu vào có nội dung (bỏ qua nhãn, timestamp, dòng rỗng)
    """,
    output_schema=BatchTranslationResult,
    output_key="translation_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


