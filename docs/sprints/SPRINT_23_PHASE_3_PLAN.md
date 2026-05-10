# Sprint 23 Phase 3: Testing & Verification

**Status:** 🔄 IN PROGRESS  
**Target:** Full test suite execution, performance validation, integration testing

---

## Phase 3 Overview

Phase 3 focuses on comprehensive testing of the Phase 2 implementations:
1. Unit tests for cache layer (11 test cases)
2. Async checker tests with mock AWS APIs (12 test cases)
3. Multi-account orchestration tests (8 test cases)
4. Integration tests with LocalStack
5. Performance benchmarks and load testing
6. Documentation and deployment guides

---

## 3.1: Test Environment Setup

### Virtual Environment Creation
```bash
# Create isolated Python environment
python3 -m venv venv_sprint23
source venv_sprint23/bin/activate

# Install all dependencies
pip install -r lambda/requirements.txt
pip install pytest pytest-asyncio pytest-mock

# Verify installations
python -m pytest --version
```

### LocalStack Setup (For Integration Tests)
```bash
# Start LocalStack with required services
docker-compose -f docker-compose.localstack.yml up -d

# Verify LocalStack services
aws s3 ls --endpoint-url=http://localhost:4566
aws ec2 describe-instances --endpoint-url=http://localhost:4566
```

---

## 3.2: Unit Test Execution

### Cache Layer Tests
```bash
cd /path/to/backend_loader
pytest tests/guardian/test_cache.py -v

# Expected Output:
# TestInMemoryCache::test_set_and_get_string PASSED
# TestInMemoryCache::test_ttl_expiration PASSED
# TestRedisCache::test_redis_set_and_get PASSED
# TestRedisCache::test_redis_fallback_to_memory PASSED
# ... (11 tests total)
```

### Async Checker Tests
```bash
pytest tests/guardian/test_async_checkers.py -v

# Expected Output:
# TestCostCheckerAsync::test_check_async_no_anomalies PASSED
# TestEC2CheckerAsync::test_check_async_unauthorized_region PASSED
# TestS3CheckerAsync::test_check_async_public_bucket_detected PASSED
# TestCloudTrailCheckerAsync::test_check_async_root_account_activity PASSED
# TestIAMCheckerAsync::test_check_async_no_baseline PASSED
# TestGuardDutyCheckerAsync::test_check_async_critical_findings PASSED
# ... (12 tests total)
```

### Multi-Account Tests
```bash
pytest tests/guardian/test_multi_account.py -v

# Expected Output:
# TestMultiAccountOrchestrator::test_get_accounts_async_multiple_accounts PASSED
# TestMultiAccountOrchestrator::test_create_account_checkers_async PASSED
# TestAccountCheckAggregation::test_determine_system_health_critical PASSED
# ... (8 tests total)
```

### Full Test Suite
```bash
# Run all guardian tests
pytest tests/guardian/ -v --tb=short

# Run with coverage
pytest tests/guardian/ --cov=lambda/guardian --cov-report=html

# Expected: 31+ tests passing with >85% code coverage
```

---

## 3.3: Integration Tests

### LocalStack Integration Tests

**test_integration_cost_checker.py**
```python
@pytest.mark.integration
async def test_cost_checker_with_localstack():
    """Test CostChecker against LocalStack Cost Explorer."""
    # Setup LocalStack CE client
    ce_client = boto3.client(
        'ce',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1'
    )
    
    # Create cost checker
    checker = CostChecker({}, {'daily_cost_threshold': 100})
    
    # Execute check
    result = await checker.check_async()
    
    # Verify result structure
    assert result.severity in ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    assert result.title is not None
```

**test_integration_ec2_checker.py**
```python
@pytest.mark.integration
async def test_ec2_checker_with_localstack():
    """Test EC2Checker against LocalStack EC2."""
    ec2 = boto3.client(
        'ec2',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1'
    )
    
    # Create test instance
    response = ec2.run_instances(
        ImageId='ami-12345678',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro'
    )
    instance_id = response['Instances'][0]['InstanceId']
    
    # Run checker
    checker = EC2Checker({}, {'authorized_regions': ['us-east-1']})
    result = await checker.check_async()
    
    # Verify detection
    assert any(instance_id in str(v) for v in result.details.values())
```

