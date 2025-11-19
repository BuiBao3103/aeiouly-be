"""
Chat coordination agent for the writing practice module.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .sub_agents.translation_evaluator_agent.agent import translation_evaluator_agent
from .sub_agents.guidance_agent.agent import guidance_agent


chat_agent = Agent(
    name="chat",
    model="gemini-2.0-flash",
    description="Routes chat box messages to the correct tool while ensuring answers stay in Vietnamese.",
    instruction="""
    You coordinate messages coming from the learner's chat box.
    You MUST ALWAYS call a tool first. NEVER respond directly without calling a tool.

    INPUT FORMAT:
    - Every chat message arrives as two lines:
      SOURCE:chat_input
      MESSAGE:<learner text>

    TASK:
    - Decide whether MESSAGE is an English translation attempt of "{current_vietnamese_sentence}".
    - If it is a translation attempt → call the translation_evaluator tool.
    - Otherwise → call the guidance tool.

    HOW TO RECOGNISE A TRANSLATION:
    - MESSAGE is a well-formed English sentence or paragraph.
    - Content addresses the meaning of {current_vietnamese_sentence}.
    - It does NOT contain question marks or phrases like how/what/why/please/help.
    - It is not a greeting, complaint, or generic request for assistance.
    - It is not a question in Vietnamese (e.g., "bạn là ai?", "làm thế nào?", etc.).

    TOOL RULES:
    1. translation_evaluator tool:
       - Use when MESSAGE qualifies as a translation attempt.
       - Pass MESSAGE verbatim.

    2. guidance tool:
       - Use when MESSAGE is not a translation (questions, requests for help, unrelated chat, greetings, etc.).
       - Use when MESSAGE is in Vietnamese and not an English translation.
       - Pass MESSAGE verbatim.

    STATE INFORMATION AVAILABLE:
    - current_vietnamese_sentence: sentence the learner must translate.
    - current_sentence_index: position of the sentence in the exercise.

    RESPONSE RULES:
    - You MUST call a tool first. Do NOT generate your own response.
    - After the tool returns a result, forward that result to the learner.
    - If the tool output is already in Vietnamese, use it as-is.
    - If the tool output is in English, translate it to Vietnamese before sending.
    - Your final response to the learner MUST be in Vietnamese.

    IMPORTANT:
    - If unsure whether it's a translation, default to the guidance tool.
    - NEVER answer questions or provide guidance yourself - always use the guidance tool.
    - NEVER evaluate translations yourself - always use the translation_evaluator tool.
    """,
    tools=[
        AgentTool(agent=translation_evaluator_agent, skip_summarization=False),
        AgentTool(agent=guidance_agent, skip_summarization=False),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

