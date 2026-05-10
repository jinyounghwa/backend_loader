"""Abstract base class for cache backends."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: 300)
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear entire cache."""
        pass
