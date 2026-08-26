"""Agent Orchestrator - Delegates to the LangGraph workflow."""
from app.graph.workflow import run_research_workflow


async def run_agents(query, retriever, test_mode: bool = False, session_id: str = "default_session"):
    """Run the research pipeline via LangGraph orchestration.

    test_mode=False (default): full pipeline — planner, hybrid retrieval with
    cross-encoder re-ranking, memory-aware synthesizer, critique, and the
    self-reflection retry loop.
    """
    result = await run_research_workflow(
        query=query,
        retriever=retriever,
        session_id=session_id,
        test_mode=test_mode,
    )
    return result