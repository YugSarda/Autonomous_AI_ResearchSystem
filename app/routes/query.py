from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import time

from app.services.agent_orchestrator import run_agents
from app.core.ollama_client import stream_generate
import app.core.state as state
from app.core.memory import get_memory, add_memory
from app.core.memory_store import get_recent_conversations, clear_session
from app.core.cache import get_cache, set_cache
from app.services.prometheus_metrics import (
    total_queries,
    avg_response_time,
    cache_hits,
    cache_misses,
)

router = APIRouter()


# =========================================================
# NORMAL QUERY ENDPOINT
# =========================================================

@router.post("/query")
async def query_api(q: str):

    print("\n" + "=" * 60)
    print("🔥 /query endpoint HIT")
    print("=" * 60)

    total_queries.labels(endpoint="/query").inc()
    query_start = time.time()

    # -----------------------------------------------------
    # CHECK RETRIEVER
    # -----------------------------------------------------

    if state.retriever is None:

        return {
            "error": "No documents uploaded yet"
        }

    print("✅ Retriever found")

    # -----------------------------------------------------
    # CHECK REDIS CACHE (same query from any user)
    # -----------------------------------------------------

    cache_key = f"query:{q.strip().lower()}"
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        print("✅ Cache HIT for query")
        cache_hits.labels(endpoint="/query").inc()
        elapsed = time.time() - query_start
        avg_response_time.observe(elapsed)
        return cached_result

    cache_misses.labels(endpoint="/query").inc()
    print("ℹ️ Cache MISS, running full pipeline")

    # -----------------------------------------------------
    # RUN AGENT PIPELINE
    # -----------------------------------------------------

    result = await run_agents(
        q,
        state.retriever
    )

    # -----------------------------------------------------
    # STORE IN CACHE
    # -----------------------------------------------------

    set_cache(cache_key, result)

    print("✅ Agent pipeline completed")

    elapsed = time.time() - query_start
    avg_response_time.observe(elapsed)

    return result


# =========================================================
# STREAMING QUERY ENDPOINT
# =========================================================

@router.post("/query/stream")
async def stream_query(q: str):

    print("\n" + "=" * 60)
    print("🔥 /query/stream endpoint HIT")
    print("=" * 60)

    if state.retriever is None:

        async def error_generator():

            yield "No documents uploaded yet."

        return StreamingResponse(
            error_generator(),
            media_type="text/plain"
        )

    async def generator():

        print("⚙️ Running agent pipeline...")

        result = await run_agents(
            q,
            state.retriever
        )

        print("✅ Agent pipeline complete")

        answer = result["answer"]

        print("📤 Streaming response...")

        for word in answer.split():

            yield word + " "

            await asyncio.sleep(0.02)

        print("✅ Streaming finished")

    return StreamingResponse(
        generator(),
        media_type="text/plain"
    )


# =========================================================
# MEMORY ENDPOINTS
# =========================================================


@router.get("/memory/{session_id}")
async def get_memory_endpoint(session_id: str = "default_session"):
    """Get both short-term and long-term memory for a session."""
    # Short-term memory (in-memory cache)
    short_term = get_memory(session_id)

    # Long-term memory (SQLite)
    long_term = get_recent_conversations(session_id, limit=50)

    return {
        "session_id": session_id,
        "short_term": short_term,
        "short_term_count": len(short_term),
        "long_term": long_term,
        "long_term_count": len(long_term),
    }


@router.delete("/memory/{session_id}")
async def clear_memory_endpoint(session_id: str = "default_session"):
    """Clear all memory for a session."""
    # Clear short-term memory
    from app.core.cache import set_cache
    set_cache(f"conversation_memory:{session_id}", [])

    # Clear long-term memory
    clear_session(session_id)

    return {
        "message": f"Memory cleared for session: {session_id}",
        "session_id": session_id,
    }
