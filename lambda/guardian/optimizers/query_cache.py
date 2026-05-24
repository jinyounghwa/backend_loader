"""Query Result Caching System"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class QueryCache:
    """In-memory caching for query results with TTL and size limits"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}

    def get_cached_result(self, key: str) -> Optional[Dict]:
        """
        Retrieve cached result if it exists and hasn't expired

        Args:
            key: Cache key

        Returns:
            Cached result or None if not found/expired
        """
        try:
            if key not in self.cache:
                logger.debug(f"Cache miss for key: {key}")
                return None

            entry = self.cache[key]
            cached_time = entry.get('timestamp')

            if cached_time:
                elapsed = (datetime.now(timezone.utc) - cached_time).total_seconds()
                if elapsed > self.ttl_seconds:
                    logger.debug(f"Cache expired for key: {key} after {elapsed}s")
                    del self.cache[key]
                    return None

            logger.debug(f"Cache hit for key: {key}")
            return entry.get('result')

        except Exception as e:
            logger.error(f"Failed to retrieve cached result: {str(e)}")
            return None

    def cache_result(self, key: str, result: Dict) -> bool:
        """
        Store a result in cache

        Args:
            key: Cache key
            result: Result data to cache

        Returns:
            True if cached successfully
        """
        try:
            # Evict oldest entry if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].get('timestamp', datetime.now(timezone.utc))
                )
                del self.cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")

            self.cache[key] = {
                'result': result,
                'timestamp': datetime.now(timezone.utc)
            }

            logger.debug(f"Cached result for key: {key}, cache size: {len(self.cache)}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache result: {str(e)}")
            return False

    def invalidate_cache(self, key: str) -> bool:
        """
        Invalidate a specific cache entry

        Args:
            key: Cache key to invalidate

        Returns:
            True if invalidated
        """
        try:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Invalidated cache for key: {key}")
                return True
            else:
                logger.debug(f"Cache key not found for invalidation: {key}")
                return False

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {str(e)}")
            return False

    def clear_cache(self) -> None:
        """Clear entire cache"""
        try:
            size = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared cache with {size} entries")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics

        Returns:
            Stats dictionary with cache size and max size
        """
        return {
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }
