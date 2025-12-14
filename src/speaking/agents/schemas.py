"""
Schemas and constants for chat agent sub-agents.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChatAgentResponse(BaseModel):
    response_text: str = Field(
        description="Final message for learner (English here, Vietnamese for guidance)"
    )

class ConversationAgentResponse(BaseModel):
    response_text: str = Field(
        description="Final message for learner (English here, Vietnamese for guidance)"
    )
    translation_sentence: Optional[str] = Field(
        default=None,
        description="Optional single Vietnamese sentence translating response_text",
    )
    is_conversation_complete: bool = Field(
        default=False,
        description="Whether the conversation is complete",
    )

