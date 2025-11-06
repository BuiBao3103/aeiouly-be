"""
Translation Evaluator Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any


def evaluate_translation(
    vietnamese_sentence: str,
    user_translation: str,
    level: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    current_sentence_index = tool_context.state.get("current_sentence_index", 0)
    evaluation_history = tool_context.state.get("evaluation_history", [])
    evaluation_history.append(
        {
            "sentence_index": current_sentence_index,
            "vietnamese": vietnamese_sentence,
            "user_translation": user_translation,
            "level": level,
        }
    )
    tool_context.state["evaluation_history"] = evaluation_history

    return {
        "action": "evaluate_translation",
        "sentence_index": current_sentence_index,
        "vietnamese_sentence": vietnamese_sentence,
        "user_translation": user_translation,
        "level": level,
        "message": f"Evaluated translation for sentence {current_sentence_index + 1}",
    }


def get_next_sentence(tool_context: ToolContext) -> Dict[str, Any]:
    current_index = tool_context.state.get("current_sentence_index", 0)
    total_sentences = tool_context.state.get("total_sentences", 0)
    session_id = tool_context.state.get("session_id")

    if current_index >= total_sentences - 1:
        tool_context.state["current_sentence_index"] = total_sentences
        try:
            from src.database import SessionLocal
            from src.writing.models import WritingSession, SessionStatus
            db = SessionLocal()
            session = db.query(WritingSession).filter(WritingSession.id == session_id).first()
            if session:
                session.current_sentence_index = total_sentences
                session.status = SessionStatus.COMPLETED
                db.commit()
            db.close()
        except Exception as e:
            print(f"Error updating database on completion: {e}")
        return {
            "action": "session_complete",
            "message": "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!",
            "current_index": total_sentences,
            "total_sentences": total_sentences,
        }

    next_index = current_index + 1
    tool_context.state["current_sentence_index"] = next_index
    try:
        from src.database import SessionLocal
        from src.writing.models import WritingSession, SessionStatus
        db = SessionLocal()
        session = db.query(WritingSession).filter(WritingSession.id == session_id).first()
        if session:
            session.current_sentence_index = next_index
            if next_index >= total_sentences:
                session.status = SessionStatus.COMPLETED
            db.commit()
        db.close()
    except Exception as e:
        print(f"Error updating database: {e}")

    return {
        "action": "next_sentence",
        "current_index": next_index,
        "total_sentences": total_sentences,
        "message": f"Chuyển sang câu {next_index + 1} trong tổng số {total_sentences} câu",
    }


translation_evaluator_agent = LlmAgent(
    name="translation_evaluator",
    model="gemini-2.0-flash",
    description="Evaluates user translations and provides detailed feedback",
    instruction="""
    Bạn là một AI đánh giá bản dịch tiếng Anh cho bài luyện viết.
    Bắt buộc phải:
    - Gọi evaluate_translation để lưu kết quả
    - Chỉ gọi get_next_sentence nếu bản dịch đúng nghĩa và đúng ngữ pháp
    - Trả lời rõ ràng người dùng: đúng hay sai, chỉ lỗi cụ thể khi sai
    """,
    tools=[evaluate_translation, get_next_sentence],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


