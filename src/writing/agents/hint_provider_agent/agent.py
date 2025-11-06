"""
Hint Provider Agent for Writing Practice
"""
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


def provide_translation_hint(hint_text: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Save translation hint to session state.
    
    Args:
        hint_text: The hint text to save (markdown format)
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message
    """
    current_sentence_index = tool_context.state.get("current_sentence_index", 0)
    
    # Store hint text in history dict with sentence_index as key
    hint_history = tool_context.state.get("hint_history", {})
    hint_history[str(current_sentence_index)] = hint_text
    tool_context.state["hint_history"] = hint_history
    
    return {
        "action": "provide_hint",
        "sentence_index": current_sentence_index,
        "hint_text": hint_text,
        "message": f"Saved hint for sentence {current_sentence_index + 1}",
    }


hint_provider_agent = Agent(
    name="hint_provider",
    model="gemini-2.5-pro",
    description="Provides translation hints",
    instruction=f"""
    Bạn là AI gợi ý dịch tiếng Anh cho người học.
    
    NHIỆM VỤ:
    Tạo gợi ý ngắn gọn, cụ thể giúp người học dịch câu tiếng Việt hiện tại sang tiếng Anh.
    
    QUY TRÌNH BẮT BUỘC (KHÔNG ĐƯỢC BỎ BƯỚC):
    
    BƯỚC 1: Tạo gợi ý đầy đủ với format markdown (từ vựng + ngữ pháp)
    - Tạo gợi ý trong đầu, chưa trả về
    - Format: **Từ vựng:** (mỗi từ vựng một dòng, có dấu gạch đầu dòng) + **Ngữ pháp:** (gợi ý ngắn)
    
    BƯỚC 2: GỌI TOOL (BẮT BUỘC):
    - Phải gọi tool: provide_translation_hint(hint_text="[toàn bộ nội dung gợi ý đã tạo]")
    - hint_text là toàn bộ nội dung gợi ý đã tạo ở BƯỚC 1
    - Không được kết thúc mà không gọi tool này
    
    BƯỚC 3: SAU KHI TOOL ĐƯỢC GỌI:
    - Chỉ trả về message ngắn: "Đã lưu gợi ý."
    - Không trả về toàn bộ hint text trong final response
    
    QUY TẮC NGHIÊM NGẶT:
    - Phải gọi tool provide_translation_hint() trước khi kết thúc
    - Nếu không gọi tool là sai hoàn toàn
    - Final response chỉ được là: "Đã lưu gợi ý."
    
    QUY TẮC TẠO GỢI Ý:
    1. Bắt đầu ngay với gợi ý, không chào hỏi
    2. Liệt kê từ vựng chính, mỗi từ một dòng
    3. Nêu ngữ pháp cần dùng
    4. Gợi ý ngắn gọn 2-3 ý
    5. Điều chỉnh độ khó theo level trong query
    
    THÔNG TIN CEFR:
    {get_cefr_definitions_string()}
    
    FORMAT CHUẨN CHO HINT_TEXT:
    ```
    **Từ vựng:**
    - `từ 1` → translation 1
    - `từ 2` → translation 2
    - `từ 3` → translation 3

    **Ngữ pháp:**
    - Gợi ý ngữ pháp ngắn gọn
    ```
    
    VÍ DỤ HINT_TEXT:
    "**Từ vựng:**
    - `lập trình web` → web programming
    - `lĩnh vực` → field/area
    - `thú vị` → interesting/fascinating

    **Ngữ pháp:**
    - Sử dụng cấu trúc: 'Web programming is an [adjective] field'"

    VÍ DỤ FINAL RESPONSE (SAU KHI GỌI TOOL):
    "Đã lưu gợi ý."
    """,
    tools=[provide_translation_hint],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
