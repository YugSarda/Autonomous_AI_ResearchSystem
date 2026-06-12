"""LangGraph Nodes - Wrapping existing research agents into graph-compatible nodes."""
from __future__ import annotations

import os
import time
import traceback
from datetime import datetime
from typing import Any, Callable

import numpy as np

from app.graph.state import ResearchState
from app.agents.planner import plan
from app.agents.retriever_agent import retrieve
from app.agents.synthesizer import synthesize
from app.agents.critic import critique
from app.agents.self_reflection import reflect
from app.services.citation_verifier import verify_citations
from app.core.memory import get_memory, add_memory, get_short_term_context, get_long_term_context
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


def timed_node(node_name: str):
    """Decorator that wraps a node function with timing and error handling."""
    def decorator(func: Callable):
        def wrapper(state: ResearchState) -> ResearchState:
            start = time.time()
            print(f"\n{'='*50}")
            print(f"📌 GRAPH NODE: {node_name}")
            print(f"📊 Iteration: {state.iteration_count + 1}")
            print(f"{'='*50}")

            try:
                result = func(state)
                elapsed = time.time() - start
                print(f"✅ Node '{node_name}' completed in {elapsed:.2f}s")
                result.metrics[node_name] = {
                    "latency_ms": round(elapsed * 1000, 2),
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
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
                    "timestamp": datetime.utcnow().isoformat()
                }
                return state

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Helper: Get embedding model from retriever
# ---------------------------------------------------------------------------


def _get_embed_model(state: ResearchState):
    """Get the embedding model from the retriever."""
    retriever = getattr(state, "_retriever", None)
    if retriever is None:
        import app.core.state as app_state
        retriever = app_state.retriever
    if retriever and hasattr(retriever, "embed_model"):
        return retriever.embed_model
    return None


def _cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ---------------------------------------------------------------------------
# Graph Node Implementations
# ---------------------------------------------------------------------------


@timed_node("plan_node")
def plan_node(state: ResearchState) -> ResearchState:
    """Generate sub-questions from the user query using the planner agent."""
    requests_total.labels(agent="planner").inc()
    with planner_latency.time():
        sub_questions = plan(state.query)
    state.sub_questions = sub_questions
    print(f"🧠 Sub-questions: {sub_questions}")
    return state


@timed_node("retrieve_node")
def retrieve_node(state: ResearchState) -> ResearchState:
    """Retrieve documents for each sub-question using the retriever agent.
    
    Uses asyncio.gather for parallel retrieval across all sub-questions.
    Captures confidence scores per sub-question.
    """
    import asyncio

    results = []
    all_docs = []
    retrieve_start = time.time()

    retriever = getattr(state, "_retriever", None)
    if retriever is None:
        print("⚠️ No retriever found in state, retrieving from app.core.state")
        import app.core.state as app_state
        retriever = app_state.retriever

    # --- Parallel retrieval for all sub-questions ---
    async def _retrieve_all():
        async def _retrieve_one(q: str):
            print(f"   → Retrieving (parallel): {q}")
            # run sync retrieve in thread pool
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None, retrieve, q, retriever, state.test_mode
            )
            return res

        tasks = [_retrieve_one(q) for q in state.sub_questions]
        return await asyncio.gather(*tasks)

    # Run the async gather in the current event loop
    loop = asyncio.new_event_loop()
    try:
        gathered = loop.run_until_complete(_retrieve_all())
    finally:
        loop.close()

    # Collect results and confidence scores
    confidence_scores = []
    for res in gathered:
        results.append(res)
        all_docs.extend(res.get("docs", []))
        confidence_scores.append(res.get("confidence", 0.5))

    state.retrieval_results = results
    state.retrieval_confidence = confidence_scores
    state.all_docs = all_docs

    print(f"📊 Retrieval confidence scores: {[round(c, 3) for c in confidence_scores]}")
    
    # --- Extract rich citations ---
    citations = []
    seen_texts = set()
    for doc in all_docs:
        text = doc.text if hasattr(doc, "text") else str(doc)
        
        # Deduplicate by text content
        text_key = text[:100].strip().lower()
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        
        # Extract metadata
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        source_path = metadata.get("source", "Unknown")
        file_name = os.path.basename(source_path) if source_path != "Unknown" else "Unknown"
        
        citation = {
            "file_name": file_name,
            "file_path": source_path,
            "file_type": metadata.get("file_type", "document"),
            "text_snippet": text[:300].strip(),
            "score": round(doc.score, 4) if hasattr(doc, "score") and doc.score else None,
        }
        citations.append(citation)
    
    state.citations = citations

    # Prometheus: record retrieval metrics
    retrieval_latency.observe(time.time() - retrieve_start)
    requests_total.labels(agent="retrieval").inc()
    if state.error:
        failures_total.labels(agent="retrieval").inc()

    print(f"✅ Extracted {len(citations)} citations")
    print(f"✅ Retrieved docs total: {len(all_docs)}")
    return state


