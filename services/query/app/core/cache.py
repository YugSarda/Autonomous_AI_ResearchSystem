"""Redis Cache for Query Service - shared across multiple instances."""
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

try:
    import redis
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("✅ Redis connected for Query Service")
except Exception as e:
    print(f"⚠️ Redis not available: {e}")
    r = None


def get_cache(key):
    """Get a value from cache."""
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            print(f"⚠️ Redis get error: {e}")
            return None
    return None


def set_cache(key, value, ttl=3600):
    """Set a value in cache with TTL (default 1 hour)."""
    if r:
        try:
            r.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            print(f"⚠️ Redis set error: {e}")
            return False
    return False


def delete_cache(key):
    """Delete a key from cache."""
    if r:
        try:
            r.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ Redis delete error: {e}")
            return False
    return False