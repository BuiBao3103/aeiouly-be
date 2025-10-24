from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.models import CustomModel
from src.pagination import PaginatedResponse


class VocabularySetBase(CustomModel):
    name: str = Field(..., min_length=1, max_length=200, description="Tên bộ từ vựng")
    description: Optional[str] = Field(None, description="Mô tả bộ từ vựng")


class VocabularySetCreate(VocabularySetBase):
    pass


class VocabularySetUpdate(CustomModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Tên bộ từ vựng")
    description: Optional[str] = Field(None, description="Mô tả bộ từ vựng")


class VocabularySetResponse(VocabularySetBase):
    id: int = Field(..., description="ID bộ từ vựng")
    user_id: int = Field(..., description="ID người dùng")
    is_default: bool = Field(..., description="Có phải bộ từ vựng mặc định")
    total_words: int = Field(..., description="Tổng số từ vựng trong bộ")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


class VocabularyItemCreate(CustomModel):
    vocabulary_set_id: Optional[int] = Field(None, description="ID bộ từ vựng (bỏ trống nếu muốn thêm vào bộ mặc định)")
    dictionary_id: int = Field(..., description="ID từ trong từ điển")
    use_default_set: bool = Field(False, description="Thêm vào bộ từ vựng mặc định của user")


class VocabularyItemResponse(CustomModel):
    id: int = Field(..., description="ID từ vựng")
    user_id: int = Field(..., description="ID người dùng")
    vocabulary_set_id: int = Field(..., description="ID bộ từ vựng")
    dictionary_id: int = Field(..., description="ID từ trong từ điển")
    created_at: datetime = Field(..., description="Thời gian thêm")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")
    word: Optional[str] = Field(None, description="Từ tiếng Anh")
    definitions: Optional[str] = Field(None, description="Định nghĩa")


class VocabularyProgressUpdate(CustomModel):
    mastery_level: int = Field(..., ge=0, le=5, description="Mức độ thành thạo (0-5)")


class VocabularyProgressResponse(CustomModel):
    id: int = Field(..., description="ID tiến độ")
    user_id: int = Field(..., description="ID người dùng")
    vocabulary_item_id: int = Field(..., description="ID từ vựng")
    mastery_level: int = Field(..., description="Mức độ thành thạo (0-5)")
    review_count: int = Field(..., description="Số lần ôn tập")
    last_reviewed_at: Optional[datetime] = Field(None, description="Lần ôn tập cuối")
    next_review_at: Optional[datetime] = Field(None, description="Lần ôn tập tiếp theo")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


class VocabularySetListResponse(CustomModel):
    vocabulary_sets: List[VocabularySetResponse] = Field(..., description="Danh sách bộ từ vựng")
    total: int = Field(..., description="Tổng số bộ từ vựng")


class VocabularyItemListResponse(CustomModel):
    vocabulary_items: List[VocabularyItemResponse] = Field(..., description="Danh sách từ vựng")
    total: int = Field(..., description="Tổng số từ vựng")


class StudySessionCreate(CustomModel):
    vocabulary_set_id: int = Field(..., description="ID bộ từ vựng để học")
    max_items: Optional[int] = Field(20, ge=1, le=50, description="Số từ tối đa trong phiên học")


class StudySessionResponse(CustomModel):
    session_id: str = Field(..., description="ID phiên học")
    vocabulary_set_id: int = Field(..., description="ID bộ từ vựng")
    total_items: int = Field(..., description="Tổng số từ trong phiên")
    current_item: int = Field(..., description="Từ hiện tại")
    items: List[VocabularyItemResponse] = Field(..., description="Danh sách từ trong phiên học")


# Flashcard schemas
class FlashcardResponse(CustomModel):
    id: int = Field(..., description="ID từ vựng")
    word: str = Field(..., description="Từ tiếng Anh")
    definitions: str = Field(..., description="Định nghĩa")


class FlashcardSessionResponse(CustomModel):
    session_id: str = Field(..., description="ID phiên học")
    vocabulary_set_id: int = Field(..., description="ID bộ từ vựng")
    total_cards: int = Field(..., description="Tổng số thẻ")
    current_card: int = Field(..., description="Thẻ hiện tại")
    cards: List[FlashcardResponse] = Field(..., description="Danh sách thẻ")


# Multiple Choice schemas
class MultipleChoiceOption(CustomModel):
    option_id: str = Field(..., description="ID phương án")
    text: str = Field(..., description="Nội dung phương án")
    is_correct: bool = Field(..., description="Có phải đáp án đúng")


class MultipleChoiceQuestion(CustomModel):
    id: int = Field(..., description="ID từ vựng")
    word: str = Field(..., description="Từ tiếng Anh")
    options: List[MultipleChoiceOption] = Field(..., description="Danh sách phương án")


class MultipleChoiceSessionResponse(CustomModel):
    session_id: str = Field(..., description="ID phiên học")
    vocabulary_set_id: int = Field(..., description="ID bộ từ vựng")
    total_questions: int = Field(..., description="Tổng số câu hỏi")
    current_question: int = Field(..., description="Câu hỏi hiện tại")
    questions: List[MultipleChoiceQuestion] = Field(..., description="Danh sách câu hỏi")


class AnswerSubmission(CustomModel):
    session_id: str = Field(..., description="ID phiên học")
    question_id: int = Field(..., description="ID câu hỏi")
    selected_option_id: str = Field(..., description="ID phương án được chọn")
    is_correct: bool = Field(..., description="Có trả lời đúng")


class StudyResultResponse(CustomModel):
    session_id: str = Field(..., description="ID phiên học")
    total_questions: int = Field(..., description="Tổng số câu hỏi")
    correct_answers: int = Field(..., description="Số câu trả lời đúng")
    accuracy: float = Field(..., description="Độ chính xác (%)")
    updated_items: List[VocabularyItemResponse] = Field(..., description="Danh sách từ đã cập nhật")
