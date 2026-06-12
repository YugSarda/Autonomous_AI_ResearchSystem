from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from app.routes import upload, query
from app.core.memory_store import init_db
from app.core.langsmith import is_langsmith_configured

app = FastAPI(title="Autonomous AI Research System", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(upload.router)
app.include_router(query.router)


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    # Initialize long-term memory database
    init_db()

    # Check LangSmith configuration
    if is_langsmith_configured():
        print("📊 LangSmith tracing is configured and ready")
    else:
        print("📊 LangSmith not configured (set LANGCHAIN_API_KEY in .env to enable)")


@app.get("/")
def root():
    return {
        "message": "Autonomous AI Research System",
        "version": "2.0.0",
        "features": [
            "LangGraph orchestration",
            "Multimodal RAG (text, PDF, images, tables)",
            "Short-term & long-term memory",
            "LangSmith observability",
        ]
    }
