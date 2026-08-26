from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.routes import query as query_routes
from app.core.langsmith import is_langsmith_configured
# OLD: from app.core.ollama_client import close_clients
from app.core.llm_client import close_clients
from app.services.reranker_service import _get_model

app = FastAPI(title="Query Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(query_routes.router)


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    if is_langsmith_configured():
        print("LangSmith tracing is configured and ready")
    else:
        print("LangSmith not configured (set LANGCHAIN_API_KEY in .env to enable)")

    # Warm up the cross-encoder reranker so the first query isn't slow
    try:
        _get_model()
        print("Reranker model loaded")
    except Exception as e:
        print(f"Reranker warm-up failed: {e}")

    print("Query Service started on port 8002")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await close_clients()
    print("Query Service shut down")


@app.get("/")
def root():
    return {
        "message": "Query Service",
        "version": "2.0.0",
        "service": "query",
    }