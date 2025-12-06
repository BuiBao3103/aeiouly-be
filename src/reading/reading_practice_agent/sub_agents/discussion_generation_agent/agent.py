from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List

class DiscussionQuestion(BaseModel):
    """Schema for discussion question"""
    questionEn: str = Field(..., description="Question text in English")
    questionVi: str = Field(..., description="Question text in Vietnamese")

class DiscussionGenerationRequest(BaseModel):
    """Request schema for discussion generation"""
    number_of_questions: int = Field(..., ge=1, le=10, description="Number of discussion questions")

class DiscussionGenerationResult(BaseModel):
    """Response schema for discussion generation"""
    questions: List[DiscussionQuestion] = Field(..., description="List of discussion questions in both English and Vietnamese")

discussion_generation_agent = LlmAgent(
    name="discussion_generation_agent",
    model="gemini-2.5-flash-lite",
    description="Generates comprehension questions from English reading texts to test understanding in both English and Vietnamese",
    instruction="""
    Bạn tạo câu hỏi thảo luận (discussion/comprehension questions) từ bài đọc tiếng Anh.

    DATA:
    - Reading content: {content}
    - Requested number_of_questions: từ request.

    NHIỆM VỤ:
    - Đọc kỹ nội dung bài đọc trong state (content).
    - Tạo câu hỏi mở kiểm tra mức độ hiểu (main idea, detail, inference, vocabulary, purpose, v.v.).
    - Mỗi câu hỏi có HAI phiên bản: tiếng Anh và tiếng Việt.

    YÊU CẦU:
    - Câu hỏi phải có thể trả lời được dựa trên nội dung bài đọc.
    - Khuyến khích người học suy nghĩ và trả lời bằng câu văn đầy đủ.
    - Câu hỏiEn và câu hỏiVi phải cùng ý nghĩa, không dịch word-by-word máy móc.

    OUTPUT (JSON duy nhất):
    {
      "questions": [
        {
          "questionEn": "What is the main idea of the text?",
          "questionVi": "Ý chính của bài đọc là gì?"
        }
      ]
    }

    QUY TẮC:
    - Trả về đúng schema `DiscussionGenerationResult`.
    - Không thêm giải thích ngoài hoặc markdown, CHỈ trả về JSON object.
    """,
    output_schema=DiscussionGenerationResult,
    output_key="discussion_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