@timed_node("synthesize_node")
def synthesize_node(state: ResearchState) -> ResearchState:
    """Synthesize retrieved results into a coherent answer with inline citations."""
    requests_total.labels(agent="synthesizer").inc()
    with synthesizer_latency.time():
        result = synthesize(
            state.retrieval_results,
            state.query,
            memory_context=state.memory_context,
            test_mode=state.test_mode,
        )
    # Handle both dict return (new) and string return (old) for compatibility
    if isinstance(result, dict):
        state.answer = result.get("answer", "")
        state.citations = result.get("citations", state.citations)
    else:
        state.answer = result
    # Estimate tokens from answer length (rough approximation)
    token_estimate = max(1, len(state.answer or "") // 4)
    synthesis_tokens_total.labels(agent="synthesizer").inc(token_estimate)
    print("✅ Synthesis complete")
    return state


@timed_node("critique_node")
def critique_node(state: ResearchState) -> ResearchState:
    """Critique the generated answer for quality and accuracy.
    
    Evaluates answer groundedness against the question AND retrieved docs.
    In test mode, skip the LLM call and assign a default score.
    """
    if state.test_mode:
        print("🧪 Test mode: skipping critique, assigning default score 75")
        state.score = 75
        state.feedback = "Test mode - critique skipped"
        return state
    
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
    print(f"📊 Score: {score}")
    return state


@timed_node("cite_node")
def cite_node(state: ResearchState) -> ResearchState:
    """Attach citation sources to the answer."""
    if state.answer and state.all_docs:
        state.answer = verify_citations(state.answer, state.all_docs)
    print("✅ Citations verified")
    return state


@timed_node("reflect_node")
def reflect_node(state: ResearchState) -> ResearchState:
    """Improve the query via self-reflection and retry.
    
    Receives the full context: question, retrieved docs, critique feedback,
    and confidence scores to generate a targeted improved query.
    """
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
    return state


@timed_node("memory_node")
def memory_node(state: ResearchState) -> ResearchState:
    """Store the conversation in short-term and long-term memory."""
    if state.answer:
        add_memory(state.query, state.answer, session_id=state.session_id, confidence=state.score)
    print("🧠 Memory stored")
    return state


# ---------------------------------------------------------------------------
# Conditional Edge Functions
# ---------------------------------------------------------------------------


def should_reflect(state: ResearchState) -> str:
    """Decide whether to reflect+retry or proceed to output."""
    if state.error:
        print(f"⚠️ Error detected: {state.error} → ending")
        return "end"

    # In test mode, skip critique/reflect entirely
    if state.test_mode:
        print(f"🧪 Test mode enabled → skipping critique/reflect, going to memory")
        return "memory"

    if state.score >= state.quality_threshold:
        print(f"✅ Score {state.score} >= threshold {state.quality_threshold} → citing + memory")
        return "cite"

    if state.iteration_count < state.max_iterations:
        print(f"🔄 Score {state.score} < {state.quality_threshold}, retry {state.iteration_count + 1}/{state.max_iterations}")
        return "reflect"

    print(f"⚠️ Max iterations ({state.max_iterations}) reached → ending")
    return "end"


def should_check_memory(state: ResearchState) -> str:
    """Decide whether to skip pipeline due to memory hit."""
    if state.memory_hit and state.cached_answer:
        print(f"🎯 Memory hit detected → skipping to memory storage")
        return "memory"
    print(f"ℹ️ No memory hit → proceeding to plan")
    return "plan"
