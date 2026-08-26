from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.core.cache import get_cache, set_cache, delete_cache
from app.core.memory_store import (
    store_conversation as store_conversation_async,
    get_recent_conversations as get_recent_conversations_async,
    clear_session as clear_session_async,
)

router = APIRouter()

MEMORY_KEY = "conversation_memory"
MAX_SHORT_TERM = 10


class MemoryPayload(BaseModel):
    query: str
    answer: str
    confidence: int = 0
    summary: Optional[str] = None


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "memory"}


# =========================================================
# GET MEMORY
# =========================================================

@router.get("/memory/{session_id}")
async def get_memory_endpoint(session_id: str = "default_session"):
    """Get both short-term and long-term memory for a session."""
    # Short-term memory (Redis cache)
    short_term = get_cache(f"{MEMORY_KEY}:{session_id}") or []

    # Long-term memory (PostgreSQL)
    long_term = await get_recent_conversations_async(session_id, limit=50)

    return {
        "session_id": session_id,
        "short_term": short_term,
        "short_term_count": len(short_term),
        "long_term": long_term,
        "long_term_count": len(long_term),
    }


# =========================================================
# STORE MEMORY
# =========================================================

@router.post("/memory/{session_id}")
async def store_memory_endpoint(payload: MemoryPayload, session_id: str = "default_session"):
    """Store a conversation in both short-term and long-term memory."""

    # Short-term memory (Redis cache)
    memory = get_cache(f"{MEMORY_KEY}:{session_id}") or []
    memory.append({
        "query": payload.query,
        "answer": payload.answer,
        "confidence": payload.confidence,
    })
    set_cache(f"{MEMORY_KEY}:{session_id}", memory[-MAX_SHORT_TERM:])

    # Long-term memory (PostgreSQL)
    await store_conversation_async(
        session_id=session_id,
        query=payload.query,
        answer=payload.answer,
        confidence=payload.confidence,
        summary=payload.summary,
    )

    return {"message": "Memory stored", "session_id": session_id}


# =========================================================
# CLEAR MEMORY
# =========================================================

@router.delete("/memory/{session_id}")
async def clear_memory_endpoint(session_id: str = "default_session"):
    """Clear all memory for a session."""
    # Clear short-term memory
    delete_cache(f"{MEMORY_KEY}:{session_id}")

    # Clear long-term memory
    await clear_session_async(session_id)

    return {
        "message": f"Memory cleared for session: {session_id}",
        "session_id": session_id,
    }