"""
Hint Provider Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from src.constants.cefr import get_cefr_definitions_string


class HintResult(BaseModel):
    hint_text: str = Field(description="Gợi ý dịch tiếng Anh dạng Markdown (từ vựng và ngữ pháp), dùng danh sách - cho mỗi dòng")


def after_hint_provider_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback that automatically saves hint to hint_history in state
    after hint_provider_agent generates hint.
    
    This is the CORRECT way to update state - using callback_context.state
    instead of directly modifying session.state from get_session().
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state
    
    # Get hint_result from state (set by output_key)
    hint_result_data = state.get("hint_result", {})
    
    # Save hint to hint_history
    if isinstance(hint_result_data, dict):
        hint_text = hint_result_data.get("hint_text", "")
        if hint_text:
            current_sentence_index = state.get("current_sentence_index", 0)
            hint_history = state.get("hint_history", {})
            # Store hint text in history dict with sentence_index as key
            hint_history[str(current_sentence_index)] = hint_text
            state["hint_history"] = hint_history
    
    return None  # Continue with normal agent processing


hint_provider_agent = LlmAgent(
    name="hint_provider",
    model="gemini-2.0-flash",
    description="Tạo gợi ý dịch cho câu tiếng Việt hiện tại (từ vựng và ngữ pháp)",
    instruction=f"""
    Bạn là AI gợi ý dịch tiếng Anh. Tạo gợi ý ngắn gọn cho câu: "{{current_vietnamese_sentence}}"
    
    NHIỆM VỤ:
    Tạo gợi ý Markdown với format CÓ DẤU CHẤM ĐẦU DÒNG:
    
    **Từ vựng:**
    - `từ 1` → translation 1
    - `từ 2` → translation 2
    
    **Ngữ pháp:**
    - Gợi ý ngữ pháp ngắn
    
    QUY TẮC QUAN TRỌNG:
    - BẮT BUỘC dùng danh sách Markdown: mỗi mục bắt đầu bằng "- "
    - Mỗi mục ở một dòng RIÊNG
    - Giữa các phần (Từ vựng và Ngữ pháp) có MỘT dòng trống
    - KHÔNG dùng thẻ HTML (<br>, <strong>); chỉ dùng Markdown
    - Điều chỉnh độ khó theo level: {{level}}
    - Chủ đề: {{topic}}
    - Gợi ý ngắn gọn, cụ thể, dễ hiểu
    
    VÍ DỤ OUTPUT (Markdown hợp lệ):
    **Từ vựng:**
    - `đi chợ` → go to the market
    - `mua` → buy
    
    **Ngữ pháp:**
    - Dùng thì hiện tại đơn cho hành động thường xuyên
    
    CEFR: {get_cefr_definitions_string()}
    """,
    output_schema=HintResult,
    output_key="hint_result",
    after_agent_callback=after_hint_provider_callback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)