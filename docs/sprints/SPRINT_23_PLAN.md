# Sprint 23 Plan: v1.3 Architecture & Implementation

**Project**: AWS Guardian v1.3 - Advanced Features  
**Date**: May 8, 2026  
**Duration**: 3-4 sessions (~12 hours)  
**Status**: 📋 PLANNED  
**Previous**: Sprint 22 (v1.2 Released)

---

## Executive Summary

Sprint 23 focuses on **v1.3 feature implementation** with three major enhancements:

1. **Redis Integration** - Distributed caching across Lambda instances
2. **aioboto3 Upgrade** - Modern async AWS SDK (replace boto3)
3. **Multi-Account Support** - Monitor multiple AWS accounts from single Lambda

**Expected Outcomes**:
- 100% test pass rate maintained (194+ tests)
- 2-3x improvement in distributed scenarios
- Full multi-account aggregation
- Production-ready v1.3

---

## Phase 1: Architecture Design (Session 1, ~2 hours)

### 1.1 Redis Integration Architecture

**Goal**: Design distributed caching system

**Current State** (v1.2):
```
Lambda Instance → In-Memory Cache (TTL: 5 min)
Lambda Instance → In-Memory Cache (TTL: 5 min)
# Problem: Cache not shared across instances
```

**Target State** (v1.3):
```
Lambda Instance 1 ↘
Lambda Instance 2 ─→ Redis (Shared Cache) ← Primary
Lambda Instance 3 ↗
                 ↓ (Fallback if Redis down)
              In-Memory Cache
```

**Design Decisions**:

| Decision | Option A | Option B | **Choice** |
|----------|----------|----------|-----------|
| Redis Tier | AWS ElastiCache | AWS MemoryDB | **ElastiCache** (cost-effective) |
| Node Type | cache.t3.micro | cache.t3.small | **cache.t3.micro** (free tier eligible) |
| Multi-AZ | Enabled | Disabled | **Enabled** (high availability) |
| Failover Strategy | Fallback to in-memory | Fail request | **Fallback to in-memory** |
| Cache TTL | 5 minutes | 1 hour | **5 minutes** (same as v1.2) |
| Encryption | Enabled | Disabled | **Enabled** (at-rest) |

**Implementation Files**:
```
lambda/guardian/cache/
├── base.py              # Abstract CacheBackend interface
├── memory.py            # In-memory implementation (existing)
├── redis.py             # Redis implementation (new)
└── __init__.py          # CacheFactory
```

**Key Classes**:
```python
# Abstract interface
class CacheBackend(ABC):
    async def get(key: str) -> Optional[T]
    async def set(key: str, value: T, ttl: int)
    async def delete(key: str) -> bool
    async def clear() -> bool

# Redis implementation
class RedisCache(CacheBackend):
    def __init__(redis_url: str)
    async def get(key: str) -> Optional[T]  # Connection pooling
    async def set(key: str, value: T, ttl: int)
    async def fallback_to_memory(value: T)  # Fallback on error

# Factory
class CacheFactory:
    @staticmethod
    def create(backend: str) -> CacheBackend:
        # Select based on env var: CACHE_BACKEND=redis|memory
```

---

### 1.2 aioboto3 Migration Architecture

**Goal**: Replace boto3 with aioboto3 for true async I/O

**Current State** (v1.2):
```python
# boto3 + ThreadPoolExecutor
client = boto3.client('ec2')  # Sync client
response = client.describe_instances()  # Blocking I/O
# Parallelism via asyncio.gather() + executor
```

**Target State** (v1.3):
```python
# aioboto3
async with aioboto3.client('ec2') as client:
    response = await client.describe_instances()  # True async I/O
# Parallelism via asyncio.gather() directly
```

**Performance Impact**:
- Remove ThreadPoolExecutor overhead (~20-50ms per checker)
- Reduce context switching
- Better CPU efficiency in Lambda

**Migration Plan**:
```
1. Add aioboto3 to requirements.txt
2. Update AWSClientProvider to use aioboto3.Session
3. Update all checkers to use async context managers
4. Update orchestrator for native async
5. Test all 194+ tests
```

