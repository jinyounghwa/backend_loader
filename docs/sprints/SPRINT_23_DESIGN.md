# Sprint 23 Architecture Design

**Status**: 📋 DESIGN PHASE  
**Date**: May 10, 2026  
**Scope**: Redis integration, aioboto3 migration, multi-account support  
**Duration**: Design phase (2 hours)

---

## 1. Redis Integration Architecture

### Problem Statement
- **Current**: In-memory cache stored only in Lambda process memory
- **Issue**: Cache lost when Lambda instance is recycled or horizontal scaling occurs
- **Target**: Persistent distributed cache across Lambda instances

### Solution Design

#### 1.1 Cache Architecture Pattern

```
┌─────────────────────────────────────────┐
│         CacheBackend (Abstract)         │
│  ├─ get(key) -> Optional[T]             │
│  ├─ set(key, value, ttl) -> None        │
│  ├─ delete(key) -> None                 │
│  └─ clear() -> None                     │
└─────────────────────────────────────────┘
         △                 △
         │                 │
    ┌────┴────┐      ┌─────┴─────┐
    │  Redis  │      │  InMemory  │
    │ Cache   │      │   Cache    │
    │(Primary)│      │ (Fallback) │
    └─────────┘      └───────────┘
```

#### 1.2 Implementation Strategy

**File Structure**:
```
lambda/guardian/cache/
├── __init__.py           # Factory pattern
├── base.py              # CacheBackend abstract class
├── redis.py             # RedisCache implementation
└── memory.py            # InMemoryCache (existing)
```

**CacheBackend Interface** (`lambda/guardian/cache/base.py`):
```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class CacheBackend(ABC):
    """Abstract cache backend interface."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value with TTL (seconds)."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear entire cache."""
        pass
```

**RedisCache Implementation** (`lambda/guardian/cache/redis.py`):

Key Features:
- Connect to AWS ElastiCache via `REDIS_URL` environment variable
- TTL support with Redis EXPIRE command
- Fallback to InMemoryCache if Redis unavailable
- JSON serialization for complex objects
- Error logging without breaking execution

```python
import json
import logging
from typing import Any, Optional
import redis
from guardian.cache.base import CacheBackend
from guardian.cache.memory import InMemoryCache

logger = logging.getLogger(__name__)

class RedisCache(CacheBackend):
    def __init__(self, redis_url: str, fallback: Optional[CacheBackend] = None):
        self.redis_url = redis_url
        self.fallback = fallback or InMemoryCache()
        self.redis = None
        self._connect()
    
    def _connect(self) -> None:
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed, using fallback: {e}")
            self.redis = None
    
    def get(self, key: str) -> Optional[Any]:
        if self.redis:
            try:
                value = self.redis.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.error(f"Redis get failed for {key}: {e}")
                return self.fallback.get(key)
        return self.fallback.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self.redis:
            try:
                self.redis.setex(key, ttl, json.dumps(value))
            except Exception as e:
                logger.error(f"Redis set failed for {key}: {e}")
                self.fallback.set(key, value, ttl)
        else:
            self.fallback.set(key, value, ttl)
    
    def delete(self, key: str) -> None:
        if self.redis:
            try:
                self.redis.delete(key)
            except Exception as e:
                logger.error(f"Redis delete failed for {key}: {e}")
        self.fallback.delete(key)
    
    def clear(self) -> None:
        if self.redis:
            try:
                self.redis.flushdb()
            except Exception as e:
                logger.error(f"Redis clear failed: {e}")
        self.fallback.clear()
```

#### 1.3 Configuration & Deployment

**Environment Variables**:
```bash
CACHE_BACKEND=redis          # or 'memory'
REDIS_URL=redis://redis:6379 # ElastiCache endpoint
CACHE_TTL=300                # Default TTL in seconds
```

**AWS ElastiCache Setup**:
- Tier: `cache.t3.micro` (free tier eligible, ~$15/month)
- Engine: Redis 7.0
- Multi-AZ: Enabled (auto-failover)
- Encryption at rest: Enabled
- Security group: Allow Lambda port 6379

**Cost Analysis**:
- AWS ElastiCache: ~$15/month (t3.micro)
- Fallback: Zero additional cost if Redis unavailable
- Performance: Cache hit time 10ms (Redis) vs 50ms+ (DynamoDB)

