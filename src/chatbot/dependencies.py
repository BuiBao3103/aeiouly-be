"""Dependencies for Chatbot module"""
from functools import lru_cache
from src.chatbot.service import ChatbotService


@lru_cache()
def get_chatbot_service() -> ChatbotService:
    """
    Dependency to get a singleton ChatbotService instance.
    
    Use LRU cache so that all requests share the same in-memory session service,
    giúp conversation_id vẫn hợp lệ giữa các request (miễn là process còn sống).
    """
    return ChatbotService()

