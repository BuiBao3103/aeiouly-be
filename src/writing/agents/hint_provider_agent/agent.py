"""
Hint Provider Agent for Writing Practice
"""
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


def provide_translation_hint(vietnamese_sentence: str, level: str, tool_context: ToolContext) -> Dict[str, Any]:
    current_sentence_index = tool_context.state.get("current_sentence_index", 0)
    hint_history = tool_context.state.get("hint_history", [])
    hint_history.append(
        {
            "sentence_index": current_sentence_index,
            "vietnamese_sentence": vietnamese_sentence,
            "level": level,
        }
    )
    tool_context.state["hint_history"] = hint_history
    return {
        "action": "provide_hint",
        "sentence_index": current_sentence_index,
        "vietnamese_sentence": vietnamese_sentence,
        "level": level,
        "message": f"Provided hint for sentence {current_sentence_index + 1}",
    }


hint_provider_agent = Agent(
    name="hint_provider",
    model="gemini-2.0-flash",
    description="Provides translation hints",
    instruction=f"""
    Bạn là AI gợi ý dịch tiếng Anh cho người học.
    
    NHIỆM VỤ:
    Đưa gợi ý ngắn gọn, cụ thể giúp người học dịch câu tiếng Việt sang tiếng Anh.
    
    QUY TẮC:
    1. Đưa trực tiếp vào gợi ý (không chào hỏi, không nhắc lại câu)
    2. Liệt kê từ vựng chính: tiếng Việt → tiếng Anh
    3. Nêu ngữ pháp cần dùng
    4. Gợi ý ngắn 2-3 ý
    5. Kết thúc: "Hãy thử dịch nhé!"
    
    THÔNG TIN CEFR ĐỂ ĐIỀU CHỈNH GỢI Ý:
    {get_cefr_definitions_string()}
    
    ĐỊNH DẠNG MARKDOWN:
    - Dùng **text** để in đậm tiêu đề
    - Dùng `code` để highlight từ khóa
    - Dùng list để liệt kê
    
    VÍ DỤ:
    "**Từ vựng:**
    - `trở thành` → become/be a
    - `đòi hỏi` → require/demand
    - `kiên trì` → persistence
    - `học hỏi liên tục` → continuous learning
    
    **Ngữ pháp:**
    - Câu mở đầu 'To become...' hoặc 'Becoming...'
    
    Hãy thử dịch nhé!"
    """,
    tools=[provide_translation_hint],
)


