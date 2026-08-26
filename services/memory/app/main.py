from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from app.routes import memory as memory_routes
from app.core.memory_store import init_db
from shared.db import close_pool

app = FastAPI(title="Memory Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(memory_routes.router)


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    # Initialize long-term memory database
    await init_db()
    print("🚀 Memory Service started on port 8003")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await close_pool()
    print("🛑 Memory Service shut down")


@app.get("/")
def root():
    return {
        "message": "Memory Service",
        "version": "2.0.0",
        "service": "memory",
    }