"""
Translation Evaluator Agent for Writing Practice
"""
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
from src.constants.cefr import get_cefr_definitions_string


def save_evaluation_result(
    evaluation_result: str,
    accuracy_score: float,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Save evaluation result to session state.
    
    Args:
        evaluation_result: The evaluation result text from agent (description of evaluation)
        accuracy_score: Accuracy score (0-100) for this translation
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message
    """
    current_sentence_index = tool_context.state.get("current_sentence_index", 0)
    evaluation_history = tool_context.state.get("evaluation_history", [])
    evaluation_history.append(
        {
            "sentence_index": current_sentence_index,
            "evaluation_result": evaluation_result,
            "accuracy_score": accuracy_score,
        }
    )
    tool_context.state["evaluation_history"] = evaluation_history

    return {
        "action": "save_evaluation",
        "sentence_index": current_sentence_index,
        "accuracy_score": accuracy_score,
        "message": f"Saved evaluation for sentence {current_sentence_index + 1}",
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
    
    # Update current_vietnamese_sentence in state
    vietnamese_sentences_data = tool_context.state.get("vietnamese_sentences", {})
    if isinstance(vietnamese_sentences_data, dict) and "sentences" in vietnamese_sentences_data:
        sentences_list = vietnamese_sentences_data.get("sentences", [])
        if 0 <= next_index < len(sentences_list):
            tool_context.state["current_vietnamese_sentence"] = sentences_list[next_index]
    
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
    description="Đánh giá bản dịch tiếng Anh của người dùng, lưu kết quả và chuyển câu tiếp theo nếu đạt ≥90%",
    instruction=f"""
    Bạn là AI chuyên đánh giá bản dịch tiếng Anh của người học.

    CÂU TIẾNG VIỆT HIỆN TẠI (state current_vietnamese_sentence):
    "{{current_vietnamese_sentence}}"

    MỨC ĐỘ KHÓ (state level): {{level}}
    
    NHIỆM VỤ:
    Đánh giá bản dịch tiếng Anh của người học cho câu tiếng Việt hiện tại, xác định mức độ đúng/sai và quyết định có chuyển sang câu tiếp theo hay không.
    
    QUY TRÌNH BẮT BUỘC:
    1. Lấy câu tiếng Việt hiện tại từ state: current_vietnamese_sentence = "{{current_vietnamese_sentence}}"
    2. Phân tích bản dịch của người học so với câu tiếng Việt gốc
    3. Đánh giá theo các tiêu chí: nghĩa, ngữ pháp, từ vựng
    4. Xác định mức độ đúng (tỷ lệ phần trăm, 0-100)
    5. Tạo đánh giá chi tiết (text mô tả đánh giá)
    6. GỌI tool save_evaluation_result(evaluation_result, accuracy_score) để lưu đánh giá vào state
    7. Nếu đạt ≥ 90%:
       - BẮT ĐẦU bằng một câu khen ngắn gọn (1 câu)
       - GỌI tool get_next_sentence() để chuyển sang câu tiếp theo
       - Yêu cầu dịch câu tiếp theo (KHÔNG cần nói đó là câu gì, chỉ yêu cầu dịch câu tiếp theo)
    8. Nếu chưa đạt < 90%:
       - Chỉ ra lỗi sai cụ thể (1-3 lỗi chính)
       - Yêu cầu dịch lại câu hiện tại
       - KHÔNG gọi get_next_sentence
    
    TIÊU CHÍ ĐÁNH GIÁ (tham chiếu CEFR):
    {get_cefr_definitions_string()}
    
    CÁCH ĐÁNH GIÁ CHI TIẾT:
    - Nghĩa: So khớp với câu tiếng Việt gốc (ý chính, thông tin chính xác)
    - Ngữ pháp: Thì, mạo từ, giới từ, số ít/số nhiều, cấu trúc động từ
    - Từ vựng: Dùng từ phù hợp ngữ cảnh; chấp nhận từ đồng nghĩa hợp lý
    - Lỗi chính tả nhỏ: CHO PHÉP và KHÔNG ngăn cản nếu tổng thể đạt ≥ 90%
    
    GỢI Ý CÂU KHEN (khi đạt ≥ 90%, chọn 1 câu):
    - "Rất tốt, bản dịch của bạn khá tự nhiên!"
    - "Tuyệt vời, bạn đã truyền tải đúng ý chính!"
    - "Làm tốt lắm, ngữ pháp nhìn chung ổn định!"
    - "Nice work! Cách dùng từ rất phù hợp ngữ cảnh."
    
    VÍ DỤ PHẢN HỒI KHI ĐẠT ≥ 90%:
    "Rất tốt, bản dịch của bạn khá tự nhiên! Hãy dịch câu tiếp theo."
    
    VÍ DỤ PHẢN HỒI KHI CHƯA ĐẠT < 90%:
    "Bản dịch của bạn có một số lỗi:
    - Thiếu mạo từ 'the' trước 'world'
    - Dùng sai thì (nên dùng present simple)
    Hãy thử dịch lại câu hiện tại."
    
    QUAN TRỌNG:
    - PHẢI gọi tool save_evaluation_result() để lưu đánh giá vào state
    - Nếu đạt ≥ 90%, PHẢI gọi tool get_next_sentence() để chuyển câu
    - Khi đạt ≥ 90%, chỉ yêu cầu dịch câu tiếp theo, KHÔNG cần nói đó là câu gì
    - Khi chưa đạt, chỉ ra lỗi cụ thể và yêu cầu dịch lại
    - Đánh giá khách quan, công bằng
    - Cho phép lỗi chính tả nhỏ nếu nghĩa và ngữ pháp đúng
    
    THÔNG TIN TRONG STATE:
    - current_sentence_index: Chỉ số câu hiện tại
    - current_vietnamese_sentence: Câu tiếng Việt hiện tại cần dịch (string)
    - vietnamese_sentences: Dict chứa {{"full_text": "...", "sentences": [...]}}
    - level: CEFR level
    """,
    tools=[save_evaluation_result, get_next_sentence],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

