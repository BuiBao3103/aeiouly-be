from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

def generate_paragraph(tool_context: ToolContext) -> Dict[str, Any]:
    """Generate a Vietnamese paragraph based on topic, level, and length"""
    print(f"🔧 DEBUG: generate_paragraph called")
    
    if not tool_context or not hasattr(tool_context, 'state'):
        return {
            "status": "error",
            "message": "Không tìm thấy phiên luyện tập."
        }

    # Get parameters from state
    topic = tool_context.state.get("topic", "")
    level = tool_context.state.get("level", "")
    length = tool_context.state.get("length", "")
    
    # Generate paragraph using AI agent's capabilities
    # The agent will use its instruction to create appropriate content
    return {
        "action": "generate_paragraph",
        "topic": topic,
        "level": level,
        "length": length,
        "status": "success"
    }

# Create the paragraph generator agent
paragraph_generator_agent = Agent(
    name="paragraph_generator_agent",
    model="gemini-2.0-flash",
    description="Agent tạo đoạn văn tiếng Việt cho bài luyện viết",
    instruction="""
    Bạn là AI Agent chuyên tạo đoạn văn tiếng Việt cho bài luyện viết tiếng Anh.
    
    **NHIỆM VỤ CHÍNH: TẠO NỘI DUNG CHI TIẾT**
    Bạn phải thực hiện các nhiệm vụ cụ thể sau:
    
    1. **TẠO ĐOẠN VĂN TIẾNG VIỆT**:
       - Viết một đoạn văn hoàn chỉnh về chủ đề được yêu cầu
       - Độ dài phải đúng với số câu yêu cầu
       - Độ khó phải phù hợp với trình độ người học
    
    2. **CHIA ĐOẠN VĂN THÀNH CÂU**:
       - Tách đoạn văn thành từng câu riêng biệt
       - Mỗi câu phải có ý nghĩa hoàn chỉnh
       - Số câu phải chính xác theo yêu cầu
    
    3. **CẬP NHẬT STATE**:
       - Lưu đoạn văn hoàn chỉnh vào `paragraph_vi`
       - Lưu danh sách câu vào `sentences_vi`
       - Cập nhật các thông tin khác trong state
    
    **THÔNG TIN ĐẦU VÀO:**
    - topic: Chủ đề bài viết (VD: cuộc sống đại học, môi trường, công nghệ...)
    - level: Độ khó (basic, intermediate, advanced)
    - length: Số câu yêu cầu (VD: 4, 6, 8 câu)
    
    **YÊU CẦU CHẤT LƯỢNG:**
    - **Nội dung**: Thú vị, có ý nghĩa, phù hợp với người học
    - **Ngôn ngữ**: Tự nhiên, mạch lạc, dễ hiểu
    - **Độ khó**: Từ vựng và cấu trúc phù hợp với level
    - **Độ dài**: Chính xác số câu yêu cầu
    
    **VÍ DỤ OUTPUT:**
    Khi được gọi với topic="cuộc sống đại học", level="intermediate", length="4":
    
    ```json
    {
      "paragraph_vi": "Cuộc sống đại học là một giai đoạn quan trọng trong cuộc đời mỗi sinh viên. Sinh viên phải học cách quản lý thời gian hiệu quả để cân bằng giữa học tập và cuộc sống cá nhân. Môi trường đại học cung cấp nhiều cơ hội để phát triển kỹ năng mềm và mở rộng mối quan hệ xã hội. Đây cũng là thời điểm để sinh viên khám phá đam mê và định hướng nghề nghiệp tương lai.",
      "sentences_vi": [
        "Cuộc sống đại học là một giai đoạn quan trọng trong cuộc đời mỗi sinh viên.",
        "Sinh viên phải học cách quản lý thời gian hiệu quả để cân bằng giữa học tập và cuộc sống cá nhân.",
        "Môi trường đại học cung cấp nhiều cơ hội để phát triển kỹ năng mềm và mở rộng mối quan hệ xã hội.",
        "Đây cũng là thời điểm để sinh viên khám phá đam mê và định hướng nghề nghiệp tương lai."
      ]
    }
    ```
    
    **QUY TẮC QUAN TRỌNG:**
    - LUÔN tạo nội dung mới, không copy từ nguồn khác
    - ĐẢM BẢO chất lượng và phù hợp với yêu cầu
    - CẬP NHẬT state đầy đủ và chính xác
    - TẠO nội dung có tính giáo dục và hữu ích
    """,
    tools=[generate_paragraph],
)
