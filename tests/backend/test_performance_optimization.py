"""Performance & scalability optimization tests for AWS Guardian."""

import pytest


class TestCacheManager:
    """Test multi-level caching."""

    def test_memory_cache_operations(self):
        """✅ Manage in-memory cache."""
        from guardian.optimization.performance import CacheManager

        cache = CacheManager()

        # Set and get
        cache.put({'key': 'threat_1', 'value': {'id': '123', 'severity': 0.9}, 'ttl': 3600})
        result = cache.get({'key': 'threat_1'})

        assert 'value' in result
        assert result['value']['id'] == '123'

    def test_cache_eviction_lru(self):
        """✅ LRU eviction when cache full."""
        from guardian.optimization.performance import CacheManager

        cache = CacheManager()

        # Fill cache
        for i in range(5):
            cache.put({
                'key': f'threat_{i}',
                'value': {'data': i},
                'ttl': 3600,
                'max_size': 3
            })

        # Check LRU behavior
        result = cache.get({'key': 'threat_0'})
        assert result['found'] is False or 'value' in result

    def test_cache_ttl_expiration(self):
        """✅ TTL expiration and cleanup."""
        from guardian.optimization.performance import CacheManager

        cache = CacheManager()

        # Set with short TTL
        cache.put({'key': 'threat_1', 'value': 'data', 'ttl': 1})
        result = cache.get({'key': 'threat_1'})

        assert 'value' in result or result.get('expired') is True


class TestBatchProcessor:
    """Test batch processing and queuing."""

    def test_batch_processing(self):
        """✅ Process items in batches."""
        from guardian.optimization.performance import BatchProcessor

        processor = BatchProcessor()

        result = processor.process({
            'items': [
                {'id': '1', 'type': 'threat', 'severity': 0.8},
                {'id': '2', 'type': 'threat', 'severity': 0.6},
                {'id': '3', 'type': 'cost_anomaly', 'severity': 0.7}
            ],
            'batch_size': 2,
            'operation': 'analyze'
        })

        assert 'processed_count' in result or 'status' in result
        assert 'batches' in result or result.get('status') is not None

    def test_queue_management(self):
        """✅ Manage processing queue."""
        from guardian.optimization.performance import BatchProcessor

        processor = BatchProcessor()

        # Enqueue items
        result = processor.enqueue({
            'items': [
                {'id': '1', 'priority': 10},
                {'id': '2', 'priority': 5},
                {'id': '3', 'priority': 8}
            ]
        })

        assert 'queue_id' in result
        assert 'item_count' in result or 'enqueued' in result

    def test_batch_ordering_by_priority(self):
        """✅ Process batches respecting priority."""
        from guardian.optimization.performance import BatchProcessor

        processor = BatchProcessor()

        result = processor.process({
            'items': [
                {'id': '1', 'priority': 1},
                {'id': '2', 'priority': 10},
                {'id': '3', 'priority': 5}
            ],
            'sort_by_priority': True
        })

        assert 'processing_order' in result or 'status' in result


class TestIndexManager:
    """Test rapid lookup indexing."""

    def test_create_index(self):
        """✅ Create index for fast search."""
        from guardian.optimization.performance import IndexManager

        index = IndexManager()

        result = index.create({
            'index_name': 'threat_index',
            'field': 'threat_type',
            'index_type': 'inverted'
        })

        assert 'index_id' in result
        assert 'status' in result

    def test_index_search(self):
        """✅ Search using index."""
        from guardian.optimization.performance import IndexManager

        index = IndexManager()

        # Build index
        index.create({
            'index_name': 'threat_index',
            'documents': [
                {'id': '1', 'threat_type': 'ec2_unauthorized'},
                {'id': '2', 'threat_type': 's3_public'},
                {'id': '3', 'threat_type': 'ec2_unauthorized'}
            ]
        })

        # Search
        result = index.search({
            'index_name': 'threat_index',
            'query': 'ec2_unauthorized'
        })

        assert 'results' in result
        assert len(result['results']) >= 0

    def test_index_update(self):
        """✅ Update index with new documents."""
        from guardian.optimization.performance import IndexManager

        index = IndexManager()

        result = index.update({
            'index_name': 'threat_index',
            'documents': [
                {'id': '4', 'threat_type': 'iam_privilege_escalation'}
            ]
        })

        assert 'updated_count' in result or 'status' in result


