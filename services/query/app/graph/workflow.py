"""Research System - LangGraph orchestration workflow.

Flow: plan -> retrieve (hybrid + cross-encoder rerank)
      -> memory_load (STM + LTM context from memory service)
      -> synthesize (grounded answer using docs + memory)
      -> critique (groundedness score)
      |-- score >= threshold -> cite -> memory -> END
      |-- score < threshold & retries left -> reflect -> retrieve (new query)
      `-- retries exhausted -> memory -> END (best-effort answer)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.graph.state import ResearchState
from app.graph.nodes import (
    plan_node,
    retrieve_node,
    memory_load_node,
    synthesize_node,
    critique_node,
    cite_node,
    reflect_node,
    memory_node,
    should_reflect,
)


def build_research_graph():
    """Build the research orchestration graph."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("plan", plan_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("memory_load", memory_load_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("cite", cite_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("memory", memory_node)

    workflow.set_entry_point("plan")

    workflow.add_edge("plan", "retrieve")
    workflow.add_edge("retrieve", "memory_load")
    workflow.add_edge("memory_load", "synthesize")
    workflow.add_edge("synthesize", "critique")

    workflow.add_conditional_edges(
        "critique",
        should_reflect,
        {
            "cite": "cite",
            "reflect": "reflect",
            "memory": "memory",
            "end": END,
        },
    )

    workflow.add_edge("cite", "memory")
    workflow.add_edge("reflect", "retrieve")
    workflow.add_edge("memory", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Singleton Graph Instance
# ---------------------------------------------------------------------------

_GRAPH_INSTANCE = None


def get_compiled_graph():
    """Get or build the workflow graph (cached singleton)."""
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        _GRAPH_INSTANCE = build_research_graph()
        print("LangGraph research graph compiled")
    return _GRAPH_INSTANCE
# ---------------------------------------------------------------------------
# Workflow Runner
# ---------------------------------------------------------------------------


async def run_research_workflow(
    query: str,
    retriever: Any = None,
    session_id: str = "default_session",
    test_mode: bool = False,
) -> Dict[str, Any]:
    """Run the research workflow with complete observability."""
    graph = get_compiled_graph()
    trace_id = str(uuid.uuid4())

    initial_state = ResearchState(
        query=query,
        session_id=session_id,
        trace_id=trace_id,
        start_time=datetime.utcnow(),
        test_mode=test_mode,
    )
    initial_state.retriever = retriever

    def _invoke():
        # graph.ainvoke is a coroutine; run it inside a dedicated event loop
        # in this worker thread (the caller only reaches us via to_thread).
        return asyncio.run(
            graph.ainvoke(
                initial_state,
                config={
                    "recursion_limit": 30,
                    "configurable": {"thread_id": session_id},
                },
            )
        )

    try:
        print("\n" + "=" * 60)
        print("Starting LangGraph Research Workflow")
        print("Query: " + query)
        print("Trace ID: " + trace_id)
        print("=" * 60)

        # Run the whole (blocking) sync graph OFF the API event loop so the
        # LLM + retrieval + rerank calls never freeze uvicorn.
        result = await asyncio.to_thread(_invoke)

        if isinstance(result, dict):
            print("Graph returned dict (likely error state), converting...")
            result = ResearchState(**result)

        duration = (datetime.utcnow() - result.start_time).total_seconds()
        print("\nWorkflow completed in %.2fs" % duration)
        return _format_result(result)

    except Exception as e:
        import traceback
        print("Workflow failed: " + str(e))
        traceback.print_exc()
        return {
            "query": query,
            "answer": "An error occurred while processing your request.",
            "confidence": 0,
            "sources": [],
            "metrics": {"latency": 0, "error": str(e)},
            "logs": ["Workflow error: " + str(e)],
            "trace_id": trace_id,
            "session_id": session_id,
        }


def _format_result(state: ResearchState) -> Dict[str, Any]:
    """Format the research state into a clean API response."""
    all_sources = []
    for doc in state.all_docs:
        try:
            all_sources.append(getattr(doc, "metadata", {"source": str(doc)[:100]}))
        except Exception:
            all_sources.append({"source": str(doc)[:100]})

    duration = (datetime.utcnow() - state.start_time).total_seconds() if state.start_time else 0

    logs = [
        "Trace: " + state.trace_id,
        "Iterations: " + str(state.iteration_count + 1),
        "Score: " + str(state.score),
        "Sub-questions: " + str(state.sub_questions),
        "Memory hit: " + str(state.memory_hit),
        "Memory context chars: " + str(len(state.memory_context or "")),
        "Retrieval confidence: " + str(state.retrieval_confidence),
    ]
    if state.error:
        logs.append("Error: " + state.error)

    return {
        "answer": state.answer or "No answer generated.",
        "confidence": state.score,
        "sources": all_sources[:10],
        "citations": state.citations,
        "metrics": {
            "latency": duration,
            "iterations": state.iteration_count + 1,
            "node_metrics": state.metrics,
            "memory_hit": state.memory_hit,
        },
        "logs": logs,
        "trace_id": state.trace_id,
        "session_id": state.session_id,
    }