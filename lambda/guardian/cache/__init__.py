"""Cache module factory pattern."""

import logging
import os

from guardian.cache.base import CacheBackend
from guardian.cache.memory import InMemoryCache

logger = logging.getLogger(__name__)


def get_cache_backend() -> CacheBackend:
    """Get cache backend based on configuration.

    Priority:
    1. CACHE_BACKEND env var (redis/memory)
    2. REDIS_URL env var (uses redis if set)
    3. Default to in-memory cache
    """
    cache_backend = os.getenv("CACHE_BACKEND", "").lower()
    redis_url = os.getenv("REDIS_URL", "")

    if cache_backend == "redis" or redis_url:
        try:
            from guardian.cache.redis import RedisCache

            if not redis_url:
                redis_url = "redis://localhost:6379"

            logger.info("Using Redis cache backend (%s)", redis_url)
            return RedisCache(redis_url, fallback=InMemoryCache())
        except Exception as e:
            logger.warning("Failed to initialize Redis cache, falling back to in-memory: %s", e)
            return InMemoryCache()

    logger.info("Using in-memory cache backend")
    return InMemoryCache()


__all__ = ["CacheBackend", "get_cache_backend"]
