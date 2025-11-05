"""
Analyze Answer Agent

This agent coordinates the answer evaluation workflow based on the language of the user's answer.
- Vietnamese: content_evaluator_vn (SequentialAgent: content -> feedback_synthesizer)
- English: content_evaluator_en (SequentialAgent: ParallelAgent(content + grammar) -> feedback_synthesizer)
"""

from google.adk.agents import LlmAgent
from .subagents.content_evaluator_en.agent import content_evaluator_en
from .subagents.content_evaluator_vn.agent import content_evaluator_vn

# Main coordinator agent
analyze_answer_agent = LlmAgent(
    name="analyze_answer_agent",
    model="gemini-2.0-flash",
    description="Coordinates answer evaluation workflow based on answer language",
    instruction="""
    Bạn là AI điều phối cho việc đánh giá câu trả lời thảo luận trong luyện đọc tiếng Anh.
    
    NHIỆM VỤ:
    - Phân tích ngôn ngữ của câu trả lời (tiếng Việt hoặc tiếng Anh)
    - Điều phối quá trình đánh giá phù hợp với ngôn ngữ
    - Tổng hợp kết quả đánh giá
    
    QUY TRÌNH HOẠT ĐỘNG:
    
    ### Khi câu trả lời là TIẾNG VIỆT:
    1. Chuyển đến content_evaluator_vn:
       - Content evaluation (đánh giá nội dung câu trả lời có đúng không)
       - Feedback synthesis (tổng hợp feedback)
    2. Trả về kết quả đánh giá
    
    ### Khi câu trả lời là TIẾNG ANH:
    1. Chuyển đến content_evaluator_en:
       - Parallel evaluation (content + grammar cùng lúc)
       - Feedback synthesis (tổng hợp feedback từ cả hai)
    2. Trả về đánh giá toàn diện
    
    XỬ LÝ KẾT QUẢ:
    - Phân tích kết quả từ các sub-agents
    - Tổng hợp feedback phù hợp
    - Đảm bảo response format đúng
    
    OUTPUT FORMAT:
    Trả về JSON với cấu trúc:
    {
      "score": điểm_tổng_thể,
      "feedback": "feedback toàn diện..."
    }
    
    QUAN TRỌNG:
    - Luôn phân tích ngôn ngữ của câu trả lời trước khi chọn agent
    - Sử dụng content_evaluator_en cho tiếng Anh
    - Sử dụng content_evaluator_vn cho tiếng Việt
    - Tổng hợp kết quả một cách logic và hữu ích
    - Trả về JSON format
    """,
    sub_agents=[content_evaluator_vn, content_evaluator_en],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