**Backward Compatibility**: 
- Keep boto3 in requirements (fallback)
- Detect aioboto3 availability at runtime
- Use boto3 if aioboto3 import fails

---

### 1.3 Multi-Account Support Architecture

**Goal**: Monitor multiple AWS accounts from single Lambda

**Current State** (v1.2):
```
Lambda Function
    ↓
AWS Account (Fixed)
    ├── EC2
    ├── S3
    └── Cost Explorer
# Problem: Can only monitor 1 account
```

**Target State** (v1.3):
```
Lambda Function
    ↓ (EventBridge event includes account_ids parameter)
AWS Account 1          AWS Account 2          AWS Account 3
├── EC2              ├── EC2                ├── EC2
├── S3               ├── S3                 ├── S3
└── Cost Explorer    └── Cost Explorer      └── Cost Explorer
    ↓                   ↓                       ↓
  Assume Role        Assume Role            Assume Role
    ↓                   ↓                       ↓
Results aggregated by account in orchestrator
```

**Design Decisions**:

| Component | Implementation |
|-----------|-----------------|
| Account List | EventBridge event parameter: `account_ids: ["123456", "789012"]` |
| Cross-Account Role | IAM role in target account with trust relationship |
| Role Naming | `arn:aws:iam::{account_id}:role/guardian-monitor-role` |
| Results Aggregation | Per-account findings + rollup summary |
| Dashboard | Account selector + aggregate view |

**EventBridge Event Schema** (Updated):
```json
{
  "check_type": "all",
  "regions": ["us-east-1", "us-west-2"],
  "account_ids": ["123456789012", "210987654321"],  // NEW
  "time": "2026-05-09T10:00:00Z"
}
```

**Orchestrator Changes**:
```python
async def run_all_checks(event: dict):
    account_ids = event.get('account_ids', [primary_account_id])
    
    results_by_account = {}
    for account_id in account_ids:
        # Assume role in target account
        client = await assume_role_and_get_client(account_id)
        
        # Run checks
        results = await run_checks_in_account(account_id, client)
        results_by_account[account_id] = results
    
    # Aggregate
    return aggregate_results(results_by_account)
```

---

### 1.4 Design Decision Document

**File**: `docs/sprints/SPRINT_23_DESIGN.md` (To Create)

**Contents**:
- Architecture diagrams (ASCII)
- Design trade-offs
- Performance projections
- Backward compatibility notes
- Testing strategy
- Deployment plan

---

## Phase 2: Core Implementation (Sessions 2-3, ~6 hours)

### 2.1 Redis Integration Implementation

**Step 1: Infrastructure Setup** (~30 min)
```bash
# AWS ElastiCache Redis cluster
terraform/redis.tf:
- ElastiCache Redis 7.0
- cache.t3.micro node (free tier)
- Multi-AZ enabled
- Automatic failover
- Encryption at rest
- VPC Security Group
- Subnet Group

Output: redis_endpoint = "redis.xxxxx.ng.0001.use1.cache.amazonaws.com:6379"
```

**Step 2: CacheBackend Classes** (~1.5 hours)

**File**: `lambda/guardian/cache/base.py`
```python
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
import json

T = TypeVar('T')

class CacheBackend(ABC, Generic[T]):
    """Abstract cache backend interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        """Retrieve value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: T, ttl: int = 300) -> bool:
        """Store value in cache with TTL (seconds)"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all keys from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass
    
    def _serialize(self, value: T) -> str:
        """Serialize value to JSON"""
        return json.dumps(value, default=str)
    
    def _deserialize(self, data: str) -> T:
        """Deserialize JSON to value"""
        return json.loads(data)
```

