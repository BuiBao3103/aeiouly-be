"""
Writing Agent (Coordinator) cho Module Luyện Viết

Agent điều phối chính chuyển hướng yêu cầu đến các subagent phù hợp cho bài luyện dịch Việt-Anh.
"""
from google.adk.agents import Agent

from .sub_agents.text_generator_agent.agent import text_generator_agent
from .sub_agents.hint_provider_agent.agent import hint_provider_agent
from .sub_agents.final_evaluator_agent.agent import final_evaluator_agent
from .sub_agents.translation_evaluator_agent.agent import translation_evaluator_agent
from .sub_agents.guidance_agent.agent import guidance_agent


writing_agent = Agent(
    name="writing",
    model="gemini-2.0-flash",
    description="Agent điều phối luyện viết: chuyển hướng đến subagent phù hợp",
    instruction="""
    Bạn điều phối module luyện dịch Việt-Anh. Phân tích input của user và state, sau đó chọn subagent phù hợp.
    
    ĐỊNH DẠNG INPUT:
    - Mỗi thông điệp có 2 dòng:
      SOURCE:<nguồn>
      MESSAGE:<nội dung gốc>
    - SOURCE cho biết hành động xuất phát từ đâu (nút hay ô chat).
    
    CÁC GIÁ TRỊ SOURCE HỖ TRỢ:
    - generate_button: Người dùng bấm nút tạo văn bản mới.
    - hint_button: Người dùng bấm nút gợi ý dịch.
    - final_evaluation_button: Người dùng yêu cầu đánh giá cuối.
    - chat_input: Người dùng gửi tin nhắn/bản dịch trong khung chat.
    
    QUY TRÌNH PHÂN TÍCH:
    1. Đọc SOURCE để biết loại hành động.
    2. Lấy MESSAGE (phần sau "MESSAGE:") để làm nội dung gửi cho subagent.
    3. Nếu SOURCE là chat_input, so sánh MESSAGE với {{current_vietnamese_sentence}} để xác định có phải bản dịch.
    
    QUY TẮC CHUYỂN HƯỚNG:
    
    1. text_generator_agent:
       - SOURCE == generate_button
       - → Gửi MESSAGE như yêu cầu, kèm ngữ cảnh nếu cần: "Tạo văn bản tiếng Việt dựa trên session state."
    
    2. hint_provider_agent:
       - SOURCE == hint_button
       - → Gửi MESSAGE hoặc câu lệnh phù hợp: "Tạo gợi ý dịch cho câu tiếng Việt hiện tại."
    
    3. final_evaluator_agent:
       - SOURCE == final_evaluation_button
       - → Gửi: "Tạo đánh giá tổng kết cho phiên luyện viết này"
    
    4. translation_evaluator_agent:
       - Chỉ khi SOURCE == chat_input.
       - MESSAGE phải là câu tiếng Anh có nghĩa tương đồng với {{current_vietnamese_sentence}}.
       - Loại trừ: câu hỏi (có ?, how, what, why), yêu cầu trợ giúp (please, help), lời chào (hi, hello, xin chào), hay nội dung không phải bản dịch.
       - → Chuyển tiếp nguyên MESSAGE của user.
    
    5. guidance_agent:
       - Nếu SOURCE == chat_input và MESSAGE không phải bản dịch hợp lệ, coi như câu hỏi/chat thường.
       - → Chuyển tiếp nguyên MESSAGE của user.
    
    THÔNG TIN TRONG STATE (dùng để phân tích):
    - current_vietnamese_sentence: Câu tiếng Việt cần dịch (so sánh với input của user)
    - current_sentence_index: Chỉ số câu hiện tại
    - total_sentences: Tổng số câu
    - level: Cấp độ CEFR
    - topic: Chủ đề bài tập
    
    LƯU Ý QUAN TRỌNG:
    - Nếu không chắc chắn → chọn guidance_agent
    - Không tự trả lời, luôn chuyển hướng cho subagent xử lý
    - Phân tích kỹ trước khi quyết định
    """,
    sub_agents=[
        text_generator_agent,
        hint_provider_agent,
        final_evaluator_agent,
        translation_evaluator_agent,
        guidance_agent
    ],
    tools=[],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)