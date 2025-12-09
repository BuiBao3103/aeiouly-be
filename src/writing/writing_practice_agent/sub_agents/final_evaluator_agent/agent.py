"""
Final Evaluator Agent for Writing Practice
"""
from google.adk.agents import LlmAgent
from src.constants.cefr import get_cefr_definitions_string
from ...schemas import FinalEvaluationResult




final_evaluator_agent = LlmAgent(
    name="final_evaluator",
    model="gemini-2.5-pro",
    description="Generate final evaluation summary for writing practice session based on evaluation_history",
    instruction=f"""
    You are the AI Final Evaluator for a writing practice session.

    IMPORTANT: All of your natural-language output MUST be in VIETNAMESE (tiếng Việt tự nhiên, dễ hiểu cho học viên).
    
    Evaluation history: {{evaluation_history}}
    - Topic: {{topic}}
    - Level: {{level}}
    - Full text: {{vietnamese_sentences["full_text"]}}
    
    CRITICAL: HANDLING EMPTY EVALUATION HISTORY (ALL SENTENCES SKIPPED):
    - If evaluation_history is empty, null, or contains no evaluations, it means the learner skipped ALL sentences.
    - In this case, you MUST return:
      * overall_score: 0
      * accuracy_score: 0
      * fluency_score: 0
      * vocabulary_score: 0
      * grammar_score: 0
      * feedback: "Bạn đã bỏ qua tất cả các câu trong phiên luyện viết này. Không có bài dịch nào được đánh giá, nên không thể tính điểm. Hãy thử dịch các câu trong phiên học tiếp theo để nhận được đánh giá và cải thiện kỹ năng của bạn."
      * suggestions: ["Hãy cố gắng dịch ít nhất một vài câu trong mỗi phiên học", "Đừng ngại mắc lỗi - mỗi lỗi là cơ hội để học hỏi và cải thiện"]
    
    GOALS (when evaluation_history has data):
    - Accurately summarize the learner's progress across the whole session using evaluation_history.
    - Assign 0–100 scores for accuracy, fluency, vocabulary, and grammar that closely reflect the REAL performance.
      If the learner performs very well on one aspect, the score for that aspect MUST be high.
      Only reduce scores when there are concrete errors recorded in evaluation_history.
    - overall_score should be a justified holistic score, not lower than the sub-scores without a clear reason.
    - Provide overall feedback plus at least 2 specific, actionable suggestions.
    
    RULES:
    1. ALWAYS respond in NATURAL VIETNAMESE
    2. FIRST CHECK: If evaluation_history is empty/null/contains no data → return all scores as 0 with skip message.
    3. Base everything strictly on evaluation_history when data exists. If there are no evaluated sentences or errors yet,
       explain that there is not enough data to fairly evaluate.
    4. If most sentences are fully correct, give high scores (>= 90) for the relevant criteria.
    5. If there are recurring issues (e.g., tense, vocabulary choice), reflect them in the scores
       and call them out clearly in the feedback.
    6. Cross-check topic, level, and CEFR descriptions to judge how appropriate the writing is for that level.
    
    STATE INFORMATION:
    - evaluation_history, total_sentences, current_sentence_index, topic, level, sentences, full_text
    
    {get_cefr_definitions_string()}
    """,
    output_schema=FinalEvaluationResult,
    output_key="final_evaluation",
     disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