#### 1.4 Cache Invalidation Strategy

**TTL-based (Primary)**:
- Default: 5 minutes for check results
- Status API: 2 minutes (more volatile)
- Account list: 1 hour (stable)

**Event-based (Secondary)**:
- Clear cache on remediation action
- Clear on cost threshold change
- Clear on account add/remove

**Manual (Admin)**:
- `?cache=false` query parameter to bypass
- Clear endpoint in admin API

---

## 2. aioboto3 Migration Strategy

### Problem Statement
- **Current**: boto3 with thread pool executor (ThreadPoolExecutor for I/O)
- **Issue**: Thread pool adds overhead, not true async
- **Target**: Pure async I/O with aioboto3

### Solution Design

#### 2.1 Migration Pattern

**Current Pattern** (boto3):
```python
# Synchronous, uses thread pool in Lambda
client = AWSClientProvider.get_client("ec2", "us-east-1")
response = client.describe_instances()
```

**Target Pattern** (aioboto3):
```python
# True async with context manager
async with aioboto3.Session().client("ec2", region_name="us-east-1") as client:
    response = await client.describe_instances()
```

#### 2.2 AWSClientProvider Changes

**New aioboto3 Session Management**:
```python
class AWSClientProvider:
    _aioboto3_session: Optional[aioboto3.Session] = None
    
    @classmethod
    def get_aioboto3_session(cls) -> aioboto3.Session:
        """Get or create aioboto3 session."""
        if cls._aioboto3_session is None:
            boto3_kwargs = Config.get_boto3_kwargs()
            cls._aioboto3_session = aioboto3.Session(**boto3_kwargs)
        return cls._aioboto3_session
    
    @classmethod
    async def get_async_client(cls, service_name: str, region: Optional[str] = None):
        """Get async client as context manager."""
        session = cls.get_aioboto3_session()
        kwargs = {}
        if region:
            kwargs["region_name"] = region
        
        boto3_kwargs = Config.get_boto3_kwargs()
        if "endpoint_url" in boto3_kwargs:
            kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]
        
        return session.client(service_name, **kwargs)
```

#### 2.3 Checker Migration Pattern

**Example: EC2Checker** (before → after):

**Before**:
```python
class EC2Checker(BaseChecker):
    def check(self) -> List[CheckResult]:
        client = AWSClientProvider.get_client("ec2")
        response = client.describe_instances()
        # ... process instances
```

**After**:
```python
class EC2Checker(BaseChecker):
    async def check_async(self) -> List[CheckResult]:
        async with AWSClientProvider.get_async_client("ec2") as client:
            response = await client.describe_instances()
            # ... process instances
```

#### 2.4 Migration Order

Priority order (simplest → most complex):

1. **CostChecker** (1 API call)
   - Single DescribeAccountBilling → describe_billing_period
   
2. **S3Checker** (2 API calls)
   - List buckets + get bucket ACL per bucket
   
3. **EC2Checker** (Multi-region parallelization)
   - describe_instances per region
   - Uses asyncio.gather for region parallelization
   
4. **CloudTrailChecker** (Paginated API)
   - Lookup events with pagination
   
5. **IAMChecker** (Nested operations)
   - List users → get user policies → list attached policies
   
6. **GuardDutyChecker** (Complex aggregation)
   - List findings with multiple filters + get finding details

#### 2.5 BaseChecker Updates

**New Abstract Methods**:
```python
class BaseChecker(ABC):
    @abstractmethod
    async def check_async(self) -> List[CheckResult]:
        """Async check implementation."""
        pass
    
    def check(self) -> List[CheckResult]:
        """Sync wrapper for backward compatibility."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # In Lambda context
            return asyncio.run(self.check_async())
        else:
            return asyncio.run(self.check_async())
```

#### 2.6 Performance Impact Analysis

**Expected Improvements**:

| Metric | v1.2 (boto3 + ThreadPool) | v1.3 (aioboto3) | Gain |
|--------|---------------------------|-----------------|------|
| Single region check | 300ms | 250ms | 50ms faster |
| Multi-region (4x) | 3000ms | 2000ms | 1s faster (true parallelization) |
| 6 checkers parallel | 3500ms | 2500ms | 1s faster |
| Lambda overhead | ~400ms | ~300ms | 100ms faster |

