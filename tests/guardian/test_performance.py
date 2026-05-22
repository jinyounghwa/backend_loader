"""Performance and load testing for Sprint 23 Phase 2 implementations."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from guardian.cache.memory import InMemoryCache
from guardian.cache.redis import RedisCache


class TestCachePerformance(unittest.TestCase):
    """Performance tests for cache implementations."""

    def test_memory_cache_set_performance(self):
        """Test in-memory cache set operation performance."""
        cache = InMemoryCache(ttl_seconds=300)

        start = time.time()
        for i in range(10000):
            cache.set(f"key_{i}", f"value_{i}")
        elapsed = time.time() - start

        avg_time = elapsed / 10000
        assert avg_time < 0.0001  # < 0.1ms per operation
        print(f"Memory cache set: {avg_time * 1000:.4f}ms per operation")

    def test_memory_cache_get_performance(self):
        """Test in-memory cache get operation performance."""
        cache = InMemoryCache(ttl_seconds=300)

        # Populate cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        start = time.time()
        for i in range(1000):
            _ = cache.get(f"key_{i}")
        elapsed = time.time() - start

        avg_time = elapsed / 1000
        assert avg_time < 0.001  # < 1ms per operation
        print(f"Memory cache get: {avg_time * 1000:.4f}ms per operation")

    def test_memory_cache_delete_performance(self):
        """Test in-memory cache delete operation performance."""
        cache = InMemoryCache(ttl_seconds=300)

        # Populate cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        start = time.time()
        for i in range(1000):
            cache.delete(f"key_{i}")
        elapsed = time.time() - start

        avg_time = elapsed / 1000
        assert avg_time < 0.001  # < 1ms per operation
        print(f"Memory cache delete: {avg_time * 1000:.4f}ms per operation")

    def test_memory_cache_clear_performance(self):
        """Test in-memory cache clear operation performance."""
        cache = InMemoryCache(ttl_seconds=300)

        # Populate cache
        for i in range(10000):
            cache.set(f"key_{i}", {"nested": f"value_{i}"})

        start = time.time()
        cache.clear()
        elapsed = time.time() - start

        assert elapsed < 0.1  # < 100ms to clear 10k items
        print(f"Memory cache clear: {elapsed * 1000:.2f}ms for 10k items")

    def test_ttl_expiration_performance(self):
        """Test TTL expiration check performance."""
        cache = InMemoryCache(ttl_seconds=1)

        # Set items
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        # Wait for expiration
        time.sleep(1.1)

        # Check expiration performance
        start = time.time()
        expired_count = 0
        for i in range(1000):
            if cache.get(f"key_{i}") is None:
                expired_count += 1
        elapsed = time.time() - start

        assert expired_count == 1000
        assert elapsed < 0.1  # < 100ms for 1000 expiration checks
        print(f"TTL expiration check: {elapsed * 1000:.2f}ms for 1000 items")


class TestAsyncCheckerPerformance(unittest.TestCase):
    """Performance tests for async checker implementations."""

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    @patch("guardian.checkers.ec2.Config.is_localstack", return_value=False)
    @patch("guardian.checkers.ec2.AWSClientProvider.get_client")
    def test_parallel_region_checking(self, mock_get_client, mock_is_localstack):
        """Test parallel region checking performance."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate 3 regions with response time
        def slow_operation(*args, **kwargs):
            time.sleep(0.1)
            return {
                "Regions": [
                    {"RegionName": "us-east-1"},
                    {"RegionName": "us-west-2"},
                    {"RegionName": "eu-west-1"},
                ]
            } if "describe_regions" in str(args) else {"Reservations": []}

        mock_client.describe_regions.side_effect = slow_operation
        mock_client.describe_instances.side_effect = slow_operation

        from guardian.checkers.ec2 import EC2Checker

        checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})

        # Measure async execution
        start = time.time()
        _result = self.loop.run_until_complete(checker.check_async())
        async_time = time.time() - start

        # With parallel execution, should be close to 0.2s, not 0.4s
        assert async_time < 0.35
        print(f"EC2 parallel check: {async_time:.2f}s (parallel) vs ~0.4s (sequential)")

    def test_parallel_bucket_checking(self):
        """Test parallel bucket checking performance."""
        mock_client = MagicMock()

        # Mock 10 buckets
        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": f"bucket-{i}", "CreationDate": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)}
                for i in range(10)
            ]
        }

        def slow_check(*args, **kwargs):
            time.sleep(0.05)
            return {"Grants": []}

        def slow_policy(*args, **kwargs):
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchBucketPolicy", "Message": "No policy"}}, "GetBucketPolicy")

        def slow_block(*args, **kwargs):
            time.sleep(0.05)
            return {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                }
            }

        mock_client.get_bucket_acl.side_effect = slow_check
        mock_client.get_bucket_policy.side_effect = slow_policy
        mock_client.get_public_access_block.side_effect = slow_block

        from guardian.checkers.s3 import S3Checker

        # Pass the mocked client in
        checker = S3Checker(clients={"s3": mock_client}, config={})

        # Measure async execution
        start = time.time()
        result = self.loop.run_until_complete(checker.check_async())
        async_time = time.time() - start

        # With parallel execution, should be < 0.25s, not 1.0s
        assert async_time < 0.25
        print(f"S3 parallel check: {async_time:.2f}s (parallel) vs ~1.0s (sequential)")

    async def async_io_operation(self, delay: float = 0.1):
        """Simulate async I/O operation."""
        await asyncio.sleep(delay)
        return {"status": "success"}

    def test_concurrent_async_operations(self):
        """Test concurrent async operation execution."""
        async def run_concurrent():
            # 10 concurrent operations with 0.1s each
            tasks = [self.async_io_operation(0.1) for _ in range(10)]
            start = time.time()
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start
            return elapsed, results

        elapsed, results = self.loop.run_until_complete(run_concurrent())

        # Parallel: ~0.1s, Sequential: ~1.0s
        assert elapsed < 0.3
        assert len(results) == 10
        print(f"10 concurrent operations: {elapsed:.2f}s (parallel) vs 1.0s (sequential)")


