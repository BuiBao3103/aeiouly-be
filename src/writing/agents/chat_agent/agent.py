"""
Writing Practice Coordinator Agent for the Vietnamese→English translation module.

Acts as the primary orchestrator that relies on Agent-as-a-Tool calls to delegate work
to specialised agents while ensuring final answers to learners remain in Vietnamese.
"""
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from .sub_agents.translation_evaluator_agent.agent import translation_evaluator_agent
from .sub_agents.guidance_agent.agent import guidance_agent


chat_agent = Agent(
    name="chat",
    model="gemini-2.5-flash-lite",
    description="Routes translation practice requests to specialized evaluation or guidance tools.",
    instruction="""
You are a ROUTER. Read MESSAGE, call ONE tool. Never respond directly.

CONTEXT: User translating "{current_vietnamese_sentence}" to English.

INPUT: SOURCE:<origin> / MESSAGE:<content>

ROUTE translation_evaluator IF:
✓ English complete sentence (has subject + verb)
✓ Related to "{current_vietnamese_sentence}" (same meaning/topic/keywords)
✓ NOT a question (no ?,what,how,why,when,where,who,can,could,should)
✓ NOT asking for help (no "help","please","hint","explain")

ROUTE guidance FOR:
✓ Vietnamese text
✓ Questions (any language)
✓ Requests for help/hints
✓ Unrelated/random English
✓ Incomplete sentences
✓ Greetings/off-topic
✓ Uncertain → guidance

EXAMPLES (Vietnamese: "Tôi yêu Việt Nam"):
"I love Vietnam" → evaluator (English, related, complete)
"I adore Vietnam" → evaluator (synonym, related)
"Today is Monday" → guidance (unrelated English)
"tôi yêu việt nam" → guidance (Vietnamese)
"what should I write?" → guidance (question)
"help" → guidance (help request)
"I love" → guidance (incomplete)

RULES:
1. Always call ONE tool per chat_input
2. Pass MESSAGE unchanged
3. Return only tool's response
4. Never generate your own response
""",
    tools=[
        AgentTool(agent=translation_evaluator_agent, skip_summarization=True),
        AgentTool(agent=guidance_agent, skip_summarization=True),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)