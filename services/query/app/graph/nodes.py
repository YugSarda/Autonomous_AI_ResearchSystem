"""LangGraph Nodes - Research pipeline.

Flow: plan -> retrieve (hybrid: semantic + BM25 + MMR + cross-encoder rerank)
      -> memory_load (short-term + long-term context) -> synthesize
      -> critique (groundedness) -> [reflect + re-retrieve loop] -> cite -> memory -> END
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os
import time
import traceback
from datetime import datetime
from typing import Callable

from app.graph.state import ResearchState
from app.agents.planner import plan
from app.agents.retriever_agent import retrieve
from app.agents.synthesizer import synthesize
from app.agents.critic import critique
from app.agents.self_reflection import reflect
from app.services.citation_verifier import verify_citations
from app.core.memory import add_memory, get_short_term_context, get_long_term_context
from app.core.state import ensure_retriever
from app.services.prometheus_metrics import (
    planner_latency,
    retrieval_latency,
    synthesizer_latency,
    critic_latency,
    requests_total,
    failures_total,
    synthesis_tokens_total,
    critic_avg_score,
)


def run_coro(coro):
    """Run a coroutine safely, even when an event loop is already running.

    LangGraph runs these (sync) nodes on the event-loop thread of a worker
    thread, so we can't await directly here. We hand the coroutine to a
    dedicated thread running `asyncio.run` to avoid "loop already running"
    errors and to keep the primary event loop unblocked.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def timed_node(node_name: str):
    """Decorator that wraps a node function with timing and error handling."""
    def decorator(func: Callable):
        def wrapper(state: ResearchState) -> ResearchState:
            start = time.time()
            print(f"📌 GRAPH NODE: {node_name} | Iteration: {state.iteration_count + 1}")
            try:
                result = func(state)
                elapsed = time.time() - start
                print(f"✅ Node '{node_name}' completed in {elapsed:.2f}s")
                result.metrics[node_name] = {
                    "latency_ms": round(elapsed * 1000, 2),
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return result
            except Exception as e:
                elapsed = time.time() - start
                print(f"❌ Node '{node_name}' FAILED: {e}")
                traceback.print_exc()
                state.error = str(e)
                state.error_node = node_name
                state.metrics[node_name] = {
                    "latency_ms": round(elapsed * 1000, 2),
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return state
        return wrapper
    return decorator
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_citations(all_docs) -> list:
    """Build rich citation dicts (deduplicated) from retrieved docs."""
    citations = []
    seen = set()
    for doc in all_docs:
        text = doc.text if hasattr(doc, "text") else str(doc)
        key = text[:100].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        source_path = metadata.get("source", "Unknown")
        file_name = os.path.basename(source_path) if source_path != "Unknown" else "Unknown"
        citations.append({
            "file_name": file_name,
            "file_path": source_path,
            "file_type": metadata.get("file_type", "document"),
            "text_snippet": text[:300].strip(),
            "score": round(doc.score, 4) if hasattr(doc, "score") and doc.score else None,
        })
    return citations


# ---------------------------------------------------------------------------
# Graph Node Implementations
# ---------------------------------------------------------------------------


@timed_node("plan")
def plan_node(state: ResearchState) -> ResearchState:
    """Generate sub-questions from the user query using the planner agent."""
    requests_total.labels(agent="planner").inc()
    with planner_latency.time():
        state.sub_questions = plan(state.query)
    print(f"🧠 Sub-questions: {state.sub_questions}")
    return state


@timed_node("retrieve")
def retrieve_node(state: ResearchState) -> ResearchState:
    """Hybrid retrieval per sub-question, in parallel, with cross-encoder rerank.

    `retrieve` -> `run_query_pipeline` performs: vector (semantic) + BM25
    (keyword) -> MMR diversity -> cross-encoder re-ranking.
    """
    start = time.time()
    retriever = getattr(state, "retriever", None)
    if retriever is None:
        retriever = ensure_retriever()

    sub_questions = state.sub_questions or [state.query]

    # Run each sub-query's retrieval (CPU-bound + blocking LLM) in worker threads
    # so the LangGraph event loop stays responsive.
    results = []
    all_docs = []
    confidence_scores = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(sub_questions), 4)
    ) as pool:
        futures = [pool.submit(retrieve, q, retriever) for q in sub_questions]
        for fut in futures:
            res = fut.result()
            results.append(res)
            all_docs.extend(res.get("docs", []))
            confidence_scores.append(res.get("confidence", 0.5))

    state.retrieval_results = results
    state.retrieval_confidence = confidence_scores
    state.all_docs = all_docs
    state.citations = _build_citations(all_docs)

    retrieval_latency.observe(time.time() - start)
    requests_total.labels(agent="retrieval").inc()
    if state.error:
        failures_total.labels(agent="retrieval").inc()

    print(f"✅ Retrieved docs total: {len(all_docs)}")
    return state