class TestCacheFailoverPerformance(unittest.TestCase):
    """Performance tests for cache failover mechanisms."""

    @patch("guardian.cache.redis.redis.from_url")
    def test_redis_to_memory_fallback_speed(self, mock_redis):
        """Test fallback to in-memory cache is fast."""
        # Simulate Redis connection failure
        mock_redis.side_effect = Exception("Connection failed")

        start = time.time()
        _cache = RedisCache(redis_url="redis://invalid")
        elapsed = time.time() - start

        # Fallback instantiation should be fast
        assert elapsed < 0.1
        print(f"Redis to Memory fallback: {elapsed * 1000:.2f}ms")

    @patch("guardian.cache.redis.redis.from_url")
    def test_fallback_cache_operations(self, mock_redis):
        """Test operations still work after fallback."""
        mock_redis.side_effect = Exception("Connection failed")

        cache = RedisCache(redis_url="redis://invalid")

        # Test operations
        start = time.time()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start

        start = time.time()
        for i in range(1000):
            value = cache.get(f"key_{i}")
            assert value == f"value_{i}"
        get_time = time.time() - start

        assert set_time < 0.1
        assert get_time < 0.1
        print(f"Fallback cache ops: set={set_time * 1000:.2f}ms, get={get_time * 1000:.2f}ms")


class TestLoadTesting(unittest.TestCase):
    """Load testing for high concurrent usage."""

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    def test_cache_under_load(self):
        """Test cache performance under high load."""
        cache = InMemoryCache(ttl_seconds=300)

        start = time.time()
        # 100 concurrent cache operations
        for batch in range(10):
            for i in range(1000):
                key = f"load_test_{batch}_{i}"
                cache.set(key, {"batch": batch, "id": i})

        for batch in range(10):
            for i in range(1000):
                key = f"load_test_{batch}_{i}"
                _ = cache.get(key)

        elapsed = time.time() - start

        # 20k operations should complete in < 1 second
        assert elapsed < 1.0
        ops_per_sec = 20000 / elapsed
        print(f"Cache under load: {ops_per_sec:.0f} ops/sec")

    async def async_checker_workload(self, delay: float = 0.05):
        """Simulate async checker workload."""
        await asyncio.sleep(delay)
        return {"severity": "INFO", "message": "All good"}

    def test_concurrent_checker_execution(self):
        """Test running many checkers concurrently."""
        async def run_load():
            # Simulate 20 concurrent checker executions
            tasks = [self.async_checker_workload(0.05) for _ in range(20)]
            start = time.time()
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start
            return elapsed, results

        elapsed, results = self.loop.run_until_complete(run_load())

        # 20 concurrent 0.05s operations should take ~0.05s, not 1.0s
        assert elapsed < 0.2
        assert len(results) == 20
        print(f"20 concurrent checkers: {elapsed:.2f}s (parallel) vs 1.0s (sequential)")


@pytest.mark.benchmark
class TestBenchmarks(unittest.TestCase):
    """Comprehensive benchmarks for phase 2 implementations."""

    def benchmark_memory_cache_operations(self):
        """Benchmark all in-memory cache operations."""
        cache = InMemoryCache(ttl_seconds=300)
        benchmarks = {}

        # Set operation
        start = time.time()
        for i in range(10000):
            cache.set(f"key_{i}", f"value_{i}")
        benchmarks["set"] = time.time() - start

        # Get operation
        start = time.time()
        for i in range(10000):
            _ = cache.get(f"key_{i}")
        benchmarks["get"] = time.time() - start

        # Delete operation
        start = time.time()
        for i in range(10000):
            cache.delete(f"key_{i}")
        benchmarks["delete"] = time.time() - start

        print("\nMemory Cache Benchmarks:")
        for op, duration in benchmarks.items():
            avg = (duration / 10000) * 1000
            print(f"  {op}: {avg:.4f}ms per operation")

        return benchmarks


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
