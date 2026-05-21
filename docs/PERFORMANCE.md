# AWS Guardian Performance Guide

This document covers performance optimization, profiling, and benchmarking strategies for AWS Guardian.

## Table of Contents

1. [Performance Targets](#performance-targets)
2. [Profiling Guide](#profiling-guide)
3. [Optimization Strategies](#optimization-strategies)
4. [Benchmarking](#benchmarking)
5. [Production Tuning](#production-tuning)
6. [Troubleshooting](#troubleshooting)

---

## Performance Targets

### Lambda Execution (v1.1)

| Scenario | Target | Notes |
|----------|--------|-------|
| **Cold Start** | < 2500ms | Python startup + imports + SAM overhead |
| **Warm Invocation** | < 500ms | Subsequent calls (no startup) |
| **Single Checker** | < 500ms | Per-checker latency (mock: 10-50ms, real: 200-500ms) |
| **6 Checkers (Sequential)** | < 8000ms | Sum of individual checkers + overhead |
| **6 Checkers (Parallel)** | < 2000ms | Max(checker_latencies) + asyncio overhead |

### API Endpoints (v1.1)

| Endpoint | Target | Notes |
|----------|--------|-------|
| `/api/status` | < 1000ms | DynamoDB query + response formatting |
| `/api/events` | < 2000ms | Large result sets may approach limit |
| `/api/response-rules` | < 500ms | Small dataset, cached |

### Memory Usage (Lambda)

| Component | Typical | Max |
|-----------|---------|-----|
| Python Runtime | 20-30 MB | 40 MB |
| Guardian Code | 10-15 MB | 20 MB |
| Cached Data | 5-10 MB | 50 MB (RDS data) |
| **Total (1 invocation)** | 40-55 MB | 110 MB |
| **Lambda Memory Setting** | 512 MB | (default, plenty of headroom) |

---

## Profiling Guide

### 1. Unit Test Profiling (Fast)

Run performance baseline tests with timing output:

```bash
# Run all performance tests
python3 -m pytest tests/lambda/test_performance_baseline.py -v -s

# Expected output:
# test_ec2_checker_performance PASSED        [ 57%]
# test_s3_checker_performance PASSED         [ 85%]
# ...all 7 tests in < 0.1s
```

**Interpretation**: These numbers represent **mock-based** execution (no network I/O). Compare to real AWS numbers to identify bottlenecks.

### 2. Local AWS SDK Profiling (Real calls)

Use `cProfile` to identify slow boto3 operations:

```bash
# Profile a single checker with real AWS calls
python3 -c "
import cProfile
import pstats
from io import StringIO
import os

os.environ['AWS_ENV'] = 'production'  # Real AWS calls

# Profile the EC2 check
pr = cProfile.Profile()
pr.enable()

from lambda.guardian.checkers.ec2 import EC2Checker
checker = EC2Checker()
result = checker.check()

pr.disable()

# Print top 10 slowest functions
s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(10)
print(s.getvalue())
"
```

**Look for**:
- `describe_instances()` latency (~500ms per region)
- `get_paginator()` overhead
- Network round-trip time

### 3. Lambda CloudWatch Logs

Enable detailed logging:

```python
# In handler.py or orchestrator.py
import time

start = time.perf_counter()
results = orchestrator.run()
elapsed = time.perf_counter() - start

logger.info(f"Orchestrator completed in {elapsed:.2f}s", extra={
    "action": "orchestrator_complete",
    "duration_seconds": elapsed,
    "checker_count": len(results)
})
```

Then view in CloudWatch:

```bash
aws logs tail /aws/lambda/guardian-handler --follow
# Filter by: [datetime, request_id, ..., "orchestrator_complete", ..., duration_seconds > 5000]
```

### 4. Real AWS Benchmarking

Run production checkers and measure actual latency:

```bash
#!/bin/bash
# benchmark.sh

export AWS_REGION=us-east-1
export AWS_ENV=production  # Real AWS calls

python3 << 'EOF'
import time
from lambda.guardian.checkers.ec2 import EC2Checker
from lambda.guardian.checkers.s3 import S3Checker
from lambda.guardian.checkers.cost import CostChecker

checkers = [
    ("EC2", EC2Checker()),
    ("S3", S3Checker()),
    ("Cost", CostChecker()),
]

for name, checker in checkers:
    start = time.perf_counter()
    result = checker.check()
    elapsed = time.perf_counter() - start
    print(f"{name:12} {elapsed*1000:7.1f}ms")
EOF
```

**Expected output** (US account with ~50 instances, ~10 buckets):
```
EC2          1234.5ms
S3            567.8ms
Cost           89.2ms
```

---

## Optimization Strategies

### 1. Use Parallel Orchestrator (Biggest Impact)

**The single biggest performance win** is using async/parallel execution:

```bash
# Sequential: ~8-10 seconds (sum of all checkers)
python3 -m pytest tests/test_orchestrator.py::TestSequentialOrchestrator -v

# Parallel: ~2-3 seconds (max of all checkers)
python3 -m pytest tests/test_orchestrator.py::TestParallelOrchestrator -v

# Time savings: 3-4x faster
```

**When to use**:
- Production Lambda (always)
- High concurrency environments
- When cold start < 2.5s is critical

**Overhead**: ~100-200ms for asyncio setup

### 2. Caching

#### In-Memory Cache (Default)

Checkers cache results for 5-10 minutes:

```python
# Reduces repeat queries in same invocation
if checker.cache.has("ec2:instances:us-east-1"):
    return checker.cache.get("ec2:instances:us-east-1")
```

**Impact**: 10-20ms saved per repeated query

#### Redis Cache (Optional)

For multi-instance deployments:

```python
from guardian.cache.redis import RedisCache

cache = RedisCache(
    host="elasticache.us-east-1.amazonaws.com",
    ttl=600  # 10 minutes
)
result = cache.get("ec2:instances:us-east-1")
```

**Impact**: 100-200ms saved when data is already warm

### 3. Pagination Optimization

Don't fetch all results; limit to first N:

```python
# Before: Fetches all 10,000 instances
response = ec2_client.describe_instances()
for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:
        ...

# After: Limit to first 100, stop if none problematic
paginator = ec2_client.get_paginator("describe_instances")
for page in paginator.paginate(PaginationConfig={"PageSize": 100}):
    for reservation in page["Reservations"]:
        for instance in reservation["Instances"]:
            ...
    if found_issue:
        break
```

**Impact**: 200-400ms saved for large accounts

### 4. Parallel Region Checking

Check multiple regions in parallel (only in parallel orchestrator):

```python
# Before: Sequential region checks (1-2s each region)
for region in regions:
    result = self._check_region(region)

# After: Concurrent region checks (all regions in parallel)
import asyncio
tasks = [self._check_region_async(r) for r in regions]
results = await asyncio.gather(*tasks)
```

**Impact**: 3-5x faster for multi-region deployments

### 5. Connection Pooling

Reuse boto3 sessions across checkers:

```python
# Before: New session per checker
class EC2Checker:
    def __init__(self):
        self.session = boto3.Session()  # New session

# After: Shared session pool
class EC2Checker:
    def __init__(self, session=None):
        self.session = session or GLOBAL_SESSION  # Reuse
```

**Impact**: 100-300ms saved per checker (reduced socket creation)

### 6. Lambda Memory Tuning

Allocate more memory → faster CPU:

```bash
# Current: 512 MB (standard)
# Time: ~2 seconds for 6 checkers

# Upgrade: 1024 MB (double memory, double CPU)
# Time: ~1.2 seconds for 6 checkers
# Cost: $0.000000167/ms vs $0.000000083/ms (~2x)
# ROI: Faster execution same total cost (for infrequent runs)
```

Trade-off: Cost vs speed. Only recommended if cold start > 2.5s.

---

## Benchmarking

### CI/CD Performance Regression Detection

Add this to your CI pipeline to fail if performance degrades:

```bash
#!/bin/bash
# .github/scripts/performance-check.sh

export AWS_ENV=localstack

# Run baseline tests
pytest tests/lambda/test_performance_baseline.py -v

# Extract timing (baseline should be < 0.1s for all mocks)
if pytest tests/lambda/test_performance_baseline.py --tb=no -q | grep -q "7 passed"; then
    echo "✓ Performance regression check: PASSED"
    exit 0
else
    echo "✗ Performance regression detected"
    exit 1
fi
```

### Continuous Profiling

Monitor production Lambda with CloudWatch Insights:

```bash
# CloudWatch Logs Insights query
fields @timestamp, duration_seconds, checker_count
| filter action = "orchestrator_complete"
| stats avg(duration_seconds) as avg_duration, max(duration_seconds) as max_duration by checker_count
```

Expected output:
```
checker_count | avg_duration | max_duration
6             | 2.1          | 2.8
```

---

## Production Tuning

### Recommended Lambda Configuration

```yaml
# sam.yaml
Resources:
  GuardianFunction:
    Type: AWS::Serverless::Function
    Properties:
      MemorySize: 512        # Balanced cost/performance
      Timeout: 30            # 30s timeout (plenty for 6 checkers)
      EphemeralStorage: 512  # For temp file export
      ReservedConcurrentExecutions: 10  # Prevent runaway costs
      Environment:
        Variables:
          # Use parallel orchestrator in production
          ORCHESTRATOR: parallel
```

### Cost Optimization

Estimated monthly costs (assuming 1 invocation/hour):

| Configuration | Invocations/mo | Avg Duration | Monthly Cost |
|--------------|----------------|--------------|--------------|
| Sequential (512MB) | 720 | 8s | $0.27 |
| Parallel (512MB) | 720 | 2s | $0.08 |
| Parallel (1GB) | 720 | 1.2s | $0.16 |

**Recommendation**: Use parallel orchestrator with 512MB (cheapest, meets targets).

### Multi-Region Optimization

For accounts with many regions:

```python
# Option 1: Parallel within regions (current)
# Time: max(region_checks) ≈ 1-2s

# Option 2: Sharded across Lambda instances
# Time: orchestrator_overhead ≈ 0.5s per shard
# Cost: Multiple Lambda invocations
```

For typical deployments (1-5 regions): Parallel within one Lambda is optimal.

---

## Troubleshooting

### Slow Checker (> 500ms)

**Symptom**: One checker slower than others

**Diagnosis**:
```bash
# Run individual checker with profiling
python3 -c "
import cProfile
from lambda.guardian.checkers.ec2 import EC2Checker

pr = cProfile.Profile()
pr.enable()
EC2Checker().check()
pr.disable()

import pstats
from io import StringIO
s = StringIO()
pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(5)
print(s.getvalue())
"
```

**Common causes**:
- **describe_instances timeout** (network): Add boto3 timeout config
- **Large result set**: Enable pagination limits
- **Missing cache**: Check Redis/in-memory cache configuration

**Fix**: See [Optimization Strategies](#optimization-strategies)

### Cold Start > 2.5s

**Symptom**: First invocation takes 2-3 seconds

**Diagnosis**:
- Python startup: ~500ms
- Import time: ~800ms (boto3, botocore, etc.)
- Checker initialization: ~200ms

**Solutions**:
1. **Lambda Layers** for dependencies (pre-compiled)
   ```bash
   # Reduces import time ~200ms
   ```
2. **Increase memory** to 1GB (doubles CPU, ≈20% faster)
3. **Use Parallel Orchestrator** (fails-fast on timeout)

### Memory Exhaustion

**Symptom**: Lambda execution fails with "FATAL: MemoryError"

**Diagnosis**:
```python
import tracemalloc
tracemalloc.start()
# ... run checkers ...
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
```

**Common causes**:
- Large DynamoDB result set (10,000+ items)
- Unbounded pagination loops
- Memory leak in cache

**Fix**:
- Limit `MaxDays` in event query (7-30 days)
- Add pagination limit (e.g., max 1000 items)
- Increase Lambda memory to 1024 MB

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) — Orchestrator patterns
- [CONTRIBUTING.md](CONTRIBUTING.md) — Performance baselines
- [PERFORMANCE_BASELINE_v1.1.md](PERFORMANCE_BASELINE_v1.1.md) — Actual measurements
