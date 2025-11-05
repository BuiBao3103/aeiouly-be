from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class QuizQuestion(BaseModel):
    """Schema for quiz question"""
    questionEn: str = Field(..., description="Question text in English")
    questionVi: str = Field(..., description="Question text in Vietnamese")
    optionsEn: List[str] = Field(..., description="Answer options in English (plain text, no A/B/C/D prefix)")
    optionsVi: List[str] = Field(..., description="Answer options in Vietnamese (plain text, no A/B/C/D prefix)")
    correctAnswer: int = Field(..., description="Index of correct answer (0-based)")
    explanationEn: str = Field(..., description="Explanation for the correct answer in English")
    explanationVi: str = Field(..., description="Explanation for the correct answer in Vietnamese")

class QuizGenerationRequest(BaseModel):
    """Request schema for quiz generation"""
    content: str = Field(..., description="Reading text content")
    number_of_questions: int = Field(..., ge=3, le=10, description="Number of questions")

class QuizGenerationResult(BaseModel):
    """Response schema for quiz generation"""
    questions: List[QuizQuestion] = Field(..., description="List of questions with correct answers")

quiz_generation_agent = LlmAgent(
    name="quiz_generation_agent",
    model="gemini-2.0-flash",
    description="Generates quizzes from English reading texts to test comprehension",
    instruction="""
    Bạn là AI chuyên tạo bài trắc nghiệm từ bài đọc tiếng Anh để kiểm tra độ hiểu.
    
    NHIỆM VỤ:
    - Tạo câu hỏi trắc nghiệm từ nội dung bài đọc tiếng Anh
    - Đảm bảo câu hỏi kiểm tra độ hiểu sâu, không chỉ ghi nhớ
    - Tạo đáp án đúng và các phương án nhiễu hợp lý
    - Đưa ra giải thích chi tiết cho đáp án đúng
    
    NGÔN NGỮ CÂU HỎI:
    - MỖI câu hỏi phải được tạo BẰNG CẢ TIẾNG ANH VÀ TIẾNG VIỆT
    - questionEn: Câu hỏi bằng tiếng Anh
    - questionVi: Câu hỏi bằng tiếng Việt (dịch chính xác từ tiếng Anh)
    - optionsEn: Các phương án trả lời bằng tiếng Anh
    - optionsVi: Các phương án trả lời bằng tiếng Việt (dịch chính xác từ tiếng Anh)
    - explanationEn: Giải thích bằng tiếng Anh
    - explanationVi: Giải thích bằng tiếng Việt (dịch chính xác từ tiếng Anh)
    
    LOẠI CÂU HỎI:
    - Main idea: Ý chính của bài
    - Detail: Chi tiết cụ thể trong bài
    - Inference: Suy luận từ thông tin trong bài
    - Vocabulary: Hiểu nghĩa từ trong ngữ cảnh
    - Author's purpose: Mục đích của tác giả
    - Tone: Giọng điệu của bài viết
    
    YÊU CẦU CÂU HỎI:
    - Câu hỏi rõ ràng, không gây nhầm lẫn
    - Đáp án đúng chỉ có 1, các phương án khác hợp lý
    - Tránh câu hỏi quá dễ hoặc quá khó
    - Phân bố đều các loại câu hỏi
    - TẤT CẢ ĐỀU LÀ MULTIPLE CHOICE (A, B, C, D)
    
    FORMAT ĐÁP ÁN:
    - Multiple choice: 4 phương án (A, B, C, D)
    - Tất cả options phải có CẢ tiếng Anh VÀ tiếng Việt
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "questions": [
        {
          "questionEn": "Question in English?",
          "questionVi": "Câu hỏi bằng tiếng Việt?",
          "optionsEn": ["Option 1", "Option 2", "Option 3", "Option 4"],
          "optionsVi": ["Phương án 1", "Phương án 2", "Phương án 3", "Phương án 4"],
          "correctAnswer": 1,
          "explanationEn": "Explanation in English why this answer is correct...",
          "explanationVi": "Giải thích bằng tiếng Việt tại sao đáp án này đúng..."
        }
      ]
    }
    
    LƯU Ý QUAN TRỌNG:
    - optionsEn và optionsVi: CHỈ TEXT THUẦN, KHÔNG có prefix "A.", "B.", "C.", "D."
    - correctAnswer: là INDEX số (0-based), ví dụ: 0 = option đầu tiên, 1 = option thứ hai, 2 = option thứ ba, 3 = option thứ tư
    - correctAnswer áp dụng cho CẢ optionsEn và optionsVi (cùng index)
    - MỖI câu hỏi PHẢI có CẢ tiếng Anh VÀ tiếng Việt
    - Câu hỏi tiếng Việt phải là bản dịch chính xác của câu hỏi tiếng Anh
    - Các phương án tiếng Việt phải là bản dịch chính xác của các phương án tiếng Anh
    - Giải thích tiếng Việt phải là bản dịch chính xác của giải thích tiếng Anh
    - Câu hỏi kiểm tra độ hiểu, không chỉ ghi nhớ
    - Đáp án đúng rõ ràng và duy nhất
    - Giải thích chi tiết và hữu ích
    - Trả về JSON format
    """,
    output_schema=QuizGenerationResult,
    output_key="quiz_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


