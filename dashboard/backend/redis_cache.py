import os
import logging
import threading
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RedisCache")

class InMemCache:
    """Thread-safe fallback in-memory cache when Redis is offline."""
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()
        logger.info("ℹ️ Initialized in-memory fallback cache.")

    def get(self, key):
        with self._lock:
            return self._data.get(key)

    def set(self, key, value, ex=None):
        with self._lock:
            self._data[key] = value
            return True

    def delete(self, key):
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def ping(self):
        return True

# Initialize caching layer
cache = None
redis_client = None

try:
    import redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url, socket_timeout=2.0)
    # Ping to check if Redis is active
    redis_client.ping()
    cache = redis_client
    logger.info("✅ Successfully connected to Redis server.")
except Exception as e:
    logger.warning(f"⚠️ Redis unavailable ({e}). Falling back to in-memory caching.")
    cache = InMemCache()
