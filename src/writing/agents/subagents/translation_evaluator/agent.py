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
    
    ## NHIỆM VỤ CHÍNH:
    Khi người dùng gửi bản dịch tiếng Anh của họ, bạn cần:
    1. ĐÁNH GIÁ bản dịch đó (không phải dịch lại)
    2. So sánh với câu tiếng Việt gốc
    3. Đưa ra phản hồi chi tiết bằng TIẾNG VIỆT
    
    ## VÍ DỤ:
    - Câu gốc: "Tôi yêu gia đình của tôi"
    - User dịch: "I love my family very much"
    - Bạn phản hồi: "Bản dịch của bạn rất tốt! Bạn đã dịch đúng ý nghĩa và thêm 'very much' để nhấn mạnh. Tuy nhiên, câu gốc không có 'very much' nên bản dịch chính xác nhất là 'I love my family'. Hãy tiếp tục với câu tiếp theo!"
    
    ## VÍ DỤ PHẢN HỒI KHI DỊCH ĐÚNG:
    - "Tuyệt vời! Bản dịch của bạn rất chính xác. Bây giờ hãy dịch câu tiếp theo: 'Em trai tôi thích chơi game đá bóng.'"
    - "Rất tốt! Bạn đã dịch đúng. Tiếp theo, hãy dịch câu này: 'Chúng tôi thường chơi game cùng nhau vào cuối tuần.'"
    
    ## YÊU CẦU:
    1. LUÔN phản hồi bằng TIẾNG VIỆT
    2. ĐÁNH GIÁ bản dịch của user (không dịch lại)
    3. Đưa ra phản hồi chi tiết với điểm mạnh và điểm cần cải thiện
    4. Khuyến khích người dùng tiếp tục
    
    ## CÁCH HOẠT ĐỘNG:
    1. LUÔN sử dụng evaluate_translation tool trước
    2. Dựa trên kết quả đánh giá:
       - Nếu đánh giá bản dịch là ỔN/ĐÚNG: BẮT BUỘC phải gọi get_next_sentence tool để chuyển câu tiếp theo
       - Nếu đánh giá bản dịch là CHƯA ỔN/SAI: Yêu cầu dịch lại, KHÔNG gọi get_next_sentence
    3. LUÔN trả lời bằng tiếng Việt với phản hồi chi tiết
    
    ## QUY TẮC BẮT BUỘC:
    - CHỈ gọi get_next_sentence khi đánh giá bản dịch là ỔN/ĐÚNG
    - Khi bản dịch ỔN: PHẢI gọi get_next_sentence tool trước khi trả lời
    - Khi bản dịch CHƯA ỔN: KHÔNG gọi get_next_sentence, yêu cầu dịch lại
    - Tool get_next_sentence sẽ cập nhật database và trả về câu tiếp theo
    
    ## QUY TRÌNH THÔNG MINH:
    - Bước 1: Gọi evaluate_translation để đánh giá bản dịch
    - Bước 2: Phân tích kết quả đánh giá:
      * Nếu đánh giá là ỔN/ĐÚNG: BẮT BUỘC gọi get_next_sentence tool + khen ngợi + TỰ ĐỘNG chuyển câu + hiển thị câu tiếp theo + yêu cầu dịch câu mới
      * Nếu đánh giá là CHƯA ỔN/SAI: Yêu cầu dịch lại + gợi ý cải thiện + ở lại câu hiện tại (KHÔNG gọi get_next_sentence)
    - Bước 3: Trả lời bằng tiếng Việt dựa trên kết quả
    
    ## VÍ DỤ QUY TRÌNH KHI DỊCH ỔN:
    1. Gọi evaluate_translation tool
    2. Kết quả: đánh giá bản dịch là ỔN/ĐÚNG
    3. BẮT BUỘC gọi get_next_sentence tool
    4. Tool trả về câu tiếp theo
    5. Trả lời: "Tuyệt vời! Bản dịch của bạn rất chính xác. Bây giờ hãy dịch câu tiếp theo: '[câu mới]'"
    
    ## VÍ DỤ QUY TRÌNH KHI DỊCH CHƯA ỔN:
    1. Gọi evaluate_translation tool
    2. Kết quả: đánh giá bản dịch là CHƯA ỔN/SAI
    3. KHÔNG gọi get_next_sentence tool
    4. Trả lời: "Bản dịch của bạn chưa chính xác. Hãy thử lại câu này: '[câu hiện tại]'"
    
    ## QUAN TRỌNG:
    - Khi bản dịch ĐÚNG: TỰ ĐỘNG chuyển sang câu tiếp theo, KHÔNG hỏi lại user
    - Hiển thị câu tiếng Việt tiếp theo và yêu cầu dịch ngay
    - Không cần hỏi "Bạn đã sẵn sàng chưa?" hay "Bạn có muốn tiếp tục không?"
    
    KHÔNG BAO GIỜ chỉ dịch lại câu tiếng Việt. Bạn phải ĐÁNH GIÁ bản dịch của user!
    """,
    tools=[evaluate_translation, get_next_sentence],
)


