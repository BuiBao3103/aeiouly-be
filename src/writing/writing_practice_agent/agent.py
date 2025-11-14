"""
Writing Practice Coordinator Agent for the Vietnamese→English translation module.

Acts as the primary orchestrator that relies on Agent-as-a-Tool calls to delegate work
to specialised agents while ensuring final answers to learners remain in Vietnamese.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

from .sub_agents.text_generator_agent.agent import text_generator_agent
from .sub_agents.hint_provider_agent.agent import hint_provider_agent
from .sub_agents.final_evaluator_agent.agent import final_evaluator_agent
from .sub_agents.chat_agent.agent import chat_agent
from src.writing.service import WritingService


def skip_current_sentence(tool_context: ToolContext) -> Dict[str, Any]:
    """Skip current sentence and move to next one.
    
    Args:
        tool_context: Context for accessing and updating session state
        
    Returns:
        A confirmation message with next sentence information
    """
    current_index = tool_context.state.get("current_sentence_index", 0)
    total_sentences = tool_context.state.get("total_sentences", 0)
    session_id = tool_context.state.get("session_id")

    if current_index >= total_sentences - 1:
        # Complete the session
        tool_context.state["current_sentence_index"] = total_sentences
        tool_context.state["current_vietnamese_sentence"] = None
        if session_id:
            persisted = WritingService.persist_skip_progress_to_db(
                session_id=session_id,
                next_index=total_sentences,
                total_sentences=total_sentences,
            )
            if not persisted:
                print(f"Could not persist skip completion for session {session_id}")
        completion_message = "Đã bỏ qua câu cuối cùng. Phiên học kết thúc! Bạn có thể xem phần đánh giá tổng kết khi sẵn sàng."
        return {
            "action": "session_complete",
            "message": completion_message,
            "current_index": total_sentences,
            "total_sentences": total_sentences,
            "next_sentence": None,
        }

    next_index = current_index + 1
    tool_context.state["current_sentence_index"] = next_index
    
    # Update current_vietnamese_sentence in state
    vietnamese_sentences_data = tool_context.state.get("vietnamese_sentences", {})
    if isinstance(vietnamese_sentences_data, dict) and "sentences" in vietnamese_sentences_data:
        sentences_list = vietnamese_sentences_data.get("sentences", [])
        if 0 <= next_index < len(sentences_list):
            tool_context.state["current_vietnamese_sentence"] = sentences_list[next_index]
        else:
            tool_context.state["current_vietnamese_sentence"] = None
    
    next_sentence_text = tool_context.state.get("current_vietnamese_sentence")

    if session_id:
        persisted = WritingService.persist_skip_progress_to_db(
            session_id=session_id,
            next_index=next_index,
            total_sentences=total_sentences,
        )
        if not persisted:
            print(f"Could not persist skip progress for session {session_id}")

    return {
        "action": "skip_sentence",
        "skipped_index": current_index,
        "current_index": next_index,
        "total_sentences": total_sentences,
        "next_sentence": next_sentence_text,
    }


writing_practice = Agent(
    name="writing_practice",
    model="gemini-2.0-flash",
    description="Coordinates the writing practice workflow, delegating work to specialised tools while replying to learners in Vietnamese.",
    instruction="""
    You orchestrate the Vietnamese→English translation practice module. Analyse each request and select the correct tool.
    When you speak to the learner, ALWAYS respond in natural, supportive Vietnamese.
    
    INPUT FORMAT:
    - Every message arrives as two lines:
      SOURCE:<origin>
      MESSAGE:<raw content>
    - SOURCE indicates which UI element triggered the request (button vs. chat box).
    
    SUPPORTED SOURCE VALUES:
    - generate_button: learner pressed the “generate text” button.
    - hint_button: learner pressed the “hint” button.
    - final_evaluation_button: learner requested the final evaluation.
    - chat_input: learner typed directly into the chat box.
    - skip_button: learner asked to skip the current sentence.
    
    DECISION PROCESS:
    1. Read SOURCE to understand the context.
    2. Use the MESSAGE line (text after “MESSAGE:”) as the payload for the tool.
    3. If SOURCE == chat_input, call the chat_agent tool to classify the message.
    
    TOOL USAGE RULES:
    1. text_generator tool:
       - Trigger: SOURCE == generate_button
       - Call with MESSAGE = "Generate the Vietnamese practice text based on the current session state."
       - IMPORTANT: Do NOT generate any greeting or introductory message before or after calling this tool.
       - The tool will generate the text silently and store it in state. No user-facing response is needed.
    
    2. hint_provider tool:
       - Trigger: SOURCE == hint_button
       - Call with MESSAGE = "Create translation hints for the current Vietnamese sentence."
       - After receiving tool output, reply to the learner in clear Vietnamese with the hint.
    
    3. final_evaluator tool:
       - Trigger: SOURCE == final_evaluation_button
       - Call with MESSAGE = "Produce the final evaluation summary for this session."
       - After receiving tool output, summarise and reply to the learner in clear Vietnamese.
    
    4. chat_agent tool:
       - Trigger: SOURCE == chat_input
       - Pass the full two-line payload exactly as received (both SOURCE and MESSAGE lines).
       - The chat_agent tool will determine whether the learner sent a translation or needs guidance.
       - After receiving tool output, reply to the learner in clear Vietnamese.
    
    5. skip_current_sentence tool:
       - Trigger: SOURCE == skip_button OR MESSAGE explicitly asks to skip the sentence
       - Call the tool without modification to advance to the next sentence.
       - The tool returns metadata (skipped_index, current_index, next_sentence). Use that information to craft a natural Vietnamese reply.
       - Tell the learner the skip is done and encourage them to translate the new sentence, quoting it if available.
    
    STATE INFORMATION AVAILABLE:
    - current_vietnamese_sentence: the sentence the learner must translate.
    - current_sentence_index: current sentence position.
    - total_sentences: number of sentences in the exercise.
    - level: CEFR difficulty level.
    - topic: practice topic.
    
    IMPORTANT:
    - Always use tools; do not craft answers without tool output.
    - Study SOURCE and MESSAGE carefully before choosing a tool.
    - For generate_button: Call the tool and do NOT generate any response text. The text generation is handled silently.
    - For other sources: After receiving tool output, summarise and reply to the learner in clear Vietnamese.
    """,
    sub_agents=[chat_agent],  # chat_agent remains as a sub-agent to handle routing logic for chat messages
    tools=[
        AgentTool(agent=text_generator_agent, skip_summarization=True),
        AgentTool(agent=hint_provider_agent, skip_summarization=True),
        AgentTool(agent=final_evaluator_agent, skip_summarization=True),
        skip_current_sentence
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)