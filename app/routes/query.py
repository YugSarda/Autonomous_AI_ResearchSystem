# from fastapi import APIRouter
# from fastapi.responses import StreamingResponse

# from app.services.agent_orchestrator import run_agents
# from app.core.ollama_client import stream_generate
# import asyncio
# router = APIRouter()


# @router.post("/query")
# async def query_api(q: str):
#     print("🔥 /query endpoint HIT")
#     result = run_agents(q)
#     return result


# @router.post("/query/stream")
# async def stream_query(q: str):
#     print("🔥 /query/stream endpoint HIT")

#     async def generator():
#         loop = asyncio.get_event_loop()

#         # Run full pipeline
#         result = await loop.run_in_executor(None, run_agents, q)

#         # Stream answer chunk by chunk
#         answer = result["answer"]

#         for word in answer.split():
#             yield word + " "
#             await asyncio.sleep(0.02)

#     return StreamingResponse(generator(), media_type="text/plain")
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

from app.services.agent_orchestrator import run_agents
from app.core.ollama_client import stream_generate
import app.core.state as state

router = APIRouter()


# =========================================================
# NORMAL QUERY ENDPOINT
# =========================================================

@router.post("/query")
async def query_api(q: str):

    print("\n" + "=" * 60)
    print("🔥 /query endpoint HIT")
    print("=" * 60)

    # -----------------------------------------------------
    # CHECK RETRIEVER
    # -----------------------------------------------------

    if state.retriever is None:

        return {
            "error": "No documents uploaded yet"
        }

    print("✅ Retriever found")

    # -----------------------------------------------------
    # RUN AGENT PIPELINE
    # -----------------------------------------------------

    result = run_agents(
        q,
        state.retriever
    )

    print("✅ Agent pipeline completed")

    return result


# =========================================================
# STREAMING QUERY ENDPOINT
# =========================================================

@router.post("/query/stream")
async def stream_query(q: str):

    print("\n" + "=" * 60)
    print("🔥 /query/stream endpoint HIT")
    print("=" * 60)

    if state.retriever is None:

        async def error_generator():

            yield "No documents uploaded yet."

        return StreamingResponse(
            error_generator(),
            media_type="text/plain"
        )

    async def generator():

        loop = asyncio.get_event_loop()

        print("⚙️ Running agent pipeline...")

        result = await loop.run_in_executor(
            None,
            run_agents,
            q,
            state.retriever
        )

        print("✅ Agent pipeline complete")

        answer = result["answer"]

        print("📤 Streaming response...")

        for word in answer.split():

            yield word + " "

            await asyncio.sleep(0.02)

        print("✅ Streaming finished")

    return StreamingResponse(
        generator(),
        media_type="text/plain"
    )
