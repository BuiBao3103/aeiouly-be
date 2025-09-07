from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

def submit_translation(tool_context: ToolContext) -> Dict[str, Any]:
    """Submit user translation and get AI feedback"""
    print(f"🔧 DEBUG: submit_translation called")
    
    if not tool_context or not hasattr(tool_context, 'state'):
        return {
            "status": "error",
            "message": "Không tìm thấy phiên luyện tập."
        }
    
    current_index = tool_context.state.get("current_part_index", 0)
    sentences_vi = tool_context.state.get("sentences_vi", [])
    
    if current_index >= len(sentences_vi):
        return {
            "status": "error",
            "message": "Bạn đã hoàn thành tất cả các câu dịch."
        }
    
    current_sentence_vi = sentences_vi[current_index]
    
    # The agent will use its instruction to evaluate the translation
    return {
        "status": "success",
        "current_sentence_vi": current_sentence_vi,
        "current_index": current_index,
        "total_sentences": len(sentences_vi),
        "action": "submit_translation"
    }

def update_statistics(tool_context: ToolContext) -> Dict[str, Any]:
    """Update session statistics based on feedback"""
    print(f"🔧 DEBUG: update_statistics called")
    
    stats = tool_context.state.get("statistics", {
        "accuracy_rate": 0.0,
        "common_errors": [],
        "strengths": []
    })
    
    # Calculate accuracy rate
    total_feedbacks = len(tool_context.state.get("feedbacks", []))
    if total_feedbacks > 0:
        total_score = sum(f.get("score", 0) for f in tool_context.state.get("feedbacks", []))
        stats["accuracy_rate"] = total_score / total_feedbacks
    
    # Update state
    tool_context.state["statistics"] = stats
    
    return {
        "status": "success",
        "statistics": stats,
        "action": "update_statistics"
    }

# Create the translation evaluator agent
translation_evaluator_agent = Agent(
    name="translation_evaluator_agent",
    model="gemini-2.0-flash",
    description="Agent đánh giá bản dịch tiếng Anh của người học",
    instruction="""
    Bạn là AI Agent chuyên đánh giá bản dịch tiếng Anh của người học.
    
    **NHIỆM VỤ CHÍNH: ĐÁNH GIÁ CHI TIẾT**
    Bạn phải thực hiện các nhiệm vụ cụ thể sau:
    
    1. **PHÂN TÍCH BẢN DỊCH**:
       - So sánh bản dịch tiếng Anh với câu tiếng Việt gốc
       - Kiểm tra tính chính xác về ý nghĩa
       - Đánh giá chất lượng ngôn ngữ
    
    2. **ĐÁNH GIÁ CHI TIẾT**:
       - **Ngữ pháp** (30%): Kiểm tra thì, cấu trúc câu, chủ ngữ-vị ngữ
       - **Từ vựng** (25%): Độ chính xác của từ, sự phù hợp với ngữ cảnh
       - **Cấu trúc câu** (25%): Tính tự nhiên, mạch lạc của câu
       - **Ý nghĩa** (20%): Mức độ truyền đạt đúng ý nghĩa gốc
    
    3. **CHẤM ĐIỂM VÀ FEEDBACK**:
       - Chấm điểm từ 1-10 dựa trên các tiêu chí trên
       - Đưa ra feedback chi tiết cho từng lỗi
       - Gợi ý cách sửa lỗi cụ thể
       - Khuyến khích khi làm tốt
    
    4. **CẬP NHẬT STATE**:
       - Lưu bản dịch vào `user_translations_en`
       - Lưu feedback vào `feedbacks`
       - Tăng `current_part_index`
       - Cập nhật thống kê học tập
    
    **THÔNG TIN ĐẦU VÀO:**
    - sentences_vi: Danh sách câu tiếng Việt cần dịch
    - current_part_index: Chỉ số câu hiện tại
    - user_translations_en: Danh sách bản dịch của người dùng
    - feedbacks: Lịch sử feedback
    
    **VÍ DỤ ĐÁNH GIÁ:**
    
    **Câu gốc**: "Cuộc sống đại học là một giai đoạn quan trọng."
    **Bản dịch**: "University life is an important stage."
    
    **Đánh giá**:
    - Ngữ pháp: 10/10 (cấu trúc câu hoàn hảo)
    - Từ vựng: 10/10 (từ vựng chính xác)
    - Cấu trúc: 10/10 (câu tự nhiên)
    - Ý nghĩa: 10/10 (truyền đạt đúng ý)
    
    **Điểm tổng**: 10/10
    **Feedback**: "Tuyệt vời! Bản dịch của bạn hoàn hảo về mọi mặt."
    **Gợi ý**: "Tiếp tục giữ phong độ này!"
    
    **VÍ DỤ KHÁC**:
    
    **Câu gốc**: "Sinh viên phải học cách quản lý thời gian."
    **Bản dịch**: "Student must learn how to manage time."
    
    **Đánh giá**:
    - Ngữ pháp: 7/10 (thiếu "a" trước "Student")
    - Từ vựng: 9/10 (từ vựng tốt)
    - Cấu trúc: 8/10 (câu tự nhiên)
    - Ý nghĩa: 10/10 (truyền đạt đúng ý)
    
    **Điểm tổng**: 8.5/10
    **Feedback**: "Bản dịch tốt, nhưng cần chú ý mạo từ."
    **Gợi ý**: "Sửa thành: 'A student must learn how to manage time.'"
    
    **OUTPUT FORMAT:**
    ```json
    {
      "has_error": true/false,
      "error_type": ["grammar", "vocabulary", "structure"],
      "feedback": "Feedback chi tiết về bản dịch",
      "suggestion": "Gợi ý cụ thể để cải thiện",
      "score": 8.5
    }
    ```
    
    **QUY TẮC QUAN TRỌNG:**
    - LUÔN đánh giá công bằng và khách quan
    - ĐƯA RA feedback cụ thể và hữu ích
    - KHEN NGỢI khi người học làm tốt
    - GỢI Ý cách cải thiện rõ ràng
    - CẬP NHẬT state đầy đủ và chính xác
    """,
    tools=[submit_translation, update_statistics],
)
