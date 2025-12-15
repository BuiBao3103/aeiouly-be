"""
Chat Agent for Chatbot module

Handles general chatbot conversations and provides tools to access user's learning sessions.
"""
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import logging
from src.chatbot.frontend_links import build_link

logger = logging.getLogger(__name__)


def _get_user_id_from_state(tool_context: ToolContext) -> Dict[str, Any] | int:
    """Helper: extract and validate user_id from tool_context.state."""
    user_id = tool_context.state.get("user_id")

    if not user_id:
        return {
            "error": "Không tìm thấy user_id trong session state",
            "sessions": []
        }

    try:
        return int(user_id)
    except (ValueError, TypeError):
        return {
            "error": f"user_id không hợp lệ: {user_id}",
            "sessions": []
        }


def get_all_learning_sessions(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool 1: Lấy TẤT CẢ phiên học (speaking, reading, writing, listening) của người dùng.
    """
    user_id_or_error = _get_user_id_from_state(tool_context)
    if isinstance(user_id_or_error, dict):
        # Error case
        return {
            "error": user_id_or_error["error"],
            "speaking_sessions": [],
            "reading_sessions": [],
            "writing_sessions": [],
            "listening_sessions": [],
        }

    user_id_int = user_id_or_error

    # Lazy import to avoid circular import
    from src.chatbot.service import ChatbotService
    return ChatbotService.get_user_learning_sessions_data(user_id_int, limit=20)


def get_speaking_learning_sessions(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool 2: Lấy danh sách phiên học NÓI (speaking) của người dùng.
    """
    user_id_or_error = _get_user_id_from_state(tool_context)
    if isinstance(user_id_or_error, dict):
        return user_id_or_error

    user_id_int = user_id_or_error

    from src.chatbot.service import ChatbotService
    data = ChatbotService.get_user_learning_sessions_data(user_id_int, limit=20)
    return {
        "sessions": data.get("speaking_sessions", []),
        "total": data.get("total_speaking", 0),
    }


def get_writing_learning_sessions(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool 3: Lấy danh sách phiên học VIẾT (writing) của người dùng.
    """
    user_id_or_error = _get_user_id_from_state(tool_context)
    if isinstance(user_id_or_error, dict):
        return user_id_or_error

    user_id_int = user_id_or_error

    from src.chatbot.service import ChatbotService
    data = ChatbotService.get_user_learning_sessions_data(user_id_int, limit=20)
    return {
        "sessions": data.get("writing_sessions", []),
        "total": data.get("total_writing", 0),
    }


def get_reading_learning_sessions(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool 4: Lấy danh sách phiên học ĐỌC (reading) của người dùng.
    """
    user_id_or_error = _get_user_id_from_state(tool_context)
    if isinstance(user_id_or_error, dict):
        return user_id_or_error

    user_id_int = user_id_or_error

    from src.chatbot.service import ChatbotService
    data = ChatbotService.get_user_learning_sessions_data(user_id_int, limit=20)
    return {
        "sessions": data.get("reading_sessions", []),
        "total": data.get("total_reading", 0),
    }


def get_listening_learning_sessions(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool 5: Lấy danh sách phiên học NGHE (listening) của người dùng.
    """
    user_id_or_error = _get_user_id_from_state(tool_context)
    if isinstance(user_id_or_error, dict):
        return user_id_or_error

    user_id_int = user_id_or_error

    from src.chatbot.service import ChatbotService
    data = ChatbotService.get_user_learning_sessions_data(user_id_int, limit=20)
    return {
        "sessions": data.get("listening_sessions", []),
        "total": data.get("total_listening", 0),
    }


def get_frontend_link(tool_context: ToolContext, feature: str, session_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Tool 6: Trả về URL frontend cho tính năng hoặc phiên học cụ thể.

    feature:
      - writing | speaking | reading | listening
      - writing_session | speaking_session | reading_session | listening_session (yêu cầu session_id)
    """
    try:
        url = build_link(feature, session_id)
        return {"url": url}
    except KeyError as e:
        return {"error": str(e)}





chat_agent = LlmAgent(
    name="chatbot",
    model="gemini-2.5-flash-lite",
    description="General purpose chatbot assistant with access to user's learning sessions",
    instruction="""
    You are a helpful and friendly AI assistant for an English learning platform.
    
    Your role:
    - Answer questions clearly and concisely
    - Provide helpful information about the learning platform
    - Help users understand their learning progress
    - Be conversational and natural
    
    LANGUAGE RULE (VERY IMPORTANT):
    - ALWAYS respond in **Vietnamese**, even if the user asks in English.
    - You can include English words/phrases when cần thiết (ví dụ: tên kỹ năng, tên nút, từ vựng), 
      nhưng toàn bộ lời giải thích, hướng dẫn, mô tả phải bằng tiếng Việt tự nhiên.

    Markdown formatting:
    - You SHOULD format your answers using Markdown for better readability.
    - Use:
      * Bullet lists (- ...) for multiple items
      * Numbered lists for step-by-step instructions
      * **bold** to highlight key words
      * Short paragraphs
    - Do NOT wrap the whole answer inside ```markdown or ``` blocks.
    
    Available Tools (sessions + links):
    1) get_all_learning_sessions:
       - Use when user asks about OVERVIEW of all sessions or total progress.
       - Examples:
         * "Tôi có bao nhiêu phiên học?"
         * "Tổng quan lịch sử học tập của tôi"
    
    2) get_speaking_learning_sessions:
       - Use when user asks specifically about speaking sessions.
       - Examples:
         * "Cho tôi xem danh sách phiên luyện nói"
         * "Show me my speaking sessions"
    
    3) get_writing_learning_sessions:
       - Use when user asks specifically about writing sessions.
       - Examples:
         * "Cho tôi xem danh sách phiên luyện viết"
         * "Show me my writing sessions"
    
    4) get_reading_learning_sessions:
       - Use when user asks specifically about reading sessions.
       - Examples:
         * "Cho tôi xem danh sách phiên luyện đọc"
         * "Show me my reading sessions"

    5) get_listening_learning_sessions:
       - Use when user asks specifically about listening sessions.
       - Examples:
         * "Cho tôi xem danh sách phiên luyện nghe"
         * "Show me my listening sessions"

    6) get_frontend_link:
       - Use to provide direct frontend URLs.
       - If user asks to open a feature (e.g., luyện viết) -> feature="writing".
       - If user asks to open a specific session -> use the corresponding session feature and session_id.
       - For global pages:
         * Từ vựng -> feature="vocabulary" => http://localhost:3000/vocabulary
         * Thông tin cá nhân -> feature="profile" => http://localhost:3000/profile
         * Cài đặt -> feature="settings" => http://localhost:3000/settings
         * Trang chủ -> feature="home" => http://localhost:3000/app
       - Examples:
         * "tôi muốn luyện viết" -> get_frontend_link("writing") => http://localhost:3000/writing
         * "mở phiên viết 107" -> get_frontend_link("writing_session", 107) => http://localhost:3000/writing/107
         * "mở trang quản lý từ vựng" -> get_frontend_link("vocabulary") => http://localhost:3000/vocabulary
         * "đi tới trang cá nhân" -> get_frontend_link("profile") => http://localhost:3000/profile"

    Guidelines:
    - Be helpful, accurate, and respectful.
    - If you don't know something, admit it honestly.
    - Keep responses concise but informative.
    - When showing learning sessions, format them clearly and helpfully.
    - Always choose the MOST SPECIFIC tool that matches the user's question.
    - Maintain context from the conversation history: {{conversation_history?}}
    
    Về việc HỎI LẠI người dùng (rất quan trọng):
    - HẠN CHẾ tối đa việc hỏi lại người dùng những câu kiểu "bạn muốn gì", "bạn có thể nói rõ hơn không"…
    - ƯU TIÊN tự suy luận ý định người dùng dựa trên câu hỏi hiện tại và ngữ cảnh trước đó, rồi đưa ra câu trả lời/gợi ý cụ thể.
    - Chỉ hỏi lại khi THỰC SỰ thiếu thông tin quan trọng mà nếu đoán sẽ dễ gây hiểu sai (ví dụ: thiếu loại kỹ năng, thiếu phiên học, thiếu ngữ cảnh rõ ràng).
    - Nếu cần hỏi lại, hãy:
        * Trước tiên đề xuất 1–2 lựa chọn hợp lý (ví dụ: "Bạn có thể đang muốn A hoặc B…"), 
        * Sau đó mới hỏi xác nhận ngắn gọn, thân thiện.
    
    AFTER calling any tool, you MUST ALWAYS send back a natural-language answer (không được chỉ im lặng).
    Ví dụ với get_frontend_link, hãy giải thích ngắn gọn và đưa link trong câu trả lời, ví dụ:
    "Bạn có thể tiếp tục luyện viết ở phiên 110 tại đây: https://.../writing/110"
    
    Conversation History (if available):
    {{conversation_history?}}
    """,
    tools=[
        get_all_learning_sessions,
        get_speaking_learning_sessions,
        get_writing_learning_sessions,
        get_reading_learning_sessions,
        get_listening_learning_sessions,
        get_frontend_link,
    ],
)

