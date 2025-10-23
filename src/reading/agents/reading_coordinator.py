"""
Reading Coordinator Agent

This agent coordinates the reading practice workflow using sequential agents
with parallel evaluation for English summaries and single evaluation for Vietnamese.
"""

from google.adk.agents import ParallelAgent, SequentialAgent, LlmAgent
from .subagents.grammar_evaluator.agent import grammar_evaluator_agent
from .subagents.feedback_synthesizer.agent import feedback_synthesizer_agent
from .subagents.comprehension_evaluator.agent import comprehension_evaluator_agent
from .subagents.summary_evaluator.agent import summary_evaluation_agent

# Parallel agent for concurrent evaluation
parallel_evaluator = ParallelAgent(
    name="parallel_evaluator",
    sub_agents=[comprehension_evaluator_agent, grammar_evaluator_agent],
)

# Sequential agent for English evaluation workflow
english_evaluation_workflow = SequentialAgent(
    name="english_evaluation_workflow",
    sub_agents=[parallel_evaluator, feedback_synthesizer_agent],
)

# Main coordinator agent
reading_coordinator_agent = LlmAgent(
    name="reading_coordinator_agent",
    model="gemini-2.0-flash",
    description="Coordinates reading practice evaluation workflow",
    instruction="""
    Bạn là AI điều phối cho việc đánh giá bài tóm tắt trong luyện đọc tiếng Anh.
    
    NHIỆM VỤ:
    - Phân tích ngôn ngữ của bài tóm tắt (tiếng Việt hoặc tiếng Anh)
    - Điều phối quá trình đánh giá phù hợp với ngôn ngữ
    - Tổng hợp kết quả đánh giá
    
    QUY TRÌNH HOẠT ĐỘNG:
    
    ### Khi bài tóm tắt là TIẾNG VIỆT:
    1. Chỉ chạy comprehension evaluation (summary_evaluation_agent)
    2. Trả về kết quả đánh giá đọc hiểu
    
    ### Khi bài tóm tắt là TIẾNG ANH:
    1. Chạy english_evaluation_workflow:
       - Parallel evaluation (comprehension + grammar)
       - Feedback synthesis
    2. Trả về đánh giá toàn diện
    
    XỬ LÝ KẾT QUẢ:
    - Phân tích kết quả từ các sub-agents
    - Tổng hợp feedback phù hợp
    - Đảm bảo response format đúng
    
    QUAN TRỌNG:
    - Luôn phân tích ngôn ngữ trước khi chọn workflow
    - Sử dụng english_evaluation_workflow cho tiếng Anh
    - Sử dụng summary_evaluation_agent cho tiếng Việt
    - Tổng hợp kết quả một cách logic và hữu ích
    """,
    sub_agents=[english_evaluation_workflow, summary_evaluation_agent],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