@timed_node("memory_load")
def memory_load_node(state: ResearchState) -> ResearchState:
    """Load short-term + long-term memory context and inject it into the state
    so the synthesizer can ground follow-up answers."""
    async def _load():
        short_term = await get_short_term_context(state.session_id)
        long_term = await get_long_term_context(state.session_id)
        parts = [p for p in (short_term, long_term) if p]
        return "\n\n".join(parts)

    context = run_coro(_load())
    state.memory_context = context if context else None
    if state.memory_context:
        print(f"🧠 Loaded memory context ({len(state.memory_context)} chars)")
    else:
        print("ℹ️ No prior memory for this session")
    return state


@timed_node("synthesize")
def synthesize_node(state: ResearchState) -> ResearchState:
    """Synthesize retrieved results into a grounded answer, using the whole
    short-term + long-term memory context."""
    requests_total.labels(agent="synthesizer").inc()
    with synthesizer_latency.time():
        result = synthesize(
            state.retrieval_results,
            state.query,
            memory_context=state.memory_context,
            test_mode=False,
        )
    if isinstance(result, dict):
        state.answer = result.get("answer", "")
        state.citations = result.get("citations", state.citations)
    else:
        state.answer = result
    token_estimate = max(1, len(state.answer or "") // 4)
    synthesis_tokens_total.labels(agent="synthesizer").inc(token_estimate)
    print("✅ Synthesis complete")
    return state


@timed_node("critique")
def critique_node(state: ResearchState) -> ResearchState:
    """Critique the answer for groundedness/faithfulness against the docs."""
    requests_total.labels(agent="critic").inc()
    with critic_latency.time():
        score, feedback = critique(
            answer=state.answer,
            question=state.query,
            docs=state.all_docs,
        )
    state.score = score
    state.feedback = feedback
    critic_avg_score.labels(agent="critic").set(score)
    print(f"📊 Groundedness score: {score}")
    return state


@timed_node("cite")
def cite_node(state: ResearchState) -> ResearchState:
    """Attach citation sources to the answer."""
    if state.answer and state.all_docs:
        state.answer = verify_citations(state.answer, state.all_docs)
    print("✅ Citations verified")
    return state


@timed_node("reflect")
def reflect_node(state: ResearchState) -> ResearchState:
    """Use self-reflection to build an improved query and retry."""
    print("⚠️ Score below threshold, reflecting...")
    improved_query = reflect(
        answer=state.answer,
        question=state.query,
        docs=state.all_docs,
        feedback=state.feedback,
        score=state.score,
        confidence_scores=state.retrieval_confidence,
    )
    state.query = improved_query
    state.iteration_count += 1
    print(f"🔄 Improved query: {improved_query[:80]}...")
    return state


@timed_node("memory")
def memory_node(state: ResearchState) -> ResearchState:
    """Store the conversation in short-term and long-term memory."""
    if state.answer:
        run_coro(add_memory(
            state.query, state.answer,
            session_id=state.session_id,
            confidence=state.score,
        ))
    print("🧠 Memory stored")
    return state


# ---------------------------------------------------------------------------
# Conditional Edge Functions
# ---------------------------------------------------------------------------


def should_reflect(state: ResearchState) -> str:
    """Decide whether the answer is good enough, needs a self-reflection retry,
    or should stop with the best-effort answer."""
    if state.error:
        print(f"⚠️ Error detected: {state.error} → ending")
        return "end"

    if state.score >= state.quality_threshold:
        print(f"✅ Score {state.score} >= threshold {state.quality_threshold} → citing + memory")
        return "cite"

    if state.iteration_count < state.max_iterations:
        print(f"🔄 Score {state.score} < {state.quality_threshold}, retry {state.iteration_count + 1}/{state.max_iterations}")
        return "reflect"

    print(f"⚠️ Max iterations ({state.max_iterations}) reached → storing best-effort answer")
    return "memory"