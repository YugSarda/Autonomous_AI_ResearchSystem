import json

try:
    import redis
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    r.ping()
except:
    r = None

_local_cache = {}


def get_cache(key):
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except:
            pass
    return _local_cache.get(key)


def set_cache(key, value):
    if r:
        try:
            r.set(key, json.dumps(value), ex=3600)
            return
        except:
            pass
    _local_cache[key] = value
