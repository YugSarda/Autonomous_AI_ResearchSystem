"""Ollama client - pooled HTTP clients (sync for agents, async for routes)."""

# =========================================================================
# ORIGINAL OLLAMA CLIENT (comment-out preserved for reference / rollback)
# =========================================================================
# =========================================================================
# import httpx
#
# from app.core.config import OLLAMA_URL, MODEL_NAME
#
# _sync_client: httpx.Client = None
# _async_client: httpx.AsyncClient = None
#
#
# def _get_sync_client() -> httpx.Client:
#     """Get the shared, connection-pooled sync client."""
#     global _sync_client
#     if _sync_client is None:
#         _sync_client = httpx.Client(timeout=None)
#     return _sync_client
#
#
# def get_async_client() -> httpx.AsyncClient:
#     """Get the shared, connection-pooled async client."""
#     global _async_client
#     if _async_client is None:
#         _async_client = httpx.AsyncClient(timeout=None)
#     return _async_client
#
#
# def generate(prompt: str) -> str:
#     """Blocking LLM generation (used by agents, runs off the event loop)."""
#     response = _get_sync_client().post(
#         f"{OLLAMA_URL}/api/generate",
#         json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
#     )
#     response.raise_for_status()
#     return response.json()["response"]
#
#
# async def generate_async(prompt: str) -> str:
#     """Async LLM generation."""
#     client = get_async_client()
#     response = await client.post(
#         f"{OLLAMA_URL}/api/generate",
#         json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
#     )
#     response.raise_for_status()
#     return response.json()["response"]
#
#
# async def stream_generate(prompt: str):
#     """Stream tokens from Ollama (for SSE-style streaming endpoints)."""
#     client = get_async_client()
#     async with client.stream(
#         "POST",
#         f"{OLLAMA_URL}/api/generate",
#         json={"model": MODEL_NAME, "prompt": prompt, "stream": True},
#     ) as response:
#         async for chunk in response.aiter_text():
#             yield chunk
#
#
# async def close_clients():
#     """Close pooled clients on shutdown."""
#     global _sync_client, _async_client
#     if _sync_client is not None:
#         _sync_client.close()
#         _sync_client = None
#     if _async_client is not None:
#         await _async_client.aclose()
#         _async_client = None