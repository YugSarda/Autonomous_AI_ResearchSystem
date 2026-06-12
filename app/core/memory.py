"""Memory Module - Short-term (in-memory cache) + Long-term (SQLite) memory."""
from typing import Dict, List, Optional, Any

from app.core.cache import get_cache, set_cache
from app.core.memory_store import (
    store_conversation,
    get_recent_conversations,
    get_long_term_summary,
)

MEMORY_KEY = "conversation_memory"
MAX_SHORT_TERM = 10


def get_memory(session_id: str = "default_session") -> list:
    """Get short-term memory (recent conversations for context window)."""
    return get_cache(f"{MEMORY_KEY}:{session_id}") or []


def add_memory(query: str, answer: str, session_id: str = "default_session", confidence: int = 0):
    """Add to both short-term (in-memory cache) and long-term (SQLite) memory."""
    # Short-term memory (for immediate context window)
    memory = get_memory(session_id)
    memory.append({"query": query, "answer": answer, "confidence": confidence})
    set_cache(f"{MEMORY_KEY}:{session_id}", memory[-MAX_SHORT_TERM:])

    # Long-term memory (persistent SQLite storage)
    store_conversation(
        session_id=session_id,
        query=query,
        answer=answer,
        confidence=confidence,
    )


def get_short_term_context(session_id: str = "default_session") -> str:
    """Build context string from recent conversations."""
    memory = get_memory(session_id)
    if not memory:
        return ""

    parts = []
    for item in memory[-3:]:  # Last 3 exchanges
        parts.append(f"Q: {item['query']}\nA: {item['answer'][:200]}")
    return "\n\n".join(parts)


def get_long_term_context(session_id: str = "default_session") -> str:
    """Build context string from long-term memory summary."""
    return get_long_term_summary(session_id)