**test_integration_s3_checker.py**
```python
@pytest.mark.integration
async def test_s3_checker_with_localstack():
    """Test S3Checker against LocalStack S3."""
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1'
    )
    
    # Create public bucket
    bucket_name = 'test-public-bucket'
    s3.create_bucket(Bucket=bucket_name)
    
    # Set public ACL
    s3.put_bucket_acl(
        Bucket=bucket_name,
        ACL='public-read'
    )
    
    # Run checker
    checker = S3Checker({}, {})
    result = await checker.check_async()
    
    # Verify detection
    assert result.severity == 'CRITICAL'
    assert bucket_name in result.message
```

---

## 3.4: Performance & Load Testing

### Async Performance Benchmark

**test_performance_async_vs_sync.py**
```python
import time
import asyncio

def test_async_performance_improvement():
    """Benchmark async vs sync execution."""
    
    # Sync execution (sequential)
    start = time.time()
    sync_results = []
    for region in ['us-east-1', 'us-west-2', 'eu-west-1']:
        result = get_region_data_sync(region)
        sync_results.append(result)
    sync_time = time.time() - start
    
    # Async execution (parallel)
    start = time.time()
    async_results = asyncio.run(
        asyncio.gather(*[
            get_region_data_async(region)
            for region in ['us-east-1', 'us-west-2', 'eu-west-1']
        ])
    )
    async_time = time.time() - start
    
    # Verify performance improvement
    speedup = sync_time / async_time
    assert speedup > 2.0  # Expected 3x improvement for 3 regions
    print(f"Async speedup: {speedup:.1f}x")
    print(f"Sync time: {sync_time:.2f}s, Async time: {async_time:.2f}s")
```

### Cache Performance Test

**test_cache_performance.py**
```python
def test_cache_hit_performance():
    """Verify cache hit performance."""
    cache = InMemoryCache(ttl_seconds=300)
    
    # Populate cache
    for i in range(1000):
        cache.set(f"key_{i}", f"value_{i}")
    
    # Measure cache hit time
    start = time.time()
    for i in range(1000):
        _ = cache.get(f"key_{i}")
    cache_time = time.time() - start
    
    # Cache access should be < 1ms per operation
    avg_time = cache_time / 1000
    assert avg_time < 0.001
    print(f"Cache avg access time: {avg_time*1000:.3f}ms")

def test_redis_vs_memory_fallback():
    """Verify automatic fallback performance."""
    # Test with failing Redis
    cache = RedisCache(redis_url="redis://invalid")
    
    start = time.time()
    cache.set("test_key", {"data": list(range(100))})
    memory_fallback_time = time.time() - start
    
    # Fallback should be immediate
    assert memory_fallback_time < 0.01
```

### Concurrent Checker Load Test

**test_concurrent_checkers.py**
```python
@pytest.mark.asyncio
async def test_concurrent_multi_account_checks():
    """Test running checkers across multiple accounts concurrently."""
    
    accounts = [
        {"account_id": "111111111", "account_name": "Prod"},
        {"account_id": "222222222", "account_name": "Dev"},
        {"account_id": "333333333", "account_name": "Test"},
    ]
    
    # Create mock checkers
    checkers = [
        create_mock_checker(account_id)
        for account_id in [a["account_id"] for a in accounts]
    ]
    
    # Run all checks in parallel
    start = time.time()
    results = await asyncio.gather(*[
        checker.check_async()
        for checker in checkers
    ])
    elapsed = time.time() - start
    
    # All checks should complete in parallel time
    # (not sequential time)
    assert elapsed < 10.0  # Should be < 1 check's time * 3
    assert len(results) == 3
```

---

## 3.5: Code Coverage Analysis

