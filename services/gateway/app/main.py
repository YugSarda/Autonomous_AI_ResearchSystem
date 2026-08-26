"""API Gateway - Single entry point for all microservices with rate limiting."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import httpx
import time

from app.core.config import (
    INGESTION_SERVICE_URL,
    QUERY_SERVICE_URL,
    MEMORY_SERVICE_URL,
)
from app.middleware.rate_limiter import RateLimitMiddleware

app = FastAPI(title="API Gateway", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware
app.add_middleware(RateLimitMiddleware)

# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Shared HTTP client
client = httpx.AsyncClient(timeout=None)


# =========================================================
# PROXY HANDLER
# =========================================================

async def proxy_request(service_url: str, request: Request):
    """Proxy an incoming request to the target service (streams responses).

    Streaming is used instead of buffering so slow LLM responses arrive
    incrementally instead of being held until the pipeline finishes.
    """
    path = request.url.path
    query = request.url.query
    query_params = dict(request.query_params)

    # Build target URL with original query params
    target_url = f"{service_url}{path}"

    # Forward session_id if present in headers
    session_id = request.headers.get("X-Session-ID")
    if session_id and "session_id" not in query_params:
        separator = "&" if query else ""
        target_url += f"{'?' if not query else ''}{query}{separator}session_id={session_id}"
    elif query:
        target_url += f"?{query}"

    print(f"🔀 Gateway: {request.method} {path} -> {target_url}")

    try:
        # Forward the request body for POST/PUT
        body = await request.body()

        # Forward headers (skip hop-by-hop headers)
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("connection", None)
        headers.pop("content-length", None)

        req = client.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )
        resp = await client.send(req, stream=True)

        # Strip hop-by-hop headers so the streaming response stays clean
        resp_headers = dict(resp.headers)
        resp_headers.pop("content-length", None)
        resp_headers.pop("transfer-encoding", None)
        resp_headers.pop("connection", None)

        async def stream_body():
            async for chunk in resp.aiter_bytes():
                yield chunk

        return StreamingResponse(
            stream_body(),
            status_code=resp.status_code,
            headers=resp_headers,
            media_type=resp.headers.get("content-type"),
        )

    except httpx.ConnectError as e:
        print(f"❌ Gateway: {path} -> Connection failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "error": f"Service unavailable: {service_url}",
                "detail": str(e),
            },
        )
    except Exception as e:
        print(f"❌ Gateway: {path} -> Error: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Bad gateway", "detail": str(e)},
        )


# =========================================================
# ROUTES - Upload routes -> Ingestion Service
# =========================================================

@app.api_route("/upload", methods=["GET", "POST", "OPTIONS"])
async def upload_proxy(request: Request):
    return await proxy_request(INGESTION_SERVICE_URL, request)


@app.api_route("/upload/status", methods=["GET", "OPTIONS"])
async def upload_status_proxy(request: Request):
    return await proxy_request(INGESTION_SERVICE_URL, request)


@app.api_route("/upload/status/{task_id}", methods=["GET", "OPTIONS"])
async def upload_task_status_proxy(request: Request):
    return await proxy_request(INGESTION_SERVICE_URL, request)


# =========================================================
# ROUTES - Query routes -> Query Service
# =========================================================

@app.api_route("/query", methods=["GET", "POST", "OPTIONS"])
async def query_proxy(request: Request):
    return await proxy_request(QUERY_SERVICE_URL, request)


@app.api_route("/query/stream", methods=["GET", "POST", "OPTIONS"])
async def query_stream_proxy(request: Request):
    return await proxy_request(QUERY_SERVICE_URL, request)


@app.api_route("/retriever/status", methods=["GET", "OPTIONS"])
async def retriever_status_proxy(request: Request):
    return await proxy_request(QUERY_SERVICE_URL, request)


# =========================================================
# ROUTES - Memory routes -> Memory Service
# =========================================================

@app.api_route("/memory/{session_id}", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def memory_proxy(request: Request):
    return await proxy_request(MEMORY_SERVICE_URL, request)


@app.api_route("/memory", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def memory_root_proxy(request: Request):
    return await proxy_request(MEMORY_SERVICE_URL, request)


# =========================================================
# ROUTES - Health checks per service
# =========================================================

@app.get("/health")
async def health():
    """Gateway health check with downstream service status."""
    services = {
        "ingestion": INGESTION_SERVICE_URL,
        "query": QUERY_SERVICE_URL,
        "memory": MEMORY_SERVICE_URL,
    }

    statuses = {}
    all_healthy = True

    for name, url in services.items():
        try:
            resp = await client.get(f"{url}/health", timeout=5.0)
            statuses[name] = "healthy" if resp.status_code == 200 else "unhealthy"
            if resp.status_code != 200:
                all_healthy = False
        except Exception:
            statuses[name] = "unreachable"
            all_healthy = False

    return {
        "status": "healthy" if all_healthy else "degraded",
        "gateway": "healthy",
        "services": statuses,
    }


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()


@app.get("/")
def root():
    return {
        "message": "API Gateway",
        "version": "2.0.0",
        "routes": {
            "upload": "/upload/* -> Ingestion Service (:8001)",
            "query": "/query/* -> Query Service (:8002)",
            "memory": "/memory/* -> Memory Service (:8003)",
        },
        "features": ["rate_limiting", "request_routing", "health_checks"],
    }