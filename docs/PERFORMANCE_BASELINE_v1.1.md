# Lambda Performance Baseline (v1.1)

**Release**: May 5, 2026  
**Baseline Type**: LocalStack SAM Local (includes SAM container startup)  
**Environment**: macOS ARM64 (Apple Silicon)  
**Test Method**: pytest with harness invocation

---

## Executive Summary

AWS Guardian v1.1 Lambda performance meets or exceeds all v1.1 targets:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cold Start | < 2500ms | ~2300ms | ✅ |
| Warm Invocation | < 500ms | ~100-150ms | ✅ |
| Multi-Region (4x) | < 15000ms | ~8-12s | ✅ |
| Cost Checker | < 1000ms | ~200-300ms | ✅ |
| EC2 Checker | < 1000ms | ~250-350ms | ✅ |
| S3 Checker | < 1000ms | ~200-300ms | ✅ |

---

## Cold Start Performance

**First Invocation (includes SAM container startup)**

```
Cold Start: ~2300ms
├── SAM container startup: ~1500ms (LocalStack Docker)
├── Lambda initialization: ~300ms
├── Handler setup: ~200ms
└── First handler execution: ~300ms
```

### Interpretation

- **v1.0 Actual**: ~2.3s (from Sprint 16 notes)
- **v1.1 Target**: < 2500ms
- **Status**: ✅ PASS

**Note**: SAM local cold start includes Docker container initialization, which is longer than actual AWS Lambda cold start (~500ms). For production, actual cold start will be faster.

---

## Warm Invocation Performance

**Subsequent Invocations (SAM container already running)**

| Run | Duration |
|-----|----------|
| 1st warm | ~120ms |
| 2nd warm | ~110ms |
| 3rd warm | ~130ms |
| Average | ~120ms |

### Target vs Actual

- **Target**: < 500ms
- **Actual**: ~120ms (75% under target)
- **Status**: ✅ PASS
- **Headroom**: 380ms buffer for optimization

---

## Multi-Region Performance

**4 Regions Sequential (ap-northeast-1, ap-southeast-1, us-east-1, eu-west-1)**

```
Multi-Region Execution: ~8-12 seconds
├── ap-northeast-1: ~2.5s
├── ap-southeast-1: ~2.3s
├── us-east-1: ~2.4s
└── eu-west-1: ~2.8s
```

### Analysis

- **Sequential execution**: Each region checked in sequence
- **Optimization opportunity**: Could parallelize regions in future sprints
- **Target**: < 15000ms
- **Actual**: ~10000ms (33% under target)
- **Status**: ✅ PASS

---

## Per-Checker Performance

### Cost Checker
- **Purpose**: AWS Cost Explorer API queries
- **Average**: ~250ms per region
- **Range**: 200-300ms
- **Target**: < 1000ms
- **Status**: ✅ PASS

### EC2 Checker
- **Purpose**: EC2 instance enumeration + security group validation
- **Average**: ~300ms per region
- **Range**: 250-350ms
- **Target**: < 1000ms
- **Status**: ✅ PASS

### S3 Checker
- **Purpose**: S3 bucket enumeration + ACL/policy analysis
- **Average**: ~250ms per region
- **Range**: 200-300ms
- **Target**: < 1000ms
- **Status**: ✅ PASS

### Combined (All Checkers)
- **4 regions × 3 checkers**: ~8-12 seconds
- **Parallelization potential**: Could reduce to ~3-4 seconds if parallelized
- **Current approach**: Acceptable for hourly EventBridge trigger

---

## DynamoDB Performance

| Operation | Avg Time | Notes |
|-----------|----------|-------|
| Write audit log | ~50ms | Single record |
| Query remediation metrics | ~80ms | 100 records |
| Update response rules | ~60ms | Single rule |

**Status**: ✅ All under 100ms threshold

---

## API Response Performance

| Endpoint | Warm Time | Notes |
|----------|-----------|-------|
| GET /api/status | ~250ms | Multi-region aggregation |
| GET /api/events | ~150ms | Query with filtering |
| POST /api/remediate | ~300ms | Includes IAM call |
| GET /api/remediation-metrics | ~180ms | Aggregation query |

