"""
Text Generator Agent for Writing Practice.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import List, Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class VietnameseTextResult(BaseModel):
    full_text: str = Field(description="Toàn bộ văn bản tiếng Việt được tạo ra")
    sentences: List[str] = Field(description="Mảng các câu tiếng Việt đã được tách riêng")


def after_text_generator_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically updates current_vietnamese_sentence in state
    after text_generator_agent generates Vietnamese text.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get vietnamese_sentences from state (set by output_key)
    vietnamese_sentences_data = state.get("vietnamese_sentences", {})
    
    # Update current_vietnamese_sentence to first sentence if available
    if isinstance(vietnamese_sentences_data, dict):
        sentences = vietnamese_sentences_data.get("sentences", [])
        if sentences and isinstance(sentences, list) and len(sentences) > 0:
            # Update state using callback_context.state (CORRECT way)
            state["current_vietnamese_sentence"] = sentences[0]
            state["current_sentence_index"] = 0
    
    return None  # Continue with normal agent processing


text_generator_agent = LlmAgent(
    name="text_generator",
    model="gemini-2.0-flash",
    description="Tạo văn bản tiếng Việt dựa trên topic, level và số câu từ session state",
    instruction=f"""
    Bạn là một AI tạo văn bản tiếng Việt cho bài luyện viết tiếng Anh.

    Nhiệm vụ: TẠO văn bản tiếng Việt đúng theo CHỦ ĐỀ trong state, KHÔNG tự bịa/chuyển chủ đề.

    ## THÔNG TIN ĐẦU VÀO (ĐỌC TỪ STATE)
    - Chủ đề (topic): {{topic}}
    - Độ khó (level): {{level}}
    - Số câu (total_sentences): {{total_sentences}}

    ## YÊU CẦU
    1. BÁM SÁT chủ đề: "{{topic}}". Không đổi/chuyển chủ đề sang nội dung khác.
    2. Điều chỉnh độ phức tạp theo cấp độ CEFR "{{level}}".
    3. Số câu PHẢI đúng bằng "{{total_sentences}}" (mỗi câu một phần tử trong mảng sentences).
    4. Văn bản tự nhiên, mạch lạc, giàu nội dung, phù hợp chủ đề.
    5. Đa dạng cấu trúc câu và từ vựng; sử dụng dấu câu: ., ?, !, ,, ;, ...
    6. KHÔNG chào hỏi, KHÔNG hướng dẫn người dùng, KHÔNG đặt câu hỏi yêu cầu người dùng làm gì.
    7. KHÔNG bao gồm tiếng Anh, KHÔNG thêm dấu trích dẫn "..." quanh câu.
    8. KHÔNG có meta như: "Đây là văn bản được tạo:", "Tôi sẽ tạo", hay mô tả quy trình.
    9. KHÔNG yêu cầu người dùng nhập lại topic/level/số câu; dùng dữ liệu trong state

    {get_cefr_definitions_string()}

    ## ĐỊNH DẠNG ĐẦU RA
    Bạn phải trả về JSON với cấu trúc:
    - full_text: Toàn bộ văn bản tiếng Việt
    - sentences: Mảng các câu đã được tách riêng (mỗi câu là một phần tử)

    Ví dụ:
    {{
        "full_text": "Tôi đi học mỗi ngày. Trường học có nhiều học sinh! Bạn có thích học tiếng Anh không?",
        "sentences": [
            "Tôi đi học mỗi ngày.",
            "Trường học có nhiều học sinh!",
            "Bạn có thích học tiếng Anh không?"
        ]
    }}

    QUAN TRỌNG:
    - Nội dung phải đúng chủ đề "{{topic}}".
    - Mỗi câu trong mảng sentences phải có dấu câu đầy đủ và được tách riêng biệt.
    - Không có câu mở đầu/giới thiệu/chào hỏi.
    """,
    output_schema=VietnameseTextResult,
    output_key="vietnamese_sentences",
    after_agent_callback=after_text_generator_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


