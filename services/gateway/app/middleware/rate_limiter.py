"""Rate Limiter Middleware - Sliding window algorithm using Redis."""
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, REDIS_URL

try:
    import redis
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("✅ Redis connected for Rate Limiter")
except Exception as e:
    print(f"⚠️ Redis not available for Rate Limiter: {e}")
    r = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter middleware."""

    def __init__(self, app, requests_per_window: int = None, window_seconds: int = None):
        super().__init__(app)
        self.requests_per_window = requests_per_window or RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or RATE_LIMIT_WINDOW

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and metrics
        if request.url.path in ("/health", "/metrics", "/"):
            return await call_next(request)

        if r is not None:
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_key = f"ratelimit:{client_ip}:{int(now // self.window_seconds)}"

            # Increment and set expiry
            current = r.incr(window_key)
            if current == 1:
                r.expire(window_key, self.window_seconds + 1)

            if current > self.requests_per_window:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Max {self.requests_per_window} requests per {self.window_seconds}s",
                        "retry_after": self.window_seconds - (now % self.window_seconds),
                    },
                    headers={"Retry-After": str(int(self.window_seconds - (now % self.window_seconds)))},
                )

        return await call_next(request)