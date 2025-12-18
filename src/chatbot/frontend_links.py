"""
Frontend link registry for chatbot recommendations.

Centralized mapping of feature links and session links so the agent/tool
can build correct URLs without hardcoding in prompts.

BASE_URL is taken from settings.CLIENT_SIDE_URL so it can be configured
via environment variables (.env) instead of being hardcoded.
"""

from src.config import settings

BASE_URL = settings.CLIENT_SIDE_URL.rstrip("/")  # e.g. http://localhost:3000

# Static feature paths
LINKS = {
    # Learning modules
    "writing": "/writing",
    "speaking": "/speaking",
    "reading": "/reading",
    "listening": "/listening",

    # Global app pages
    "vocabulary": "/vocabulary",
    "profile": "/profile",
    "settings": "/settings",
    "home": "/app",
}

# Session-specific paths (must supply session_id)
SESSION_LINKS = {
    "writing_session": "/writing/{session_id}",
    "speaking_session": "/speaking/{session_id}",
    "reading_session": "/reading/{session_id}",
    "listening_session": "/listening/{session_id}",
}


def build_link(feature: str, session_id: int | None = None) -> str:
    """
    Build full frontend URL for a feature or session.

    Args:
        feature: one of LINKS keys or SESSION_LINKS keys
        session_id: optional, required when using session links

    Returns:
        Full URL as string.
    Raises:
        KeyError if feature not found or session_id missing when required.
    """
    if feature in LINKS:
        return f"{BASE_URL}{LINKS[feature]}"

    if feature in SESSION_LINKS:
        if session_id is None:
            raise KeyError("session_id is required for session link")
        return f"{BASE_URL}{SESSION_LINKS[feature].format(session_id=session_id)}"

    raise KeyError(f"Unknown feature '{feature}'")

