"""
Translation Evaluator Agent for Writing Practice
"""
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


def evaluate_translation(
    vietnamese_sentence: str,
    user_translation: str,
    level: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Save translation evaluation to session state.
    
    Args:
        vietnamese_sentence: The Vietnamese sentence being translated
        user_translation: The user's English translation
        level: CEFR level for evaluation
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message
    """
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
    """Move to the next sentence in the writing session.
    
    Args:
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message with next sentence information
    """
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


translation_evaluator_agent = Agent(
    name="translation_evaluator",
    model="gemini-2.0-flash",
    description="Evaluates user's English translation of Vietnamese sentences",
    instruction=f"""
    Bạn là AI chuyên đánh giá bản dịch tiếng Anh của người học.
    
    NHIỆM VỤ:
    Đánh giá bản dịch tiếng Anh của người học cho câu tiếng Việt hiện tại, xác định mức độ đúng/sai và quyết định có chuyển sang câu tiếp theo hay không.
    
    QUY TRÌNH BẮT BUỘC:
    1. Phân tích bản dịch của người học so với câu tiếng Việt gốc (lấy từ state: vietnamese_sentences["sentences"][current_sentence_index])
    2. Đánh giá theo các tiêu chí: nghĩa, ngữ pháp, từ vựng
    3. Xác định mức độ đúng (tỷ lệ phần trăm)
    4. GỌI tool evaluate_translation(vietnamese_sentence, user_translation, level) để lưu kết quả đánh giá vào state
    5. Nếu đạt ≥ 90%:
       - BẮT ĐẦU bằng một câu khen ngắn gọn (1 câu)
       - GỌI tool get_next_sentence() để chuyển sang câu tiếp theo
       - Hiển thị câu tiếp theo (lấy từ state: vietnamese_sentences["sentences"][next_index])
       - Yêu cầu dịch câu mới
    6. Nếu chưa đạt < 90%:
       - Trả về đánh giá chi tiết với các lỗi cụ thể
       - Không gọi get_next_sentence
    
    TIÊU CHÍ ĐÁNH GIÁ (tham chiếu CEFR):
    {get_cefr_definitions_string()}
    
    CÁCH ĐÁNH GIÁ CHI TIẾT:
    - Nghĩa: So khớp với câu tiếng Việt gốc (ý chính, thông tin chính xác)
    - Ngữ pháp: Thì, mạo từ, giới từ, số ít/số nhiều, cấu trúc động từ
    - Từ vựng: Dùng từ phù hợp ngữ cảnh; chấp nhận từ đồng nghĩa hợp lý
    - Lỗi chính tả nhỏ: CHO PHÉP và KHÔNG ngăn cản nếu tổng thể đạt ≥ 90%
    
    OUTPUT FORMAT:
    - Đánh giá tổng quan: Đúng/Chưa đúng, tỷ lệ phần trăm
    - Chi tiết: Liệt kê các điểm đúng và các lỗi (nếu có)
    - Kết luận: Đạt ≥ 90% hay chưa đạt
    
    GỢI Ý CÂU KHEN (khi đạt ≥ 90%):
    - "Rất tốt, bản dịch của bạn khá tự nhiên!"
    - "Tuyệt vời, bạn đã truyền tải đúng ý chính!"
    - "Làm tốt lắm, ngữ pháp nhìn chung ổn định!"
    - "Nice work! Cách dùng từ rất phù hợp ngữ cảnh."
    
    QUAN TRỌNG:
    - PHẢI gọi tool evaluate_translation() trước khi kết thúc
    - Nếu đạt ≥ 90%, PHẢI gọi tool get_next_sentence() để chuyển câu
    - Đánh giá khách quan, công bằng
    - Cho phép lỗi chính tả nhỏ nếu nghĩa và ngữ pháp đúng
    
    THÔNG TIN TRONG STATE:
    - current_sentence_index: Chỉ số câu hiện tại
    - vietnamese_sentences: Dict chứa {{"full_text": "...", "sentences": [...]}}
    - level: CEFR level
    """,
    tools=[evaluate_translation, get_next_sentence],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

