"""Gemini LLM client - Google Gemini 2.5 Flash backend.

Replaces the old Ollama-based ``ollama_client`` while keeping the exact same
function signatures (``generate``, ``generate_async``, ``stream_generate``,
``close_clients``) so agents and the main app require minimal changes.

Uses the current supported ``google-genai`` package (``from google import
genai``). The original Ollama implementation is preserved (commented out) at:
    services/query/app/core/ollama_client.py
"""
from google import genai
from typing import AsyncGenerator

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL

# ---------------------------------------------------------------------------
# Validate configuration up-front and cache the client singleton
# ---------------------------------------------------------------------------
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to your .env or the docker-compose "
        "environment variables (GEMINI_API_KEY)."
    )

_client: "genai.Client | None" = None


def _get_client() -> "genai.Client":
    """Return the shared genai.Client singleton (created on first use)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Public API - mirrors the old ``ollama_client`` interface
# ---------------------------------------------------------------------------

def generate(prompt: str) -> str:
    """Blocking LLM generation (used by agents, runs off the event loop)."""
    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


async def generate_async(prompt: str) -> str:
    """Async LLM generation."""
    client = _get_client()
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


async def stream_generate(prompt: str) -> AsyncGenerator[str, None]:
    """Stream tokens from Gemini (for SSE-style streaming endpoints)."""
    client = _get_client()
    async for chunk in client.aio.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text


def close_clients():
    """Close pooled clients on shutdown.

    The genai SDK manages its own HTTP connections internally. We simply
    reset the cached client singleton so the next call re-initializes.
    """
    global _client
    _client = None