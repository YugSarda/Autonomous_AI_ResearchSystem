"""LangSmith configuration for observability."""
import os


def is_langsmith_configured() -> bool:
    """Check if LangSmith is configured."""
    return bool(os.getenv("LANGCHAIN_API_KEY"))