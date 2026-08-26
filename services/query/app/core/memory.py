"""Memory Module - Calls Memory Service via HTTP (async, for LangGraph compatibility)."""
import httpx
from typing import Optional
from app.core.config import MEMORY_SERVICE_URL

MEMORY_KEY = "conversation_memory"
MAX_SHORT_TERM = 10

_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create the global HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def close_http_client():
    """Close the global HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


async def get_memory(session_id: str = "default_session") -> list:
    """Get short-term memory from Memory Service (async)."""
    try:
        client = get_http_client()
        resp = await client.get(f"{MEMORY_SERVICE_URL}/memory/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("short_term", [])
    except Exception as e:
        print(f"⚠️ Memory service call failed: {e}")
    return []


async def add_memory(query: str, answer: str, session_id: str = "default_session", confidence: int = 0):
    """Store conversation in Memory Service (async)."""
    try:
        client = get_http_client()
        await client.post(
            f"{MEMORY_SERVICE_URL}/memory/{session_id}",
            json={
                "query": query,
                "answer": answer,
                "confidence": confidence,
            },
        )
    except Exception as e:
        print(f"⚠️ Failed to store memory: {e}")


async def get_short_term_context(session_id: str = "default_session") -> str:
    """Build context string from recent conversations."""
    memory = await get_memory(session_id)
    if not memory:
        return ""

    parts = []
    for item in memory[-3:]:  # Last 3 exchanges
        parts.append(f"Q: {item['query']}\nA: {item['answer'][:200]}")
    return "\n\n".join(parts)


async def get_long_term_context(session_id: str = "default_session") -> str:
    """Get long-term memory context from Memory Service (async)."""
    try:
        client = get_http_client()
        resp = await client.get(f"{MEMORY_SERVICE_URL}/memory/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            long_term = data.get("long_term", [])
            if not long_term:
                return ""
            parts = []
            for item in long_term[-5:]:  # Last 5 long-term items
                parts.append(f"Q: {item['query']}\nA: {item['answer'][:200]}")
            return "\n\n".join(parts)
    except Exception as e:
        print(f"⚠️ Failed to get long-term context: {e}")
    return ""