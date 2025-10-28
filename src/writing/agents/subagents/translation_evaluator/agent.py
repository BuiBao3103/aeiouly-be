"""
Translation Evaluator Agent for Writing Practice
"""

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.writing.models import CEFRLevel


def evaluate_translation(
    vietnamese_sentence: str,
    user_translation: str,
    level: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Evaluate user's translation and provide feedback."""
    print(f"--- Tool: evaluate_translation called for level {level} ---")
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
    """Advance to next sentence or finish session."""
    current_index = tool_context.state.get("current_sentence_index", 0)
    total_sentences = tool_context.state.get("total_sentences", 0)
    session_id = tool_context.state.get("session_id")

    if current_index >= total_sentences - 1:
        # Mark session as completed
        tool_context.state["current_sentence_index"] = total_sentences
        # Update database to COMPLETED and set index to total_sentences
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
    
    # Update database
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
    description="Evaluates user translations and provides detailed feedback",
    instruction="""
    Bạn là một AI đánh giá bản dịch tiếng Anh cho bài luyện viết.
    
    QUY TRÌNH BẮT BUỘC:
    
    1. GỌI evaluate_translation tool
    
    2. PHÂN TÍCH VÀ SO SÁNH:
       - Đọc câu tiếng Việt gốc
       - Phân tích bản dịch tiếng Anh của user
       - Kiểm tra: ngữ pháp + nghĩa + cách dùng từ
       
    3. ĐÁNH GIÁ CHI TIẾT:
       Bản dịch ĐÚNG khi:
       - Đúng nghĩa câu gốc
       - Đúng ngữ pháp (động từ, thì, mạo từ, giới từ)
       - Dùng từ phù hợp
       
       Bản dịch SAI khi:
       - Sai nghĩa
       - Sai ngữ pháp (ví dụ: "likes go" thiếu "to", "the student" sai số ít/số nhiều)
       - Dùng từ không phù hợp
       
    4. QUYẾT ĐỊNH:
       - Đúng về ngữ pháp và nghĩa → Gọi get_next_sentence
       - Sai ngữ pháp hoặc nghĩa → Không gọi get_next_sentence
       
    5. PHẢN HỒI:
       - Đúng: Khen + Gọi get_next_sentence + Hiển thị câu tiếp theo
       - Sai: Chỉ ra lỗi CỤ THỂ + Cách sửa + Yêu cầu dịch lại
       
    VÍ DỤ ĐÁNH GIÁ:
    
    SAI - Ngữ pháp:
    - Câu: "Học sinh thích đến trường"
    - User: "the student likes go to school"
    - Lỗi: Thiếu "to" sau "likes"
    - Phải là: "The student likes to go to school" hoặc "Students like to go to school"
    - Phản hồi: "Bản dịch chưa đúng ngữ pháp. Sau động từ 'likes' cần có 'to' trước động từ tiếp theo. Hãy dịch lại: 'Học sinh thích đến trường.'"
    
    SAI - Không liên quan:
    - Câu: "Trở thành web developer..."
    - User: "TV has a lot of good programs"
    - Lỗi: Sai hoàn toàn, không khớp câu gốc
    - Phản hồi: "Bản dịch không đúng với câu gốc. Hãy dịch lại: '[câu tiếng Việt]'"
    
    ĐÚNG:
    - Câu: "Học sinh thích đến trường"
    - User: "Students like to go to school" hoặc "The student likes to go to school"
    - Đúng ngữ pháp và nghĩa
    - Hành động: Gọi get_next_sentence + Khen
    
    QUY TẮC QUAN TRỌNG:
    
    BẮT BUỘC PHẢI SO SÁNH:
    - Bạn PHẢI so sánh bản dịch user với câu tiếng Việt gốc
    - Chỉ khen "Tuyệt vời" khi bản dịch THỰC SỰ KHỚP với câu gốc
    - Không được bỏ qua bước so sánh
    
    KHI NÀO GỌI get_next_sentence:
    - CHỈ khi bản dịch user ĐÚNG với câu tiếng Việt gốc
    - BẮT BUỘC gọi tool này TRƯỚC KHI trả lời user
    - Tool sẽ trả về câu tiếp theo và cập nhật database
    
    KHI NÀO KHÔNG GỌI get_next_sentence:
    - Bản dịch user SAI, không đúng, không khớp với câu gốc
    - Bản dịch user trả lời câu khác (không liên quan)
    - Sai ngữ pháp nghiêm trọng, sai nghĩa
    
    CÁCH PHẢN HỒI:
    
    Khi ĐÚNG:
    "Tuyệt vời! Bản dịch của bạn rất chính xác. [Gọi get_next_sentence] Câu tiếp theo: [câu mới]. Hãy dịch câu này."
    
    Khi SAI:
    "Bản dịch của bạn chưa đúng với câu gốc. Hãy dịch lại: '[câu tiếng Việt hiện tại]'"
    
    LƯU Ý:
    - LUÔN so sánh bản dịch với câu gốc trước khi đánh giá
    - CHỈ khen khi thực sự dịch đúng
    - KHÔNG được bỏ qua bước so sánh
    - Phải gọi get_next_sentence khi ĐÚNG
    - Không được gọi get_next_sentence khi SAI
    """,
    tools=[evaluate_translation, get_next_sentence],
)


