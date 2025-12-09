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
from .sub_agents.translation_evaluator_agent.agent import translation_evaluator_agent
from .sub_agents.guidance_agent.agent import guidance_agent
from src.writing.service import WritingService

import random


def skip_current_sentence(tool_context: ToolContext) -> Dict[str, Any]:
    """Skip current sentence and move to next one."""
    current_index = tool_context.state.get("current_sentence_index", 0)
    total_sentences = tool_context.state.get("total_sentences", 0)
    session_id = tool_context.state.get("session_id")

    # Check if this is the last sentence
    if current_index >= total_sentences - 1:
        tool_context.state["current_sentence_index"] = total_sentences
        tool_context.state["current_vietnamese_sentence"] = "Tất cả các câu đã được dịch xong. Phiên học hoàn thành!"

        if session_id:
            WritingService.persist_skip_progress_to_db(
                session_id, total_sentences, total_sentences)
            WritingService.create_skip_assistant_message(
                session_id, "Đã bỏ qua câu cuối cùng. Phiên học kết thúc!", total_sentences)

        return {
            "action": "session_complete",
            "message": "Đã bỏ qua câu cuối cùng. Phiên học kết thúc! Bạn có thể xem phần đánh giá tổng kết khi sẵn sàng.",
            "current_index": total_sentences,
            "total_sentences": total_sentences,
            "next_sentence": None,
        }

    # Move to next sentence
    next_index = current_index + 1
    tool_context.state["current_sentence_index"] = next_index

    # Get next sentence
    vietnamese_data = tool_context.state.get("vietnamese_sentences", {})
    sentences = vietnamese_data.get("sentences", [])
    next_sentence = sentences[next_index] if next_index < len(
        sentences) else None
    tool_context.state["current_vietnamese_sentence"] = next_sentence

    # Generate translation request message
    if next_sentence:
        templates = [
            f"Hãy dịch câu sau: \"{next_sentence}\"",
            f"Dịch câu này sang tiếng Anh: \"{next_sentence}\"",
            f"Hãy thử dịch câu: \"{next_sentence}\"",
            f"Câu tiếp theo cần dịch là: \"{next_sentence}\"",
            f"Hãy dịch câu \"{next_sentence}\" sang tiếng Anh nhé!",
            f"Dịch câu này: \"{next_sentence}\"",
            f"Hãy dịch câu \"{next_sentence}\"",
            f"Dịch câu sau sang tiếng Anh: \"{next_sentence}\"",
            f"Câu tiếp theo: \"{next_sentence}\". Hãy dịch nó nhé!",
        ]
        translation_message = random.choice(templates)
    else:
        translation_message = "Hãy dịch câu tiếp theo."

    # Persist to database
    if session_id:
        WritingService.persist_skip_progress_to_db(
            session_id, next_index, total_sentences)
        WritingService.create_skip_assistant_message(
            session_id, translation_message, next_index)

    return {
        "action": "skip_sentence",
        "skipped_index": current_index,
        "current_index": next_index,
        "total_sentences": total_sentences,
        "next_sentence": next_sentence,
    }


writing_practice = Agent(
    name="writing_practice",
    model="gemini-2.5-flash-lite",
    description="Coordinates Vietnamese→English translation practice by routing requests to specialized tools.",
    instruction="""
    You are the primary coordinator for the writing practice flow. All final learner-facing replies must be in Vietnamese.

    INPUT FORMAT (always 2 lines):
    SOURCE:<origin>
    MESSAGE:<content>

    ROUTING BY SOURCE:
    - chat_input: classify MESSAGE
        • If MESSAGE is an English translation of "{current_vietnamese_sentence}" → call translation_evaluator tool (pass MESSAGE verbatim).
        • Otherwise (questions, greetings, unsure, off-topic, hint/skip requests, etc.) → call guidance tool (pass MESSAGE verbatim).
    - generate_button → text_generator tool
    - hint_button → hint_provider tool
    - final_evaluation_button → final_evaluator tool
    - skip_button → skip_current_sentence tool

    RULES:
    - Always check SOURCE to choose the correct tool.
    - For chat_input: you must call guidance or translation_evaluator; never answer directly.
    - For other SOURCE values: only call the mapped tool; do not add extra text.
    - After a tool returns, forward the result to the learner in Vietnamese (if the tool already responded in Vietnamese, reuse it as-is).
    """,
    tools=[
        AgentTool(agent=text_generator_agent, skip_summarization=True),
        AgentTool(agent=hint_provider_agent, skip_summarization=True),
        AgentTool(agent=final_evaluator_agent, skip_summarization=True),
        AgentTool(agent=translation_evaluator_agent, skip_summarization=True),
        AgentTool(agent=guidance_agent, skip_summarization=True),
        skip_current_sentence,
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)
