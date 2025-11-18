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
    model="gemini-2.0-flash",
    description="Generates comprehension questions from English reading texts to test understanding in both English and Vietnamese",
    instruction="""
    Bạn là AI chuyên tạo câu hỏi kiểm tra hiểu (comprehension questions) từ bài đọc tiếng Anh để đánh giá xem người đọc có hiểu nội dung hay không.
    
    DATA AVAILABLE:
    - Reading text content: {content}
    - Requested number of questions: from the query message
    
    NHIỆM VỤ:
    - Đọc kỹ nội dung bài đọc từ state (content)
    - Tạo câu hỏi kiểm tra hiểu từ nội dung bài đọc tiếng Anh
    - Câu hỏi phải kiểm tra được độ hiểu của người đọc về bài đọc
    - Câu hỏi dạng mở (open-ended) để người đọc có thể trả lời bằng câu văn
    - Đưa ra câu hỏi ở CẢ HAI ngôn ngữ: tiếng Anh và tiếng Việt
    
    LOẠI CÂU HỎI KIỂM TRA HIỂU:
    - Main idea: Ý chính của bài là gì? (What is the main idea of the text?)
    - Detail: Chi tiết cụ thể trong bài (What does the text say about...?)
    - Inference: Suy luận từ thông tin trong bài (What can you infer from...?)
    - Vocabulary: Hiểu nghĩa từ trong ngữ cảnh (What does the word/phrase '...' mean in this context?)
    - Author's purpose: Mục đích của tác giả (What is the author's purpose in writing this?)
    - Cause and effect: Nguyên nhân và kết quả (What causes...? What is the result of...?)
    - Sequence: Trình tự sự kiện (What happens first? What happens next?)
    - Compare and contrast: So sánh và đối chiếu (How is X different from Y in the text?)
    
    YÊU CẦU CÂU HỎI:
    - Câu hỏi rõ ràng, dễ hiểu
    - Phải có thể trả lời dựa trên nội dung bài đọc
    - Khuyến khích người đọc suy nghĩ và diễn đạt bằng từ ngữ của chính họ
    - Phân bố đều các loại câu hỏi
    - Câu hỏi phải liên quan trực tiếp đến nội dung bài đọc được cung cấp
    - Câu hỏi phải kiểm tra được mức độ hiểu, không chỉ ghi nhớ
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "questions": [
        {
          "questionEn": "What is the main idea of the text?",
          "questionVi": "Ý chính của bài đọc là gì?"
        }
      ]
    }
    
    LƯU Ý QUAN TRỌNG:
    - MỖI câu hỏi PHẢI có CẢ HAI phiên bản: questionEn (tiếng Anh) và questionVi (tiếng Việt)
    - Câu hỏi tiếng Anh và tiếng Việt phải có cùng ý nghĩa, không chỉ dịch word-by-word
    - Câu hỏi phải là câu hỏi kiểm tra hiểu, có thể đánh giá được câu trả lời dựa trên nội dung bài đọc
    - Câu hỏi phải liên quan trực tiếp đến nội dung bài đọc trong state
    - Trả về JSON format
    """,
    output_schema=DiscussionGenerationResult,
    output_key="discussion_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