**File**: `lambda/guardian/cache/redis.py`
```python
import redis.asyncio as redis
from .base import CacheBackend
import logging

logger = logging.getLogger(__name__)

class RedisCache(CacheBackend):
    """Redis-backed cache implementation"""
    
    def __init__(self, redis_url: str, fallback_memory_cache=None):
        self.redis_url = redis_url
        self.pool = None
        self.fallback = fallback_memory_cache
        self.connected = False
    
    async def connect(self):
        """Establish Redis connection pool"""
        try:
            self.pool = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self.pool.ping()
            self.connected = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using fallback.")
            self.connected = False
    
    async def get(self, key: str):
        """Get value from Redis with fallback"""
        try:
            if not self.connected:
                return None
            
            data = await self.pool.get(key)
            if data:
                return self._deserialize(data)
            return None
        except Exception as e:
            logger.warning(f"Redis GET failed: {e}. Trying fallback.")
            if self.fallback:
                return await self.fallback.get(key)
            return None
    
    async def set(self, key: str, value, ttl: int = 300) -> bool:
        """Set value in Redis with fallback"""
        try:
            if not self.connected:
                if self.fallback:
                    return await self.fallback.set(key, value, ttl)
                return False
            
            serialized = self._serialize(value)
            result = await self.pool.setex(key, ttl, serialized)
            return bool(result)
        except Exception as e:
            logger.warning(f"Redis SET failed: {e}. Trying fallback.")
            if self.fallback:
                return await self.fallback.set(key, value, ttl)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            if not self.connected:
                return False
            result = await self.pool.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all keys (use with caution)"""
        try:
            if not self.connected:
                return False
            await self.pool.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis CLEAR failed: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            if not self.connected:
                return False
            result = await self.pool.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS failed: {e}")
            return False
    
    async def close(self):
        """Close Redis connection pool"""
        if self.pool:
            await self.pool.close()
            self.connected = False
```

**Step 3: CacheFactory** (~30 min)

**File**: `lambda/guardian/cache/__init__.py`
```python
from .base import CacheBackend
from .memory import MemoryCache
from .redis import RedisCache
import os
import logging

logger = logging.getLogger(__name__)

class CacheFactory:
    _cache_instance = None
    
    @staticmethod
    def create(backend: str = None) -> CacheBackend:
        """Factory method to create cache backend"""
        if CacheFactory._cache_instance:
            return CacheFactory._cache_instance
        
        backend = backend or os.getenv('CACHE_BACKEND', 'memory')
        
        if backend == 'redis':
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                logger.warning("REDIS_URL not set. Falling back to memory cache.")
                CacheFactory._cache_instance = MemoryCache()
            else:
                # Create memory cache as fallback
                fallback = MemoryCache()
                CacheFactory._cache_instance = RedisCache(redis_url, fallback)
        else:
            CacheFactory._cache_instance = MemoryCache()
        
        return CacheFactory._cache_instance
```

---

### 2.2 aioboto3 Migration

**Step 1: Update Dependencies** (~15 min)

**File**: `lambda/requirements.txt`
```diff
boto3==1.28.0
+ aioboto3==12.0.0
botocore==1.31.0
```

**Step 2: Update AWSClientProvider** (~1 hour)

**File**: `lambda/guardian/aws_client_provider.py`
```python
import aioboto3
import os
import logging

logger = logging.getLogger(__name__)

class AWSClientProvider:
    _session = None
    
    @staticmethod
    def get_session():
        """Get or create aioboto3 session"""
        if AWSClientProvider._session is None:
            AWSClientProvider._session = aioboto3.Session(
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
        return AWSClientProvider._session
    
    @staticmethod
    async def get_client(service: str):
        """Get async client for service"""
        session = AWSClientProvider.get_session()
        return session.client(service)
    
    @staticmethod
    async def get_resource(service: str):
        """Get async resource for service"""
        session = AWSClientProvider.get_session()
        return session.resource(service)
    
    @staticmethod
    def clear_session():
        """Clear cached session"""
        AWSClientProvider._session = None
```

**Step 3: Update Checkers** (~2 hours)

**Pattern**: Update each checker to use async context managers

**Before** (boto3):
```python
class EC2Checker(BaseChecker):
    def __init__(self):
        self.ec2_client = boto3.client('ec2')
    
    def check(self):
        response = self.ec2_client.describe_instances()
        return CheckResult(...)
```

