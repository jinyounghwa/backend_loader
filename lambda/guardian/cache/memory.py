"""In-memory cache backend implementation."""

import logging
import time
from typing import Any, Dict, Optional

from guardian.cache.base import CacheBackend

logger = logging.getLogger(__name__)


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support."""

    def __init__(self):
        """Initialize in-memory cache."""
        self._cache: Dict[str, tuple[Any, float]] = {}

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

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 300)
        """
        expiry = time.time() + ttl
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
