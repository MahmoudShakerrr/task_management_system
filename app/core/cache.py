import redis
import json
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)


def set_cache(key: str, value, expire: int = 60):
    try:
        redis_client.setex(key, expire, json.dumps(value, default=str))
    except Exception:
        pass


def get_cache(key: str):
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def delete_cache(key: str):
    try:
        redis_client.delete(key)
    except Exception:
        pass


def delete_cache_pattern(pattern: str):
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass