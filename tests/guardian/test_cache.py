"""Tests for cache layer implementations (Redis and In-Memory)."""

import time
import unittest
from unittest.mock import MagicMock, patch

from guardian.cache.base import CacheBackend
from guardian.cache.memory import InMemoryCache
from guardian.cache.redis import RedisCache


class TestInMemoryCache(unittest.TestCase):
    """Test InMemoryCache implementation with TTL support."""

    def setUp(self):
        self.cache = InMemoryCache(ttl_seconds=2)

    def test_set_and_get_string(self):
        """Test setting and getting string values."""
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_set_and_get_dict(self):
        """Test setting and getting dictionary values."""
        test_dict = {"name": "test", "count": 42}
        self.cache.set("config", test_dict)
        self.assertEqual(self.cache.get("config"), test_dict)

    def test_set_and_get_list(self):
        """Test setting and getting list values."""
        test_list = [1, 2, 3, 4, 5]
        self.cache.set("items", test_list)
        self.assertEqual(self.cache.get("items"), test_list)

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_ttl_expiration(self):
        """Test that values expire after TTL."""
        self.cache.set("temp_key", "temp_value")
        self.assertEqual(self.cache.get("temp_key"), "temp_value")
        time.sleep(2.1)
        self.assertIsNone(self.cache.get("temp_key"))

    def test_ttl_not_expired(self):
        """Test that values don't expire before TTL."""
        self.cache.set("temp_key", "temp_value")
        time.sleep(1)
        self.assertEqual(self.cache.get("temp_key"), "temp_value")

    def test_delete_key(self):
        """Test deleting a key from cache."""
        self.cache.set("key1", "value1")
        self.cache.delete("key1")
        self.assertIsNone(self.cache.get("key1"))

    def test_delete_nonexistent_key(self):
        """Test deleting a key that doesn't exist (should not raise)."""
        self.cache.delete("nonexistent")

    def test_clear_cache(self):
        """Test clearing all cached values."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_custom_ttl(self):
        """Test setting custom TTL per operation."""
        cache_short = InMemoryCache(ttl_seconds=1)
        cache_short.set("key", "value")
        time.sleep(1.1)
        self.assertIsNone(cache_short.get("key"))


class TestRedisCache(unittest.TestCase):
    """Test RedisCache implementation with fallback to InMemory."""

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_set_and_get(self, mock_redis):
        """Test basic set/get with Redis client."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.get.return_value = b'"value1"'

        cache = RedisCache(redis_url="redis://localhost:6379")
        cache.set("key1", "value1")
        result = cache.get("key1")

        mock_client.set.assert_called_once()
        self.assertEqual(result, "value1")

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_fallback_to_memory(self, mock_redis):
        """Test fallback to InMemory when Redis connection fails."""
        mock_redis.side_effect = Exception("Connection failed")

        cache = RedisCache(redis_url="redis://invalid")
        cache.set("key1", "fallback_value")
        result = cache.get("key1")

        self.assertEqual(result, "fallback_value")

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_delete(self, mock_redis):
        """Test deleting keys from Redis."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        cache = RedisCache(redis_url="redis://localhost:6379")
        cache.delete("key1")

        mock_client.delete.assert_called_once_with("key1")

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_clear(self, mock_redis):
        """Test clearing Redis cache."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        cache = RedisCache(redis_url="redis://localhost:6379")
        cache.clear()

        mock_client.flushdb.assert_called_once()

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_json_serialization(self, mock_redis):
        """Test JSON serialization of complex objects."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.get.return_value = b'{"key": "value", "count": 42}'

        cache = RedisCache(redis_url="redis://localhost:6379")
        result = cache.get("config")

        self.assertEqual(result, {"key": "value", "count": 42})

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_exception_on_get(self, mock_redis):
        """Test graceful handling of Redis exceptions on get."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.get.side_effect = Exception("Redis error")

        cache = RedisCache(redis_url="redis://localhost:6379")
        cache.set("fallback_key", "fallback_value")
        result = cache.get("fallback_key")

        self.assertEqual(result, "fallback_value")


class TestCacheFactory(unittest.TestCase):
    """Test cache backend factory pattern."""

    @patch.dict("os.environ", {"CACHE_BACKEND": "memory", "REDIS_URL": ""})
    def test_get_memory_cache(self):
        """Test factory returns InMemoryCache when configured."""
        from guardian.cache import get_cache_backend

        cache = get_cache_backend()
        self.assertIsInstance(cache, InMemoryCache)

    @patch.dict("os.environ", {"CACHE_BACKEND": "redis", "REDIS_URL": "redis://localhost:6379"})
    @patch("guardian.cache.redis.redis.from_url")
    def test_get_redis_cache(self, mock_redis):
        """Test factory returns RedisCache when configured."""
        from guardian.cache import get_cache_backend

        mock_redis.return_value = MagicMock()
        cache = get_cache_backend()
        self.assertIsInstance(cache, RedisCache)

    @patch.dict("os.environ", {"CACHE_BACKEND": "", "REDIS_URL": ""})
    def test_get_default_cache(self):
        """Test factory returns InMemoryCache by default."""
        from guardian.cache import get_cache_backend

        cache = get_cache_backend()
        self.assertIsInstance(cache, InMemoryCache)


class TestCacheBackendInterface(unittest.TestCase):
    """Test CacheBackend abstract interface."""

    def test_cache_backend_is_abstract(self):
        """Test that CacheBackend cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            CacheBackend()

    def test_cache_implementations_implement_interface(self):
        """Test that implementations provide all required methods."""
        memory_cache = InMemoryCache()
        required_methods = ["get", "set", "delete", "clear"]

        for method in required_methods:
            self.assertTrue(hasattr(memory_cache, method))
            self.assertTrue(callable(getattr(memory_cache, method)))


if __name__ == "__main__":
    unittest.main()
