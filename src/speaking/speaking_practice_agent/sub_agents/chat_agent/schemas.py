"""
Schemas and constants for chat agent sub-agents.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChatAgentResponse(BaseModel):
    response_text: str = Field(
        description="Final message for learner (English here, Vietnamese for guidance)"
    )
    translation_sentence: Optional[str] = Field(
        default=None,
        description="Optional single Vietnamese sentence translating response_text",
    )


CHAT_RESPONSE_STATE_KEY = "chat_response"

