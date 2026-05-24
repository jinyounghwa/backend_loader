"""Sprint 38 Phase 2: Rule Performance Optimization Tests"""

import pytest
import asyncio
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from storage.rule_cache import RuleCache
from detectors.parallel_evaluator import ParallelEvaluator, ParallelEvaluationResult


# ==========================================
# Test Group 1: Rule Cache Basics (4 tests)
# ==========================================

def test_cache_initialization():
    """Test cache initialization"""
    repo = MagicMock()
    cache = RuleCache(repo, ttl_seconds=5)

    assert cache is not None
    assert cache.ttl == 5
    assert cache.get_cache_size() == 0


def test_cache_first_access_loads_from_repo():
    """Test that first cache access loads from repository"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [
        {'rule_id': 'rule-1', 'priority': 8},
        {'rule_id': 'rule-2', 'priority': 5},
        {'rule_id': 'rule-3', 'priority': 7}
    ]

    cache = RuleCache(repo, ttl_seconds=5)
    rules = cache.get_active_rules()

    assert len(rules) == 3
    assert repo.list_active_rules.call_count == 1


def test_cache_second_access_uses_cached_data():
    """Test that second access uses cached data without DB call"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=5)
    rules1 = cache.get_active_rules()
    rules2 = cache.get_active_rules()

    assert repo.list_active_rules.call_count == 1  # Only called once
    assert rules1 == rules2


def test_cache_hit_rate_calculation():
    """Test cache statistics and hit rate calculation"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=5)
    cache.get_active_rules()  # miss + load
    cache.get_active_rules()  # hit
    cache.get_active_rules()  # hit

    stats = cache.get_statistics()
    assert stats.hits == 2
    assert stats.misses == 1
    assert stats.hit_rate == pytest.approx(66.67, abs=1)


# ==========================================
# Test Group 2: Cache Expiration (3 tests)
# ==========================================

def test_cache_expires_after_ttl():
    """Test that cache expires after TTL"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=0.1)

    rules1 = cache.get_active_rules()
    assert repo.list_active_rules.call_count == 1

    time.sleep(0.15)

    rules2 = cache.get_active_rules()
    assert repo.list_active_rules.call_count == 2  # Called again after expiration


def test_cache_invalidation():
    """Test manual cache invalidation"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=5)
    cache.get_active_rules()
    assert cache.get_cache_size() == 1

    cache.invalidate()
    assert cache.get_cache_size() == 0

    stats = cache.get_statistics()
    assert stats.evictions == 1


def test_cache_age_tracking():
    """Test cache age tracking"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=5)
    cache.get_active_rules()

    age_ms = cache.get_cache_age_ms()
    assert age_ms is not None
    assert age_ms < 100

    time.sleep(0.1)
    age_ms = cache.get_cache_age_ms()
    assert age_ms > 100


# ==========================================
# Test Group 3: Parallel Evaluator Basics (3 tests)
# ==========================================

def test_parallel_evaluator_initialization():
    """Test evaluator initialization"""
    evaluator = ParallelEvaluator(max_concurrent_tasks=5, batch_size=10)
    assert evaluator.max_concurrent_tasks == 5
    assert evaluator.batch_size == 10


def test_parallel_evaluation_with_empty_input():
    """Test evaluation with empty threats or rules"""
    evaluator = ParallelEvaluator()

    result = evaluator.run_evaluation_async([], [])
    assert result.total_tasks == 0
    assert result.matched_threats == 0


def test_parallel_evaluation_creates_all_tasks():
    """Test that all threat/rule combinations are evaluated"""
    evaluator = ParallelEvaluator()

    threats = [MagicMock(threat_id=f't-{i}', severity=5+i) for i in range(5)]
    rules = [{'rule_id': f'r-{i}', 'priority': 5} for i in range(5)]

    result = evaluator.run_evaluation_async(threats, rules)

    # Should evaluate: 5 threats × 5 rules = 25 tasks
    assert result.total_tasks == 25


# ==========================================
# Test Group 4: Parallel Performance (2 tests)
# ==========================================

def test_parallel_evaluation_performance():
    """Test that parallel evaluation completes in reasonable time"""
    evaluator = ParallelEvaluator(max_concurrent_tasks=10)

    threats = [MagicMock(threat_id=f't-{i}', severity=5+i) for i in range(3)]
    rules = [{'rule_id': f'r-{i}', 'priority': 5+i} for i in range(3)]

    result = evaluator.run_evaluation_async(threats, rules)

    assert result.execution_time_ms < 5000
    assert result.completed_tasks == 9


