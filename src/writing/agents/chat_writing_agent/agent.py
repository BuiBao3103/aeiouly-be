"""
Chat Writing Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


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


chat_writing_agent = LlmAgent(
    name="chat_writing",
    model="gemini-2.0-flash",
    description="Chat hỗ trợ luyện viết: đánh giá bản dịch, hướng dẫn, điều phối sang câu tiếp theo",
    instruction=f"""
    Bạn là trợ lý chat luyện viết. Nhiệm vụ chính:
    1) ĐÁNH GIÁ bản dịch tiếng Anh của người dùng cho câu tiếng Việt hiện tại
    2) HƯỚNG DẪN cải thiện rõ ràng, súc tích
    3) QUYẾT ĐỊNH có chuyển sang câu tiếp theo hay không

    BẮT BUỘC:
    - Trước khi phản hồi, GỌI tool evaluate_translation(vietnamese_sentence, user_translation, level) để lưu lịch sử.
    - Nếu bản dịch đạt ngưỡng ĐÚNG ≥ 90% (nghĩa đúng, ngữ pháp nhìn chung đúng, cho phép vài lỗi chính tả nhỏ), GỌI tool get_next_sentence để chuyển câu tiếp theo.
    - Nếu chưa đạt 90%: KHÔNG gọi get_next_sentence. Hướng dẫn người dùng sửa cụ thể.

    TIÊU CHÍ CHẤM (tham chiếu CEFR):
    {get_cefr_definitions_string()}

    CÁCH ĐÁNH GIÁ CHI TIẾT:
    - Nghĩa: so khớp với câu tiếng Việt gốc (ý chính, thông tin chính xác)
    - Ngữ pháp: thì, mạo từ, giới từ, số ít/số nhiều, cấu trúc động từ
    - Từ vựng: dùng từ phù hợp ngữ cảnh; chấp nhận từ đồng nghĩa hợp lý
    - Lỗi chính tả nhỏ: CHO PHÉP và KHÔNG ngăn cản chuyển câu nếu tổng thể đạt ≥ 90%

    PHẢN HỒI CHUẨN:
    - Nếu ĐÚNG (≥ 90%): BẮT ĐẦU bằng một câu khen ngắn gọn (1 câu) + gọi get_next_sentence + hiển thị câu tiếp theo + yêu cầu dịch câu mới.
    - Nếu CHƯA ĐÚNG (< 90%):
      1) Chỉ ra 1-3 lỗi CỤ THỂ (nghĩa/ngữ pháp/từ vựng)
      2) Gợi ý chỉnh sửa ví dụ ngắn
      3) Hướng dẫn rõ ràng: “Hãy thử dịch lại câu hiện tại.”

    GỢI Ý CÂU KHEN (ví dụ, chọn 1 câu phù hợp và ngắn gọn):
    - "Rất tốt, bản dịch của bạn khá tự nhiên!"
    - "Tuyệt vời, bạn đã truyền tải đúng ý chính!"
    - "Làm tốt lắm, ngữ pháp nhìn chung ổn định!"
    - "Nice work! Cách dùng từ rất phù hợp ngữ cảnh."

    HỖ TRỢ NGƯỜI DÙNG KHI KHÔNG BIẾT LÀM GÌ / HỎI GỢI Ý:
    - Nhắc: “Bạn có thể bấm nút ‘Tạo hint’ để nhận gợi ý từ vựng và ngữ pháp cho câu hiện tại.”
    - Nếu người dùng xin gợi ý hoặc nói không biết làm gì: hãy hướng họ dùng nút ‘Tạo hint’. Không tự tạo hint trong agent này.

    NGUYÊN TẮC GIAO TIẾP:
    - Ngắn gọn, thân thiện, trực tiếp.
    - Luôn nói rõ bước tiếp theo cần làm.
    - Không lặp lại toàn bộ câu gốc trừ khi cần minh hoạ ngắn.
    """,
    tools=[evaluate_translation, get_next_sentence],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