### Coverage Requirements
- Cache layer: >95% (abstract interface + 2 implementations)
- Async checkers: >80% (6 checkers with mocked AWS)
- Orchestrator: >85% (multi-account coordination)
- Overall: >82% for lambda/guardian/

### Coverage Report
```bash
# Generate coverage report
pytest tests/guardian/ --cov=lambda/guardian --cov-report=term-missing

# Generate HTML report
pytest tests/guardian/ --cov=lambda/guardian --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Targets by Module
```
lambda/guardian/cache/base.py        100%
lambda/guardian/cache/memory.py      98%
lambda/guardian/cache/redis.py       92%
lambda/guardian/checkers/cost.py     85%
lambda/guardian/checkers/ec2.py      84%
lambda/guardian/checkers/s3.py       86%
lambda/guardian/checkers/cloudtrail.py 82%
lambda/guardian/checkers/iam.py      83%
lambda/guardian/checkers/guardduty.py 81%
lambda/guardian/orchestrator.py      87%
```

---

## 3.6: Validation Checklist

### Functionality
- [ ] All 30+ unit tests passing
- [ ] Integration tests with LocalStack passing
- [ ] Async/await patterns working correctly
- [ ] Error handling and fallback mechanisms
- [ ] Multi-account orchestration working
- [ ] Cache TTL expiration verified
- [ ] Redis fallback to InMemory tested

### Performance
- [ ] Async execution shows 3x+ speedup vs sync
- [ ] Cache hits < 1ms per operation
- [ ] Concurrent account checks execute in parallel
- [ ] No memory leaks in long-running tests
- [ ] Connection pooling working correctly

### Compatibility
- [ ] Sync wrappers work in all contexts
- [ ] Backward compatibility maintained
- [ ] Error handling doesn't break execution
- [ ] Logging captures all events
- [ ] JSON serialization works for all types

### Code Quality
- [ ] >82% code coverage
- [ ] No pylint/flake8 warnings
- [ ] Type hints correct
- [ ] Exception handling comprehensive
- [ ] Context managers properly implemented

---

## 3.7: Known Issues & Workarounds

### Environment Constraints
**Issue:** Homebrew Python system package protection prevents pip install  
**Workaround:** Use virtual environment (`python3 -m venv venv_sprint23`)

**Issue:** LocalStack may require additional Docker configuration  
**Workaround:** Use provided docker-compose.localstack.yml

### Test Execution Tips
```bash
# Run single test file
pytest tests/guardian/test_cache.py -v

# Run specific test
pytest tests/guardian/test_cache.py::TestInMemoryCache::test_ttl_expiration -v

# Run with detailed output
pytest tests/guardian/ -vv --tb=long

# Stop on first failure
pytest tests/guardian/ -x
```

---

## 3.8: Timeline & Dependencies

| Task | Duration | Dependencies |
|------|----------|--------------|
| Environment setup | 10 min | venv, pip |
| Unit test execution | 5 min | pytest |
| Integration test setup | 15 min | LocalStack, Docker |
| Performance testing | 10 min | pytest, test data |
| Coverage analysis | 5 min | pytest-cov |
| Documentation review | 10 min | Previous phases |
| **Total Phase 3** | **55 min** | All Phase 2 code |

---

## 3.9: Success Criteria

✅ **Testing**
- 31+ tests passing with 0 failures
- >82% code coverage across guardian/
- All async patterns working correctly
- Error handling tested

✅ **Performance**
- 3x+ speedup from async parallelization
- Cache hits performing optimally
- Concurrent operations executing in parallel

✅ **Quality**
- No warnings in test execution
- All edge cases covered
- Comprehensive error scenarios tested

✅ **Documentation**
- Test results documented
- Performance metrics recorded
- Known issues cataloged

---

## Next Steps: Phase 4 (Documentation & Deployment)

After Phase 3 validation:
1. Create deployment guide for multi-account AWS setup
2. Document cache invalidation strategies
3. Create operations runbook
4. Document troubleshooting procedures
5. Create v1.3 release notes

**Estimated:** 2-3 hours for complete Phase 3 + Phase 4
