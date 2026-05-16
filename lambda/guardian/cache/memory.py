"""In-memory cache backend implementation."""

import logging
import time
from typing import Any, Dict, Optional

from guardian.cache.base import CacheBackend

logger = logging.getLogger(__name__)


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize in-memory cache.

        Args:
            ttl_seconds: Default time-to-live in seconds for cached items
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: instance ttl_seconds)
        """
        effective_ttl = ttl if ttl is not None else self.ttl_seconds
        expiry = time.time() + effective_ttl
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
