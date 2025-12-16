"""
Text Reviewer Agent

This agent reviews reading texts for word count compliance and provides feedback.
"""

from google.adk.agents.llm_agent import LlmAgent

from .tools import count_words, exit_loop

# Constants
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Use faster model for reviewer


# Define the Text Reviewer Agent
text_reviewer_agent = LlmAgent(
    name="text_reviewer_agent",
    model=GEMINI_MODEL,
    instruction="""You are a Reading Text Quality Reviewer.

    Your task is to evaluate ONLY the word count of a generated reading text.
    
    ## REQUIRED VALUE FROM STATE
    - Target word count: {target_word_count}
    
    ## EVALUATION PROCESS
    
    1. Use the count_words tool to check word count.
       Pass the current text content directly to the tool.
       The tool will check if the word count is within ±20% of the target word count.
    
    2. If the word count check fails (tool result is "fail"), provide specific feedback on what needs to be fixed.
       Use the tool's message as a guideline, but add your own professional critique.
       Return the feedback in Vietnamese.
    
    3. If word count check passes, the text meets the length requirement.
    
    ## OUTPUT INSTRUCTIONS
    IF the word count check fails (tool result is "fail"):
      - Return concise, specific feedback in Vietnamese on what to improve
      - Use the information from the count_words tool result to provide specific numbers
      - Example format: "Bài đọc hiện tại có X từ, cần thêm khoảng Y từ để đạt yêu cầu tối thiểu Z từ (mục tiêu: T ±20%)."
      - Or if too long: "Bài đọc hiện tại có X từ, cần bớt khoảng Y từ để đạt yêu cầu tối đa Z từ (mục tiêu: T ±20%)."
      
    ELSE IF the text meets the word count requirement:
      - Call the exit_loop function
      - Return "Bài đọc đã đạt yêu cầu về độ dài. Kết thúc quá trình tinh chỉnh."
      
    Do not embellish your response. Either provide feedback on what to improve OR call exit_loop and return the completion message.
    
    ## TEXT TO REVIEW
    {current_text}
    """,
    description="Reviews text word count and provides feedback on what to improve or exits the loop if word count requirement is met (±20%)",
    tools=[count_words, exit_loop],
    output_key="review_feedback",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

