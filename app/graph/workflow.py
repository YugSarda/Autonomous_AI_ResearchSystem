"""Research System - LangGraph orchestration workflow replacing custom agent orchestration."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.graph.state import ResearchState
from app.graph.nodes import (
    plan_node,
    retrieve_node,
    synthesize_node,
    critique_node,
    cite_node,
    reflect_node,
    memory_node,
    should_reflect,
)


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------


def build_research_graph() -> StateGraph:
    """Build the research orchestration graph.

    Flow (test_mode=True):
        plan -> retrieve -> synthesize -> memory -> END
            (skips critique, reflect, cite)

    Flow (test_mode=False):
        plan -> retrieve -> synthesize -> critique
            ├── score >= threshold → cite → memory → END
            └── score < threshold → reflect ──> retrieve (retry loop)
                (up to max_iterations)
    """
    workflow = StateGraph(ResearchState)

    # Register nodes (no check_memory — removed)
    workflow.add_node("plan", plan_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("cite", cite_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("memory", memory_node)

    # Set entry point — start directly with planning
    workflow.set_entry_point("plan")

    # Main flow edges
    workflow.add_edge("plan", "retrieve")
    workflow.add_edge("retrieve", "synthesize")
    workflow.add_edge("synthesize", "critique")

    # Conditional edges after critique:
    # - test_mode → memory (skip critique/reflect)
    # - score >= threshold: cite -> memory -> END
    # - score < threshold and retries left: reflect -> retrieve
    # - max retries reached: END
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

    # After citation, go to memory then end
    workflow.add_edge("cite", "memory")
    workflow.add_edge("memory", END)

    # After reflection, loop back to retrieval
    workflow.add_edge("reflect", "retrieve")

    return workflow.compile()


# ---------------------------------------------------------------------------
# Singleton Graph Instance
# ---------------------------------------------------------------------------

_GRAPH_INSTANCE = None


def get_compiled_graph() -> StateGraph:
    """Get or build the workflow graph (cached singleton)."""
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        _GRAPH_INSTANCE = build_research_graph()
        print("✅ LangGraph research graph compiled")
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

    # Store retriever as hidden attribute for nodes to use
    initial_state._retriever = retriever

    try:
        print(f"\n{'='*60}")
        print("🚀 Starting LangGraph Research Workflow")
        print(f"📝 Query: {query}")
        print(f"🔗 Trace ID: {trace_id}")
        print(f"🧪 Test Mode: {test_mode}")
        print(f"{'='*60}")

        result = await graph.ainvoke(
            initial_state,
            config={
                "recursion_limit": 25,
                "configurable": {"thread_id": session_id},
            },
        )

        # Handle both ResearchState object and dict return types
        if isinstance(result, dict):
            print(f"⚠️ Graph returned dict (likely error state), converting...")
            # Convert dict back to ResearchState for formatting
            result = ResearchState(**result)

        duration = (datetime.utcnow() - result.start_time).total_seconds()
        print(f"\n✅ Workflow completed in {duration:.2f}s")

        return _format_result(result)

    except Exception as e:
        import traceback
        print(f"❌ Workflow failed: {e}")
        traceback.print_exc()
        return {
            "query": query,
            "answer": "An error occurred while processing your request.",
            "confidence": 0,
            "sources": [],
            "metrics": {"latency": 0, "error": str(e)},
            "logs": [f"Workflow error: {e}"],
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
        "logs": [
            f"Trace: {state.trace_id}",
            f"Iterations: {state.iteration_count + 1}",
            f"Score: {state.score}",
            f"Sub-questions: {state.sub_questions}",
            f"Memory hit: {state.memory_hit}",
            f"Matched query: {state.matched_query}" if state.matched_query else "No memory match",
            f"Similarity score: {state.similarity_score}" if state.similarity_score else "",
            f"Error: {state.error}" if state.error else "No errors",
        ],
        "trace_id": state.trace_id,
        "session_id": state.session_id,
    }