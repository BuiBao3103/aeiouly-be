"""
Hint Provider Agent for Writing Practice
"""

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any


def provide_translation_hint(vietnamese_sentence: str, level: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Provide translation hint and track hint history."""
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
    instruction="""
    Bạn là một AI cung cấp gợi ý dịch tiếng Anh cho bài luyện viết.
    
    Nhiệm vụ của bạn là cung cấp gợi ý từ vựng, ngữ pháp và mẹo dịch cho câu tiếng Việt hiện tại.
    
    ## YÊU CẦU:
    1. LUÔN phản hồi bằng TIẾNG VIỆT
    2. Cung cấp từ vựng chính và nghĩa tiếng Anh
    3. Giải thích cấu trúc ngữ pháp
    4. Đưa ra mẹo dịch hữu ích
    5. Khuyến khích người dùng thử dịch
    
    ## CÁCH HOẠT ĐỘNG:
    - Sử dụng provide_translation_hint để xử lý
    - LUÔN trả lời bằng tiếng Việt
    """,
    tools=[provide_translation_hint],
)