**After** (aioboto3):
```python
class EC2Checker(BaseChecker):
    async def check_async(self):
        async with aioboto3.client('ec2') as client:
            response = await client.describe_instances()
        return CheckResult(...)
    
    def check(self):
        # Fallback for sync calls (keep for backward compat)
        # Use asyncio.run() if needed
        ...
```

**Checkers to Update**:
- CostChecker
- EC2Checker
- S3Checker
- CloudTrailChecker
- IAMChecker
- GuardDutyChecker

---

### 2.3 Multi-Account Support

**Step 1: IAM Cross-Account Setup** (~30 min)

**Terraform**: `terraform/cross_account_iam.tf`
```hcl
# In target account, create role that primary account can assume
resource "aws_iam_role" "guardian_monitor" {
  name = "guardian-monitor-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${var.primary_account_id}:role/guardian-lambda-role"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "guardian_monitor_policy" {
  role       = aws_iam_role.guardian_monitor.name
  policy_arn = aws_iam_policy.guardian_permissions.arn
}
```

**Step 2: Update Orchestrator** (~1 hour)

**File**: `lambda/guardian/orchestrator.py`
```python
import aioboto3

class GuardianOrchestrator:
    async def run_all_checks(self, event: dict):
        """Run checks across multiple accounts"""
        account_ids = event.get('account_ids', [os.getenv('AWS_ACCOUNT_ID')])
        
        results_by_account = {}
        for account_id in account_ids:
            try:
                # Assume role in target account
                sts_client = aioboto3.client('sts')
                assumed_role = await self._assume_role(sts_client, account_id)
                
                # Create clients with assumed role credentials
                clients = self._create_clients_with_credentials(assumed_role)
                
                # Run checks in target account
                results = await self._run_checks_in_account(
                    account_id, clients, event
                )
                results_by_account[account_id] = results
            except Exception as e:
                logger.error(f"Failed to check account {account_id}: {e}")
                results_by_account[account_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Aggregate results
        return self._aggregate_multi_account_results(results_by_account)
    
    async def _assume_role(self, sts_client, account_id: str):
        """Assume role in target account"""
        role_arn = f"arn:aws:iam::{account_id}:role/guardian-monitor-role"
        
        response = await sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"guardian-session-{account_id}"
        )
        
        return response['Credentials']
    
    def _aggregate_multi_account_results(self, results_by_account: dict):
        """Aggregate results from multiple accounts"""
        aggregated = {
            'accounts': results_by_account,
            'summary': {
                'total_alerts': 0,
                'accounts_checked': len(results_by_account),
                'alerts_by_severity': {}
            }
        }
        
        # Count alerts by severity
        for account_id, results in results_by_account.items():
            for check_result in results.get('checks', []):
                severity = check_result.get('severity', 'INFO')
                aggregated['summary']['alerts_by_severity'][severity] = \
                    aggregated['summary']['alerts_by_severity'].get(severity, 0) + 1
        
        return aggregated
```

---

## Phase 3: Testing & Verification (Session 4, ~2 hours)

### 3.1 Unit Tests (16 new tests)

**File**: `tests/test_redis_cache.py`
```python
import pytest
from guardian.cache.redis import RedisCache
from guardian.cache.memory import MemoryCache

class TestRedisCache:
    @pytest.mark.asyncio
    async def test_redis_get_set(self):
        """Test basic Redis set/get"""
        cache = RedisCache('redis://localhost:6379')
        await cache.connect()
        
        await cache.set('test_key', {'data': 'value'}, ttl=60)
        result = await cache.get('test_key')
        
        assert result == {'data': 'value'}
    
    @pytest.mark.asyncio
    async def test_redis_fallback_to_memory(self):
        """Test fallback to memory cache on Redis error"""
        memory_cache = MemoryCache()
        redis_cache = RedisCache('redis://invalid:0000', memory_cache)
        
        # Set should fallback to memory
        await redis_cache.set('key', 'value', ttl=60)
        result = await memory_cache.get('key')
        
        assert result == 'value'
    
    @pytest.mark.asyncio
    async def test_redis_ttl_expiration(self):
        """Test TTL expiration"""
        cache = RedisCache('redis://localhost:6379')
        await cache.set('expiring_key', 'value', ttl=1)
        
        # Should exist immediately
        assert await cache.exists('expiring_key')
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        assert not await cache.exists('expiring_key')
```

**File**: `tests/test_aioboto3_migration.py`
```python
import pytest
from guardian.checkers.ec2 import EC2Checker

class TestAioboto3Migration:
    @pytest.mark.asyncio
    async def test_ec2_checker_async(self):
        """Test EC2 checker uses aioboto3"""
        checker = EC2Checker()
        result = await checker.check_async()
        
        assert result.severity in ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    @pytest.mark.asyncio
    async def test_all_checkers_async(self):
        """Test all checkers support async"""
        checkers = [
            CostChecker(),
            EC2Checker(),
            S3Checker(),
            CloudTrailChecker(),
            IAMChecker(),
            GuardDutyChecker()
        ]
        
        results = await asyncio.gather(
            *[checker.check_async() for checker in checkers]
        )
        
        assert len(results) == 6
        assert all(r.severity in SEVERITY_LEVELS for r in results)
```

**File**: `tests/test_multi_account.py`
```python
import pytest
from guardian.orchestrator import GuardianOrchestrator

class TestMultiAccount:
    @pytest.mark.asyncio
    async def test_multi_account_event(self):
        """Test multi-account event handling"""
        event = {
            'check_type': 'all',
            'account_ids': ['123456789012', '210987654321']
        }
        
        orchestrator = GuardianOrchestrator()
        result = await orchestrator.run_all_checks(event)
        
        assert 'accounts' in result
        assert len(result['accounts']) == 2
    
    @pytest.mark.asyncio
    async def test_aggregation_summary(self):
        """Test results aggregation"""
        # Results from multiple accounts
        results = {
            'account1': {'severity': 'HIGH', 'checks': 3},
            'account2': {'severity': 'INFO', 'checks': 3}
        }
        
        aggregated = orchestrator._aggregate_multi_account_results(results)
        
        assert aggregated['summary']['accounts_checked'] == 2
```

### 3.2 Integration Tests

**Run existing 194+ test suite**:
```bash
# Unit tests
python3 -m pytest tests/test_*.py -v

# Lambda tests
python3 -m pytest tests/lambda/ -v

# All tests
python3 -m pytest tests/ --tb=short

# Expected: 200+/200+ passing (100%)
```

### 3.3 Performance Benchmarks

**File**: `tests/test_performance_v1.3.py`
```python
import time

class TestPerformanceV1_3:
    async def test_redis_cache_performance(self):
        """Benchmark Redis cache performance"""
        cache = RedisCache('redis://localhost:6379')
        
        # Warm-up
        await cache.set('bench_key', 'value')
        
        # Measure cache hit
        start = time.perf_counter()
        for _ in range(100):
            await cache.get('bench_key')
        elapsed = time.perf_counter() - start
        
        # Expected: ~0.5-1ms per hit (vs ~5ms for in-memory)
        assert elapsed / 100 < 0.01
    
    async def test_aioboto3_performance(self):
        """Benchmark aioboto3 vs boto3"""
        # Should be same or faster than boto3 due to async
        checker = EC2Checker()
        
        start = time.perf_counter()
        result = await checker.check_async()
        elapsed = time.perf_counter() - start
        
        # Expected: <1000ms per check
        assert elapsed < 1.0
    
    async def test_multi_account_parallelization(self):
        """Benchmark parallel multi-account checks"""
        # Run 3 accounts in parallel
        start = time.perf_counter()
        results = await asyncio.gather(
            check_account('account1'),
            check_account('account2'),
            check_account('account3')
        )
        elapsed = time.perf_counter() - start
        
        # Expected: ~3 seconds (parallel) not ~9 seconds (sequential)
        assert elapsed < 5.0
```

---

## Phase 4: Documentation (Part of Phase 3)

### 4.1 Technical Design Document

**File**: `docs/sprints/SPRINT_23_DESIGN.md` (To Create)

