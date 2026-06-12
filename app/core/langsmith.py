"""LangSmith - Observability and tracing configuration."""
import os
from typing import Optional

# LangSmith will auto-configure via environment variables
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=ls__...
# LANGCHAIN_PROJECT=autonomous_research_system


def is_langsmith_configured() -> bool:
    """Check if LangSmith environment variables are configured."""
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1")
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    return tracing and bool(api_key)


def get_langsmith_callbacks():
    """Get LangSmith tracing callbacks if configured.

    Returns a LangChainTracer instance if LangSmith is configured,
    otherwise returns None (tracing will be disabled).
    """
    if not is_langsmith_configured():
        print("📊 LangSmith not configured (set LANGCHAIN_API_KEY to enable)")
        return None

    try:
        from langsmith.run_trees import RunTree
        from langchain.callbacks.tracers import LangChainTracer

        project_name = os.getenv("LANGCHAIN_PROJECT", "autonomous_research_system")
        tracer = LangChainTracer(project_name=project_name)
        print(f"📊 LangSmith tracing enabled (project: {project_name})")
        return tracer

    except ImportError:
        print("⚠️ langsmith package not installed. Install with: pip install langsmith")
        return None

    except Exception as e:
        print(f"⚠️ LangSmith initialization failed: {e}")
        return None


def get_run_config():
    """Get the LangChain run config for use with LangGraph."""
    tracer = get_langsmith_callbacks()
    if tracer:
        return {
            "callbacks": [tracer],
        }
    return {}