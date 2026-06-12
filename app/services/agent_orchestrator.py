"""Agent Orchestrator - Delegates to LangGraph workflow."""
import asyncio

from app.graph.workflow import run_research_workflow


async def run_agents(query, retriever, test_mode: bool = True):
    """Run the research pipeline via LangGraph orchestration.

    This function wraps the LangGraph workflow to maintain backward
    compatibility with existing route handlers.
    """
    result = await run_research_workflow(
        query=query,
        retriever=retriever,
        session_id="default_session",
        test_mode=test_mode,
    )
    return result
