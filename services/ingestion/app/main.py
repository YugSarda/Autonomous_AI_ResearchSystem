from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from app.routes import upload
from app.core.task_store import init_task_store
from app.services.async_ingestion import start_ingestion_worker
from app.utils.storage import ensure_bucket
from shared.db import init_db, close_pool

app = FastAPI(title="Ingestion Service", version="2.0.0")

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


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    # Initialize PostgreSQL database (shared schema)
    await init_db()

    # Ensure MinIO bucket exists for uploaded documents
    ensure_bucket()

    # Initialize async task store
    await init_task_store()

    # Start background ingestion worker
    await start_ingestion_worker()
    print("🚀 Ingestion Service started on port 8001")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await close_pool()
    print("🛑 Ingestion Service shut down")


@app.get("/")
def root():
    return {
        "message": "Ingestion Service",
        "version": "2.0.0",
        "service": "ingestion",
    }