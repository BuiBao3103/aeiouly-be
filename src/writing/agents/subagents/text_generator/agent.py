"""
Text Generator Agent for Writing Practice

This agent generates Vietnamese text based on topic and level.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List
from src.constants.cefr import get_cefr_definitions_string


# --- Define Output Schema ---
class VietnameseTextResult(BaseModel):
    """Schema for Vietnamese text generation results."""
    
    full_text: str = Field(
        description="Toàn bộ văn bản tiếng Việt được tạo ra"
    )
    sentences: List[str] = Field(
        description="Mảng các câu tiếng Việt đã được tách riêng"
    )


text_generator_agent = LlmAgent(
    name="text_generator",
    model="gemini-2.0-flash",
    description="Generates Vietnamese text for writing practice based on topic and level",
    instruction=f"""
    Bạn là một AI tạo văn bản tiếng Việt cho bài luyện viết tiếng Anh.

    Nhiệm vụ của bạn là tạo ra văn bản tiếng Việt dựa trên chủ đề và độ khó được cung cấp.

    ## THÔNG TIN ĐẦU VÀO
    **Chủ đề:** {{topic}}
    **Độ khó:** {{level}}
    **Số câu:** {{total_sentences}}

    ## YÊU CẦU
    1. Tạo ra văn bản tiếng Việt phù hợp với chủ đề
    2. Điều chỉnh độ phức tạp theo cấp độ CEFR
    3. Đảm bảo văn bản tự nhiên và hấp dẫn
    4. Tạo câu ngày càng thử thách trong cùng độ khó
    5. Bao gồm đa dạng cấu trúc câu và từ vựng
    6. Sử dụng đa dạng dấu câu: dấu chấm (.), dấu chấm hỏi (?), dấu chấm than (!), dấu phẩy (,), dấu chấm phẩy (;), dấu ba chấm (...)
    7. KHÔNG bao gồm văn bản tiếng Anh hoặc giải thích
    8. KHÔNG bao gồm cụm từ như "Đây là văn bản được tạo:" hoặc "Tôi sẽ tạo"

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

    QUAN TRỌNG: Mỗi câu trong mảng sentences phải có dấu câu đầy đủ và được tách riêng biệt.
    """,
    output_schema=VietnameseTextResult,
    output_key="vietnamese_text",
)