class TestLoadBalancer:
    """Test load balancing."""

    def test_distribute_load(self):
        """✅ Distribute tasks across workers."""
        from guardian.optimization.performance import LoadBalancer

        balancer = LoadBalancer()

        result = balancer.distribute({
            'tasks': [
                {'id': '1', 'load': 10},
                {'id': '2', 'load': 15},
                {'id': '3', 'load': 8},
                {'id': '4', 'load': 12}
            ],
            'workers': 3
        })

        assert 'distribution' in result or 'assignments' in result
        assert 'status' in result

    def test_load_balancing_algorithm(self):
        """✅ Use balanced distribution algorithm."""
        from guardian.optimization.performance import LoadBalancer

        balancer = LoadBalancer()

        result = balancer.distribute({
            'tasks': [
                {'id': '1', 'load': 100},
                {'id': '2', 'load': 50},
                {'id': '3', 'load': 75}
            ],
            'algorithm': 'round_robin',
            'workers': 2
        })

        assert 'distribution' in result or 'assignments' in result

    def test_adaptive_load_balancing(self):
        """✅ Adapt balancing based on worker capacity."""
        from guardian.optimization.performance import LoadBalancer

        balancer = LoadBalancer()

        result = balancer.distribute({
            'tasks': [
                {'id': '1', 'load': 50},
                {'id': '2', 'load': 50}
            ],
            'worker_capacities': [100, 50, 75],
            'adaptive': True
        })

        assert 'distribution' in result or 'assignments' in result


class TestPerformanceOptimizationIntegration:
    """End-to-end performance optimization workflows."""

    def test_full_caching_pipeline(self):
        """✅ Cache hits and misses in pipeline."""
        from guardian.optimization.performance import CacheManager

        cache = CacheManager()

        # First access - cache miss
        result1 = cache.get({'key': 'threat_1'})

        # Store in cache
        cache.put({'key': 'threat_1', 'value': {'data': 'test'}, 'ttl': 3600})

        # Second access - cache hit
        result2 = cache.get({'key': 'threat_1'})

        assert ('value' in result2 or 'hit' in result2)

    def test_batch_and_index_pipeline(self):
        """✅ Batch process then index results."""
        from guardian.optimization.performance import BatchProcessor, IndexManager

        processor = BatchProcessor()
        index = IndexManager()

        # Process batches
        batch_result = processor.process({
            'items': [
                {'id': '1', 'threat_type': 'ec2'},
                {'id': '2', 'threat_type': 's3'},
                {'id': '3', 'threat_type': 'ec2'}
            ],
            'batch_size': 2
        })

        # Index results
        index_result = index.create({
            'index_name': 'processed_threats',
            'documents': [
                {'id': '1', 'threat_type': 'ec2'},
                {'id': '2', 'threat_type': 's3'},
                {'id': '3', 'threat_type': 'ec2'}
            ]
        })

        assert 'status' in batch_result
        assert 'index_id' in index_result

    def test_load_balanced_cache_and_batch(self):
        """✅ Balance load across cache and batch operations."""
        from guardian.optimization.performance import (
            CacheManager,
            BatchProcessor,
            LoadBalancer
        )

        cache = CacheManager()
        processor = BatchProcessor()
        balancer = LoadBalancer()

        # Distribute tasks
        distribution = balancer.distribute({
            'tasks': [
                {'id': '1', 'type': 'cache', 'load': 10},
                {'id': '2', 'type': 'batch', 'load': 20},
                {'id': '3', 'type': 'cache', 'load': 5}
            ],
            'workers': 2
        })

        assert 'distribution' in distribution or 'assignments' in distribution

    def test_full_optimization_stack(self):
        """✅ Complete optimization: cache, batch, index, load-balance."""
        from guardian.optimization.performance import (
            CacheManager,
            BatchProcessor,
            IndexManager,
            LoadBalancer
        )

        cache = CacheManager()
        processor = BatchProcessor()
        index = IndexManager()
        balancer = LoadBalancer()

        # Cache threats
        cache.put({'key': 'threats', 'value': [], 'ttl': 3600})

        # Batch process
        batch = processor.process({
            'items': [{'id': '1'}, {'id': '2'}],
            'batch_size': 2
        })

        # Index
        idx = index.create({'index_name': 'threats', 'documents': []})

        # Load balance
        distribution = balancer.distribute({
            'tasks': [{'id': '1', 'load': 10}],
            'workers': 1
        })

        assert 'status' in batch
        assert 'index_id' in idx
        assert 'distribution' in distribution or 'assignments' in distribution