Content:
- Architecture diagrams
- Design trade-offs
- API schemas
- Deployment architecture
- Security considerations

### 4.2 Implementation Guides

**Files to Create**:
- `docs/REDIS_SETUP.md` - Redis configuration guide
- `docs/MULTI_ACCOUNT_GUIDE.md` - Multi-account setup
- `docs/AIOBOTO3_MIGRATION.md` - Migration reference

### 4.3 Sprint Completion Report

**File**: `docs/sprints/SPRINT_23_COMPLETION.md` (To Create at end)

---

## Success Criteria

### Code Quality ✅
- [ ] All 194+ tests passing (100%)
- [ ] No breaking changes to existing API
- [ ] Backward compatible (boto3 fallback)
- [ ] Type-safe (Python type hints)
- [ ] Properly documented

### Performance ✅
- [ ] Redis cache hit: <10ms (vs 50ms in-memory)
- [ ] aioboto3 checks: <1000ms per check
- [ ] Multi-account parallelization: ~3-4s (vs 10s+ sequential)
- [ ] Cold start: <2500ms (same as v1.2)

### Features ✅
- [ ] Redis integration working
- [ ] aioboto3 migration complete
- [ ] Multi-account support functional
- [ ] Graceful fallback handling
- [ ] Comprehensive error handling

### Documentation ✅
- [ ] Design document created
- [ ] Setup guides created
- [ ] Migration guide created
- [ ] Sprint completion report created
- [ ] API documentation updated

---

## Testing Strategy

### Unit Tests (90 tests)
- Cache backend tests (16 new tests)
- Checker async tests (6 new tests)
- Orchestrator multi-account tests (8 new tests)
- Existing tests (60 tests to verify no regression)

### Integration Tests (40+ tests)
- Redis + Lambda integration
- aioboto3 + AWS SDK tests
- Multi-account end-to-end
- Cache fallback scenarios
- Error handling paths

### Performance Tests (8 tests)
- Cache performance
- Checker performance
- Multi-account parallelization
- Cold start regression

### Total: 194+ tests, 100% pass rate target

---

## Time Estimates by Phase

| Phase | Duration | Tasks |
|-------|----------|-------|
| 1: Design | 2 hours | Architecture + design decisions |
| 2: Implementation | 6 hours | Redis (1.5h) + aioboto3 (2h) + multi-account (2h) + factory (0.5h) |
| 3: Testing | 1.5 hours | 90+ new tests + performance benchmarks |
| 4: Documentation | 1 hour | Design + setup + completion report |
| 5: Integration & Fixes | 1.5 hours | Integration testing + bug fixes |
| **Total** | **~12 hours** | **3-4 sessions** |

---

## Resources & References

**Redis Documentation**:
- AWS ElastiCache: https://docs.aws.amazon.com/elasticache/latest/userguide/
- redis-py: https://redis-py.readthedocs.io/

**aioboto3 Documentation**:
- GitHub: https://github.com/terrycain/aioboto3
- Docs: https://aioboto3.readthedocs.io/

**Python Async**:
- asyncio: https://docs.python.org/3/library/asyncio.html
- Type hints: https://peps.python.org/pep-0484/

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Redis connection failures | Availability | Fallback to in-memory cache |
| aioboto3 compatibility issues | Functionality | Keep boto3 as fallback |
| Multi-account role assumption fails | Coverage | Log errors, continue with other accounts |
| Test regression with new code | Quality | Comprehensive test suite (194+ tests) |
| Performance degradation | Performance | Benchmarks at each phase |

---

## Sign-Off Criteria

- [ ] All 194+ tests passing
- [ ] No performance regression
- [ ] Documentation complete
- [ ] Code reviewed and approved
- [ ] Ready for v1.3 release

---

**Status**: 📋 PLANNED  
**Previous Sprint**: Sprint 22 (v1.2 Released)  
**Next Sprint**: Sprint 24 (v1.3 Testing & Release)  
**Implementation**: Claude Code + User oversight

---

*Last Updated*: May 8, 2026  
*Duration*: 3-4 sessions, ~12 hours  
*Complexity*: High (3 major features)
