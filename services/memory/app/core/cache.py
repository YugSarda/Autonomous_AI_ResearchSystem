"""Redis Cache for Memory Service."""
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

try:
    import redis
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("✅ Redis connected for Memory Service")
except Exception as e:
    print(f"⚠️ Redis not available for Memory Service: {e}")
    r = None


def get_cache(key):
    """Get a value from cache."""
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None
    return None


def set_cache(key, value, ttl=3600):
    """Set a value in cache with TTL."""
    if r:
        try:
            r.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception:
            return False
    return False


def delete_cache(key):
    """Delete a key from cache."""
    if r:
        try:
            r.delete(key)
            return True
        except Exception:
            return False
    return False