**Reason**: Thread pool context switching eliminated, pure async I/O

#### 2.7 Dependencies

**Add to `lambda/requirements.txt`**:
```
aioboto3>=11.4.0  # Latest stable
```

---

## 3. Multi-Account Support Design

### Problem Statement
- **Current**: Monitor only current AWS account
- **Issue**: Organizations with multiple accounts need unified monitoring
- **Target**: Monitor N accounts simultaneously, aggregate results

### Solution Design

#### 3.1 Architecture Pattern

```
┌──────────────────────────────────────┐
│      Primary Account (Guardian)      │
│  - STS AssumeRole cross-account role │
│  - Orchestrator runs checkers × N    │
└──────────────────────────────────────┘
         │
         ├──→ [Account A] (AssumeRole → temp creds)
         ├──→ [Account B] (AssumeRole → temp creds)
         ├──→ [Account C] (AssumeRole → temp creds)
         └──→ [Account D] (AssumeRole → temp creds)
         
Results aggregated by account → Dashboard/Alerts
```

#### 3.2 STS AssumeRole Pattern

**Cross-Account IAM Role** (target account setup):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::PRIMARY_ACCOUNT:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Role Permissions** (read-only):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:Get*",
        "s3:List*",
        "ce:GetCostAndUsage",
        "cloudtrail:LookupEvents",
        "iam:Get*",
        "iam:List*",
        "guardduty:Get*",
        "guardduty:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 3.3 AWSClientProvider Updates

**Cross-Account Credential Management**:

```python
class AWSClientProvider:
    @classmethod
    async def assume_role_async(
        cls,
        account_id: str,
        role_name: str = "GuardianCrossAccountRole",
        session_duration: int = 3600,
    ) -> Dict[str, str]:
        """Assume role in target account, return temporary credentials."""
        async with cls.get_async_client("sts") as sts_client:
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
            response = await sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f"guardian-{account_id}",
                DurationSeconds=session_duration,
            )
            
            credentials = response["Credentials"]
            return {
                "aws_access_key_id": credentials["AccessKeyId"],
                "aws_secret_access_key": credentials["SecretAccessKey"],
                "aws_session_token": credentials["SessionToken"],
            }
    
    @classmethod
    async def get_async_client_for_account(
        cls,
        service_name: str,
        account_id: str,
        region: Optional[str] = None,
    ):
        """Get async client for cross-account access."""
        credentials = await cls.assume_role_async(account_id)
        
        session = aioboto3.Session(
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            aws_session_token=credentials["aws_session_token"],
        )
        
        kwargs = {}
        if region:
            kwargs["region_name"] = region
        
        return session.client(service_name, **kwargs)
```

#### 3.4 Orchestrator Changes

**Multi-Account Check Execution**:

```python
class GuardianOrchestrator:
    async def run_checks_for_accounts(
        self,
        account_ids: List[str],
        check_type: str = "all",
    ) -> Dict[str, Any]:
        """Run all checks across multiple accounts."""
        
        # Create checker tasks for each account
        tasks = []
        for account_id in account_ids:
            task = self._run_checks_for_account(account_id, check_type)
            tasks.append(task)
        
        # Execute in parallel
        results_by_account = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        aggregated = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "accounts": {},
            "summary": {}
        }
        
        for account_id, results in zip(account_ids, results_by_account):
            if isinstance(results, Exception):
                aggregated["accounts"][account_id] = {
                    "status": "error",
                    "error": str(results)
                }
            else:
                aggregated["accounts"][account_id] = results
        
        return aggregated
    
    async def _run_checks_for_account(
        self,
        account_id: str,
        check_type: str,
    ) -> Dict[str, Any]:
        """Run checks in single account."""
        # For each checker, pass account_id
        # Checker uses AWSClientProvider.get_async_client_for_account()
        # ...
```

#### 3.5 Event Parameter Format

**Lambda Event** (multi-account):
```json
{
  "check_type": "all",
  "account_ids": ["123456789012", "987654321098"],
  "time": "2026-05-10T12:00:00Z"
}
```

