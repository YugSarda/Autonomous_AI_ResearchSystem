from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import time

from app.services.agent_orchestrator import run_agents
from app.core.cache import get_cache, set_cache
from app.core.state import ensure_retriever
from app.services.prometheus_metrics import (
    total_queries,
    avg_response_time,
    cache_hits,
    cache_misses,
)

router = APIRouter()


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "query"}


# =========================================================
# CHECK RETRIEVER STATUS
# =========================================================

@router.get("/retriever/status")
async def retriever_status():
    """Check if ChromaDB has any indexed documents."""
    import os
    from app.core.config import VECTOR_DB_PATH

    chroma_path = VECTOR_DB_PATH
    has_index = os.path.exists(chroma_path) and any(
        f.endswith(".chroma") or os.path.isdir(os.path.join(chroma_path, d))
        for d in os.listdir(chroma_path)
    ) if os.path.exists(chroma_path) else False

    return {"retriever_ready": has_index}


# =========================================================
# NORMAL QUERY ENDPOINT
# =========================================================

@router.post("/query")
async def query_api(q: str, session_id: str = "default_session"):

    print("\n" + "=" * 60)
    print("🔥 /query endpoint HIT")
    print("=" * 60)

    total_queries.labels(endpoint="/query").inc()
    query_start = time.time()

    # -----------------------------------------------------
    # CHECK REDIS CACHE (same query from any user)
    # -----------------------------------------------------

    cache_key = f"query:{q.strip().lower()}:{session_id}"
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
    # ENSURE RETRIEVER IS AVAILABLE (builds from ChromaDB on demand)
    # -----------------------------------------------------

    retriever = ensure_retriever()
    if retriever is None:
        return {
            "error": "No documents indexed yet. Upload a document via /upload first.",
            "hint": "The retriever rebuilds automatically once ingestion completes.",
            "answer": "No documents indexed yet. Please upload a document first.",
            "confidence": 0,
            "citations": [],
        }

    # -----------------------------------------------------
    # RUN AGENT PIPELINE
    # -----------------------------------------------------

    result = await run_agents(q, retriever=retriever, session_id=session_id)

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

    async def generator():
        retriever = ensure_retriever()
        if retriever is None:
            yield "No documents indexed yet. Upload a document via /upload first."
            return

        print("⚙️ Running agent pipeline...")
        result = await run_agents(q, retriever=retriever)
        print("✅ Agent pipeline complete")

        answer = result.get("answer", "")
        print("📤 Streaming response...")

        for word in answer.split():
            yield word + " "
            await asyncio.sleep(0.02)

        print("✅ Streaming finished")

    return StreamingResponse(
        generator(),
        media_type="text/plain"
    )