def test_parallel_evaluation_with_batch_processing():
    """Test batch processing configuration"""
    evaluator = ParallelEvaluator(batch_size=5)

    threats = [MagicMock(threat_id=f't-{i}', severity=5) for i in range(3)]
    rules = [{'rule_id': f'r-{i}', 'priority': 4} for i in range(3)]

    result = evaluator.run_evaluation_async(threats, rules)

    assert result.completed_tasks == 9


# ==========================================
# Test Group 5: Configuration (2 tests)
# ==========================================

def test_cache_ttl_configuration():
    """Test TTL configuration changes"""
    repo = MagicMock()
    cache = RuleCache(repo, ttl_seconds=5)

    assert cache.ttl == 5
    cache.set_ttl(10)
    assert cache.ttl == 10


def test_parallel_evaluator_configuration():
    """Test evaluator configuration options"""
    evaluator = ParallelEvaluator(max_concurrent_tasks=5, batch_size=20)

    evaluator.set_max_concurrent_tasks(10)
    assert evaluator.max_concurrent_tasks == 10

    evaluator.set_batch_size(50)
    assert evaluator.batch_size == 50


# ==========================================
# Test Group 6: Statistics Tracking (1 test)
# ==========================================

def test_cache_statistics_tracking():
    """Test detailed statistics tracking"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    cache = RuleCache(repo, ttl_seconds=5)

    cache.get_active_rules()  # miss + load
    for _ in range(3):
        cache.get_active_rules()  # hits

    cache.invalidate()
    cache.get_active_rules()  # miss + load (eviction counted)

    stats = cache.get_statistics()
    assert stats.hits == 3
    assert stats.misses == 2  # First load + load after invalidate
    assert stats.evictions == 1


# ==========================================
# Test Group 7: Sync Wrapper (1 test)
# ==========================================

def test_parallel_evaluator_sync_wrapper():
    """Test synchronous wrapper for asyncio evaluation"""
    evaluator = ParallelEvaluator()

    threats = [MagicMock(threat_id='t-1', severity=7)]
    rules = [{'rule_id': 'r-1', 'priority': 5}]

    result = evaluator.run_evaluation_async(threats, rules)

    assert isinstance(result, ParallelEvaluationResult)
    assert result.total_tasks == 1
    assert result.completed_tasks == 1


# ==========================================
# Test Group 8: Error Handling (1 test)
# ==========================================

def test_cache_handles_repo_errors():
    """Test cache handles repository errors gracefully"""
    repo = MagicMock()
    repo.list_active_rules.side_effect = Exception("DB error")

    cache = RuleCache(repo, ttl_seconds=5)

    with pytest.raises(Exception):
        cache.get_active_rules()

    # Fix error and retry
    repo.list_active_rules.side_effect = None
    repo.list_active_rules.return_value = [{'rule_id': 'rule-1'}]

    rules = cache.get_active_rules()
    assert len(rules) == 1


# ==========================================
# Test Group 9: Integration Test (1 test)
# ==========================================

def test_cache_with_realistic_workflow():
    """Integration: cache with realistic rule management workflow"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [
        {'rule_id': 'rule-1', 'priority': 8},
        {'rule_id': 'rule-2', 'priority': 5},
        {'rule_id': 'rule-3', 'priority': 7}
    ]

    cache = RuleCache(repo, ttl_seconds=10)

    # Load rules
    rules = cache.get_active_rules()
    assert len(rules) == 3

    # Use cache multiple times
    for _ in range(5):
        rules = cache.get_active_rules()

    stats = cache.get_statistics()
    assert stats.hits >= 4
    assert stats.hit_rate > 50


# ==========================================
# Test Group 10: Throughput Measurement (1 test)
# ==========================================

def test_parallel_evaluator_throughput():
    """Test parallel evaluator throughput metrics"""
    evaluator = ParallelEvaluator(max_concurrent_tasks=20, batch_size=50)

    threats = [MagicMock(threat_id=f't-{i}', severity=5+i%5) for i in range(10)]
    rules = [{'rule_id': f'r-{i}', 'priority': 5+i%5} for i in range(10)]

    result = evaluator.run_evaluation_async(threats, rules)

    # 10 threats × 10 rules = 100 tasks
    assert result.total_tasks == 100
    assert result.execution_time_ms > 0
    assert result.throughput_tasks_per_sec > 0