**Or from Organizations**:
```json
{
  "check_type": "all",
  "organization_mode": true,
  "time": "2026-05-10T12:00:00Z"
}
```

#### 3.6 Error Handling Strategy

**Account-Level Failures**:
- One account fails → log error, continue with others
- Partial results returned (succeeded accounts + errors)

**Cross-Account Role Issues**:
- AssumeRole fails → cached credentials? → in-memory client?
- Return error for that account, don't crash

**Network Issues**:
- Timeout on checker → async timeout wrapper
- Don't wait > 60s per account

---

## 4. Integration Points

### 4.1 Cache Integration with Checkers

- Checkers inject CacheBackend on init
- Check result: check cache before API calls
- Cache invalidation: on remediation action

### 4.2 aioboto3 Integration with BaseChecker

- All checkers override `check_async()`
- Orchestrator calls `check_async()` (not `check()`)
- Backward compatibility: `check()` wrapper still works

### 4.3 Multi-Account Integration with Orchestrator

- Orchestrator receives account_ids in event
- Spawns parallel tasks per account
- Aggregates results with account labels

---

## 5. Testing Strategy

### 5.1 Redis Cache Tests (6 tests)
- ✅ Connect to Redis
- ✅ Get/set values with TTL
- ✅ Fallback to in-memory on connection failure
- ✅ Clear cache
- ✅ Serialization/deserialization
- ✅ Error logging

### 5.2 aioboto3 Migration Tests (6 tests)
- ✅ EC2Checker async execution
- ✅ S3Checker async execution
- ✅ CostChecker async execution
- ✅ Parallel region execution
- ✅ Exception handling in gather()
- ✅ Performance improvement validation

### 5.3 Multi-Account Tests (8 tests)
- ✅ STS AssumeRole success
- ✅ AssumeRole failure handling
- ✅ Parallel account execution
- ✅ Result aggregation
- ✅ Mixed success/failure accounts
- ✅ Organization mode detection
- ✅ Cache per account
- ✅ Timeout on slow account

---

## 6. Rollout Plan

### Phase 2a: Redis Integration (1.5 hours)
1. Create cache abstract interface
2. Implement RedisCache with fallback
3. Add factory pattern
4. Test with mock Redis

### Phase 2b: aioboto3 Migration (2 hours)
1. Update AWSClientProvider for async
2. Migrate checkers (simplest → complex)
3. Update Orchestrator for async gather
4. Test performance improvements

### Phase 2c: Multi-Account Support (2 hours)
1. Add AssumeRole to AWSClientProvider
2. Update Orchestrator for account parallelization
3. Add account aggregation logic
4. Test with mock STS

### Phase 3: Testing & Verification (2 hours)
- 16+ new cache tests
- 6+ new aioboto3 tests
- 8+ new multi-account tests
- Performance validation
- No regressions

---

## 7. Success Criteria

### Code Quality
- ✅ All new code passes mypy strict mode
- ✅ 100% test coverage on new modules
- ✅ No deprecation warnings

### Performance
- ✅ Cache hit time: < 10ms (Redis) vs 50ms+ (DynamoDB)
- ✅ aioboto3 checks: ±0% vs boto3 (same speed, true async)
- ✅ Multi-account (3x): < 5s total (parallel)

### Functionality
- ✅ Redis fallback to in-memory works
- ✅ Cross-account AssumeRole succeeds
- ✅ Results aggregated correctly by account

---

## 8. Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Redis unavailable | Cache misses | Fallback to in-memory (5x slower but functional) |
| ElastiCache costs | $15+/month | Can disable Redis, use in-memory only |
| AssumeRole fails | Account unchecked | Log error, continue with other accounts |
| aioboto3 bug | All checks break | Keep boto3 as fallback, gradual rollout |
| Cascading timeouts | Slow checks block others | Parallel execution with per-account timeout |

---

## Next Steps

**Phase 1 Approval**: Review this design document
- [ ] Redis architecture approved
- [ ] aioboto3 migration strategy approved
- [ ] Multi-account design approved

**Phase 2 Ready**: Begin implementation
- Start with simplest components
- Test each piece independently
- Integrate gradually

---

**Design Completed**: May 10, 2026  
**Status**: ✅ Ready for Phase 2 Implementation  
**Session Duration**: ~2 hours
