import redis
from app.core.config import get_settings

settings = get_settings()

class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # decode_responses=True automatically decodes bytes to strings
            cls._instance = redis.from_url(settings.redis_url, decode_responses=True)
        return cls._instance

def get_redis():
    """FastAPI dependency for Redis"""
    return RedisClient.get_instance()
