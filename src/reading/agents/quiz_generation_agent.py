from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CorrectAnswer(BaseModel):
    """Schema for correct answer"""
    correct_option: str = Field(..., description="Correct answer option")
    explanation: str = Field(..., description="Explanation for the answer")

class QuizQuestion(BaseModel):
    """Schema for quiz question"""
    id: str = Field(..., description="Question ID")
    question: str = Field(..., description="Question text in Vietnamese")
    options: List[str] = Field(..., description="Answer options in Vietnamese")
    correct_answer: CorrectAnswer = Field(..., description="Correct answer with explanation")

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
    - Tạo câu hỏi trắc nghiệm BẰNG TIẾNG VIỆT từ nội dung bài đọc tiếng Anh
    - Đảm bảo câu hỏi kiểm tra độ hiểu sâu, không chỉ ghi nhớ
    - Tạo đáp án đúng và các phương án nhiễu hợp lý BẰNG TIẾNG VIỆT
    - Đưa ra giải thích chi tiết cho đáp án đúng BẰNG TIẾNG VIỆT
    
    LOẠI CÂU HỎI:
    - Main idea: Ý chính của bài
    - Detail: Chi tiết cụ thể trong bài
    - Inference: Suy luận từ thông tin trong bài
    - Vocabulary: Hiểu nghĩa từ trong ngữ cảnh
    - Author's purpose: Mục đích của tác giả
    - Tone: Giọng điệu của bài viết
    
    YÊU CẦU CÂU HỎI:
    - Câu hỏi BẰNG TIẾNG VIỆT, rõ ràng, không gây nhầm lẫn
    - Đáp án đúng chỉ có 1, các phương án khác hợp lý
    - Tránh câu hỏi quá dễ hoặc quá khó
    - Phân bố đều các loại câu hỏi
    - TẤT CẢ ĐỀU LÀ MULTIPLE CHOICE (A, B, C, D)
    
    FORMAT ĐÁP ÁN:
    - Multiple choice: A, B, C, D
    - Tối thiểu 3 phương án, tối đa 4 phương án
    - Tất cả options BẰNG TIẾNG VIỆT
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "questions": [
        {
          "id": "q1",
          "question": "Câu hỏi bằng tiếng Việt?",
          "options": ["A. Phương án 1", "B. Phương án 2", "C. Phương án 3", "D. Phương án 4"],
          "correct_answer": {
            "correct_option": "B",
            "explanation": "Giải thích bằng tiếng Việt tại sao đáp án này đúng..."
          }
        }
      ]
    }
    
    QUAN TRỌNG:
    - TẤT CẢ CÂU HỎI VÀ ĐÁP ÁN PHẢI BẰNG TIẾNG VIỆT
    - Câu hỏi kiểm tra độ hiểu, không chỉ ghi nhớ
    - Đáp án đúng rõ ràng và duy nhất
    - Giải thích chi tiết và hữu ích BẰNG TIẾNG VIỆT
    - Trả về JSON format
    """,
    output_schema=QuizGenerationResult,
    output_key="quiz_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
