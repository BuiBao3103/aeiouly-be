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
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., description="Answer options")
    type: str = Field(..., description="Question type: multiple_choice or true_false")
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
    - Tạo câu hỏi trắc nghiệm từ nội dung bài đọc
    - Đảm bảo câu hỏi kiểm tra độ hiểu sâu, không chỉ ghi nhớ
    - Tạo đáp án đúng và các phương án nhiễu hợp lý
    - Đưa ra giải thích chi tiết cho đáp án đúng
    
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
    
    FORMAT ĐÁP ÁN:
    - Multiple choice: A, B, C, D
    - True/False: True, False
    - Tối thiểu 3 phương án, tối đa 4 phương án
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "questions": [
        {
          "id": "q1",
          "question": "Câu hỏi?",
          "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
          "type": "multiple_choice",
          "correct_answer": {
            "correct_option": "B",
            "explanation": "Giải thích tại sao đáp án này đúng..."
          }
        }
      ]
    }
    
    QUAN TRỌNG:
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
