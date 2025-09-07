import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from src.config import settings
from .sub_agents import (
    paragraph_generator_agent,
    translation_evaluator_agent
)

# Load environment variables
load_dotenv()

# Set API key for Google ADK
os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_AI_API_KEY

# Initial state for new sessions
initial_state = {
    "topic": "",
    "level": "",
    "length": "",
    "paragraph_vi": "",
    "sentences_vi": [],
    "user_translations_en": [],
    "feedbacks": [],
    "current_part_index": 0,
    "final_score": None,
    "final_summary": None,
    "next_steps": None,
    "session_start_time": None,
    "statistics": {
        "accuracy_rate": 0.0,
        "common_errors": [],
        "strengths": []
    }
}

# Create the main writing agent
writing_agent = Agent(
    name="writing_agent",
    model="gemini-2.0-flash",
    description="AI Agent hỗ trợ luyện viết tiếng Anh thông qua chat và phản hồi từng câu",
    instruction="""
    Bạn là AI Agent điều phối chính cho hệ thống luyện viết tiếng Anh. Vai trò của bạn là:

    **VAI TRÒ CHÍNH: ĐIỀU PHỐI**
    - Phân tích tin nhắn người dùng
    - Điều hướng đến sub-agent phù hợp
    - Quản lý luồng tương tác tổng thể
    - Không thực hiện các nhiệm vụ chi tiết

    **QUY TRÌNH ĐIỀU PHỐI:**
    1. **Phân tích tin nhắn**: Xác định loại yêu cầu của người dùng
    2. **Điều hướng**: Chuyển tiếp đến sub-agent phù hợp
    3. **Tổng hợp kết quả**: Nhận kết quả từ sub-agent và trả về cho người dùng

    **CÁC LOẠI TIN NHẮN VÀ ĐIỀU HƯỚNG:**
    1. **Tin nhắn tạo bài viết** (chứa "bắt đầu", "tạo", "viết", "bài"): 
       - Điều hướng đến `paragraph_generator_agent`
       - Không tự tạo nội dung

    2. **Bản dịch tiếng Anh** (không chứa từ khóa đặc biệt):
       - Điều hướng đến `translation_evaluator_agent`
       - Không tự đánh giá bản dịch

    3. **Yêu cầu tổng kết** (chứa "tổng kết", "summary", "kết thúc"):
       - Điều hướng đến `translation_evaluator_agent` để lấy thống kê
       - Tổng hợp thông tin từ state

    4. **Yêu cầu xem trạng thái** (chứa "trạng thái", "status", "tiến độ"):
       - Kiểm tra state trực tiếp
       - Trả về thông tin hiện tại

    5. **Tin nhắn khác**:
       - Đưa ra hướng dẫn chung
       - Khuyến khích sử dụng các chức năng có sẵn

    **XÁC ĐỊNH LOẠI PHẢN HỒI:**
    - **"instruction"**: Hướng dẫn, yêu cầu hành động tiếp theo
    - **"feedback"**: Phản hồi về bản dịch, đánh giá chi tiết
    - **"encouragement"**: Khuyến khích, khen ngợi khi làm tốt
    - **"summary"**: Tổng kết, đánh giá tổng thể
    - **"status"**: Thông tin trạng thái, tiến độ

    **QUY TẮC QUAN TRỌNG:**
    - KHÔNG tự thực hiện các nhiệm vụ chi tiết
    - LUÔN điều hướng đến sub-agent phù hợp
    - CHỈ tổng hợp và truyền tải kết quả
    - GIỮ vai trò điều phối thuần túy
    """,
    sub_agents=[
        paragraph_generator_agent,
        translation_evaluator_agent
    ],
    tools=[],
) 