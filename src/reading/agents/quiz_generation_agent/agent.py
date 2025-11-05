from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class QuizQuestion(BaseModel):
    """Schema for quiz question"""
    question: str = Field(..., description="Question text in specified language")
    options: List[str] = Field(..., description="Answer options (plain text, no A/B/C/D prefix) in specified language")
    correctAnswer: int = Field(..., description="Index of correct answer (0-based)")
    explanation: str = Field(..., description="Explanation for the correct answer in specified language")

class QuizGenerationRequest(BaseModel):
    """Request schema for quiz generation"""
    content: str = Field(..., description="Reading text content")
    number_of_questions: int = Field(..., ge=3, le=10, description="Number of questions")
    question_language: str = Field("vietnamese", description="Language for questions: 'vietnamese' or 'english'")

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
    - Nếu question_language = "vietnamese": Tất cả câu hỏi, đáp án và giải thích BẰNG TIẾNG VIỆT
    - Nếu question_language = "english": Tất cả câu hỏi, đáp án và giải thích BẰNG TIẾNG ANH
    
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
    - Multiple choice: A, B, C, D
    - Tối thiểu 3 phương án, tối đa 4 phương án
    - Tất cả options theo ngôn ngữ được chỉ định
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "questions": [
        {
          "question": "Câu hỏi theo ngôn ngữ được chỉ định?",
          "options": ["Phương án 1", "Phương án 2", "Phương án 3", "Phương án 4"],
          "correctAnswer": 1,
          "explanation": "Giải thích theo ngôn ngữ được chỉ định tại sao đáp án này đúng..."
        }
      ]
    }
    
    LƯU Ý QUAN TRỌNG:
    - options: CHỈ TEXT THUẦN, KHÔNG có prefix "A.", "B.", "C.", "D."
    - correctAnswer: là INDEX số (0-based), ví dụ: 0 = option đầu tiên, 1 = option thứ hai, 2 = option thứ ba, 3 = option thứ tư
    - SỬ DỤNG ĐÚNG NGÔN NGỮ ĐƯỢC CHỈ ĐỊNH TRONG question_language
    - Câu hỏi kiểm tra độ hiểu, không chỉ ghi nhớ
    - Đáp án đúng rõ ràng và duy nhất
    - Giải thích chi tiết và hữu ích theo ngôn ngữ được chỉ định
    - Trả về JSON format
    """,
    output_schema=QuizGenerationResult,
    output_key="quiz_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


