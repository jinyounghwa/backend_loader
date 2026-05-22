"""Redis cache backend implementation."""

import json
import logging
from typing import Any, Optional

import redis
from guardian.cache.base import CacheBackend
from guardian.cache.memory import InMemoryCache

logger = logging.getLogger(__name__)


class RedisCache(CacheBackend):
    """Redis-backed cache with in-memory fallback."""

    def __init__(self, redis_url: str, fallback: Optional[CacheBackend] = None):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL (e.g. redis://localhost:6379)
            fallback: Fallback cache backend if Redis unavailable (default: InMemoryCache)
        """
        self.redis_url = redis_url
        self.fallback = fallback or InMemoryCache()
        self.redis: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=5)
            self.redis.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning("Redis connection failed, using fallback cache: %s", e)
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with fallback.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if self.redis:
            try:
                value_json = self.redis.get(key)
                if value_json:
                    if isinstance(value_json, bytes):
                        value_json = value_json.decode("utf-8")
                    return json.loads(value_json)
                return None
            except Exception as e:
                logger.error("Redis get failed for key %s: %s", key, e)
                return self.fallback.get(key)

        return self.fallback.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in Redis with fallback.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: 300)
        """
        if self.redis:
            try:
                value_json = json.dumps(value)
                self.redis.setex(key, ttl, value_json)
            except Exception as e:
                logger.error("Redis set failed for key %s: %s", key, e)
                self.fallback.set(key, value, ttl)
        else:
            self.fallback.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Delete key from Redis and fallback.

        Args:
            key: Cache key
        """
        if self.redis:
            try:
                self.redis.delete(key)
            except Exception as e:
                logger.error("Redis delete failed for key %s: %s", key, e)

        self.fallback.delete(key)

    def clear(self) -> None:
        """Clear Redis and fallback cache."""
        if self.redis:
            try:
                self.redis.flushdb()
            except Exception as e:
                logger.error("Redis clear failed: %s", e)

        self.fallback.clear()