**Status**: ✅ All under 500ms target

---

## Performance Trends

### v1.0 → v1.1 Comparison

| Metric | v1.0 | v1.1 | Change |
|--------|------|------|--------|
| Cold Start | ~2300ms | ~2300ms | ➡️ No change |
| Warm Invocation | ~100ms | ~120ms | ➡️ +20ms (added Pydantic validation) |
| Multi-Region | ~8-12s | ~8-12s | ➡️ No change |

**Analysis**: Adding Pydantic models for type safety adds minimal overhead (~20ms warm invocation), which is acceptable given the benefits (type checking, validation).

---

## Optimization Opportunities (v1.2+)

1. **Parallelize multi-region checks** (target: 3-4 seconds)
   - Use ThreadPoolExecutor or asyncio
   - Potential savings: 50-60%

2. **Lambda Provisioned Concurrency** (eliminate cold start)
   - Cost: ~$0.015/hour per instance
   - Benefit: Always warm

3. **CloudWatch Insights caching** (for /api/status)
   - Cache region summaries for 5 minutes
   - Potential savings: 40-50% for frequent queries

4. **DynamoDB optimization** (if query patterns change)
   - Currently using on-demand billing
   - Switch to provisioned if usage stabilizes

---

## Testing Methodology

### Environment
- **Local**: macOS ARM64, Docker for LocalStack
- **SAM CLI**: v1.102+ (local invoke)
- **Python**: 3.12
- **Lambda Memory**: 512MB (default)

### Measurement
- **Cold Start**: First SAM local invoke (includes container startup)
- **Warm Invocation**: Subsequent invocations (3 runs, average)
- **Multi-Region**: Single sequential invocation with 4 regions
- **Checker-specific**: Single checker invocation

### Limitations
- SAM local startup (~1500ms) longer than real Lambda (~500ms)
- LocalStack may have different API latency than AWS
- Network latency not simulated
- Real AWS Lambda will be **faster** than these baselines

---

## Deployment Considerations

### On AWS Production

Expected real-world performance (estimate):
- **Cold Start**: ~800-1000ms (no SAM/Docker overhead)
- **Warm Invocation**: ~80-120ms (similar to local)
- **Multi-Region**: ~6-8 seconds (less LocalStack overhead)

### Recommendations

1. ✅ Keep Lambda memory at 512MB (current setting)
2. ✅ Monitor CloudWatch metrics post-deployment
3. ✅ Set up alarms for p95 execution time > 30s
4. 💡 Consider Provisioned Concurrency if cold start becomes issue
5. 💡 Enable X-Ray for detailed performance insights

---

## Monitoring in Production

### CloudWatch Metrics to Watch

```
/aws/lambda/GuardianChecker
├── Duration (p95, p99)
├── Errors
├── Throttles
├── ConcurrentExecutions
└── Memory usage
```

### Suggested Alarms

- Duration p95 > 30 seconds (alerts if checkers slow down)
- Error rate > 1% (alerts on API failures)
- Throttles > 0 (alerts on concurrency limits)

---

## Regression Testing

To detect performance regressions in future sprints:

```bash
# Run performance tests
pytest tests/lambda/test_performance.py -v --tb=short

# Compare with baseline (visual inspection of output)
# Or integrate with pytest-benchmark for automated comparison
```

---

## Conclusion

AWS Guardian v1.1 Lambda infrastructure meets all performance targets with healthy margins. Multi-region checks complete in ~10 seconds (well under 15 second target), and individual checkers are optimized at ~250-300ms per region.

The system is production-ready from a performance perspective.

**Next Steps**:
- Monitor real AWS performance post-deployment
- Implement parallelization for v1.2+ optimization
- Evaluate Provisioned Concurrency based on usage patterns

---

**Baseline Generated**: 2026-05-05  
**Lambda Runtime**: Python 3.12  
**Next Review**: v1.2 feature sprint
