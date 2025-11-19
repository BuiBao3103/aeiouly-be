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
    description="Coordinates Vietnamese→English translation practice by routing requests to specialized tools.",
    instruction="""
    Orchestrate the translation practice workflow. Route requests based on SOURCE and respond in Vietnamese.
    
    INPUT: Two-line format
    SOURCE:<origin>
    MESSAGE:<content>
    
    ROUTING RULES from SOURCE:
    - chat_input → chat tool (forward full payload, don't generate own response, even if message request skip current sentence)
    - generate_button → text_generator tool (no response needed)
    - hint_button → hint_provider tool (reply in Vietnamese with hint)
    - final_evaluation_button → final_evaluator tool (summarize in Vietnamese)
    - skip_button → skip_current_sentence tool (craft Vietnamese reply with metadata)
    
    TOOL CALLS:
    - text_generator: MESSAGE = "Generate Vietnamese practice text"
    - hint_provider: MESSAGE = "Create translation hints"
    - final_evaluator: MESSAGE = "Produce final evaluation"
    - chat: Pass full two-line payload as-is, forward response
    
    
    CRITICAL: For chat_input, call chat tool immediately without generating own response.
    """,
    tools=[
        AgentTool(agent=text_generator_agent, skip_summarization=True),
        AgentTool(agent=hint_provider_agent, skip_summarization=True),
        AgentTool(agent=final_evaluator_agent, skip_summarization=True),
        skip_current_sentence
    ],
    sub_agents=[chat_agent],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)