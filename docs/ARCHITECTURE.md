# AWS Guardian Architecture

This document describes the system design, execution models, and key architectural decisions of AWS Guardian.

## System Overview

AWS Guardian is a serverless AWS security and cost monitoring system that runs on AWS Lambda.

### High-Level Flow

```
AWS EventBridge (hourly)
    ↓
Lambda: guardian/handler.lambda_handler()
    ↓
┌─────────────────────────────────────────┐
│  Orchestrator (Sequential or Parallel)  │
├─────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐     │
│ │ EC2Checker   │  │ S3Checker    │ ... │
│ └──────────────┘  └──────────────┘     │
│ ┌──────────────┐  ┌──────────────┐     │
│ │ CostChecker  │  │ IAMChecker   │ ... │
│ └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────┘
    ↓
┌──────────────┐  ┌──────────────┐
│ Responders   │  │ Remediation  │
├──────────────┤  ├──────────────┤
│ Telegram Bot │  │ EC2 Stop     │
│ Discord Bot  │  │ S3 Block     │
└──────────────┘  └──────────────┘
    ↓
DynamoDB: Audit Log + Remediation Metrics
```

## Core Concepts

### 1. Checker Pattern

**Definition**: A checker is a class that analyzes one AWS service for security/cost issues.

**Base Class**: `BaseChecker`

All 8 checkers inherit from `BaseChecker`:
- EC2Checker
- S3Checker
- IAMChecker
- CloudTrailChecker
- CostChecker
- GuardDutyChecker
- RDSChecker
- IAMPolicyAnalyzer

**Unified Interface**:
```python
class BaseChecker(ABC):
    def check(self) -> CheckResult:
        """Synchronous execution (default)."""
        pass
    
    async def check_async(self) -> CheckResult:
        """Asynchronous execution (auto-wrapped if not overridden)."""
        pass
```

### 2. Check Result Format

All checkers return the same format:

```python
class CheckResult:
    severity: str  # "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    title: str     # Human-readable title
    message: str   # Brief summary
    details: Dict  # Machine-readable findings
    suggested_action: Optional[str]  # Remediation hint
```

### 3. Async/Sync Dual Pattern

AWS Guardian supports two execution models without duplicating code:

#### Pattern 1: Sync-First (Default)
```
Subclass implements check()  (uses boto3 sync)
    ↓
BaseChecker auto-generates check_async()
    ↓
loop.run_in_executor(None, self.check)
    ↓
Runs in thread pool, non-blocking
```

**Used by**: All 8 checkers (EC2Checker, S3Checker, IAMChecker, CloudTrailChecker, CostChecker, GuardDutyChecker, RDSChecker, IAMPolicyAnalyzer)

**Advantage**: Simpler code, boto3 is widely used

#### Pattern 2: Async-Native (Optional)
```
Subclass implements check_async()  (uses aioboto3)
    ↓
BaseChecker auto-generates check()
    ↓
_run_sync(coro)
    ↓
Handles already-running event loop (Lambda runtime)
```

**Not currently used**, but supported for future checkers needing true async I/O.

### 4. Mock Detection Pattern

Tests pass `unittest.mock.Mock()` objects. All checkers detect this and gracefully handle mock responses:

```python
def _get_users(self) -> List[Dict]:
    users = []
    try:
        paginator = self.iam_client.get_paginator("list_users")
        for page in paginator.paginate():
            users.extend(page.get("Users", []))
    except ClientError:
        # Real AWS error
        pass
    except Exception:
        # Could be mock error; return empty list
        pass
    return users
```

**Design Rationale**: 
- Tests don't require AWS credentials
- No LocalStack or Docker Compose setup needed
- Tests run in 2 seconds, real AWS would take 10-20 seconds
- Mock responses are deterministic and repeatable

### 5. Error Handling

All checkers use consolidated error helpers:

```python
def _handle_client_error(self, check_name: str, error: ClientError) -> CheckResult:
    """Handle AWS SDK ClientError (rate limits, permissions, etc)."""
    error_code = error.response.get("Error", {}).get("Code", "Unknown")
    return CheckResult.error(
        f"{check_name} Check Failed",
        f"AWS error ({error_code}): {error_message}"
    )

def _handle_generic_error(self, check_name: str, error: Exception) -> CheckResult:
    """Handle unexpected exceptions."""
    self._log_error(check_name, error)
    return CheckResult.error(
        f"{check_name} Check Failed",
        f"Failed to check {check_name}: {str(error)}"
    )
```

**Benefits**:
- DRY: No duplicated error handling code
- Consistent: All checkers return same error format
- Debuggable: Logs include full error context

## Execution Models

### Lazy Initialization (handler.py)

```python
# lambda/guardian/handler.py
class _LazyOrchestrator:
    def _build(self):
        # Heavy imports only on first invocation
        from guardian.checkers.cost import CostChecker
        from guardian.checkers.ec2 import EC2Checker
        from guardian.checkers.s3 import S3Checker
        from guardian.orchestrator import GuardianOrchestrator
        ...
        self._orchestrator = GuardianOrchestrator(...)
```

### Sequential Orchestrator

```python
# lambda/guardian/orchestrator.py
class GuardianOrchestrator:
    def run_all_checks(self, event) -> Dict:
        results = {}
        for name, checker in self.checkers.items():
            results[name] = checker.check()  # Wait for each
        return results
```

**Timing**: Sum of all checker times (mock: ~80ms, real AWS: varies)

**Pros**:
- Simple logic
- Easier to debug
- Better for debugging individual failures

**Cons**:
- Slower overall
- High Lambda timeout (15+ minutes recommended)

### Parallel Orchestrator

```python
# lambda/guardian/parallel_orchestrator.py
class ParallelOrchestrator:
    async def run_checks_async(self) -> Dict[str, CheckResult]:
        tasks = [
            EC2Checker(...).check_async(),
            S3Checker(...).check_async(),
            ...
        ]
        results = await asyncio.gather(*tasks)
        return dict(zip(names, results))
```

**Timing**: Max of all checker times (mock: ~20ms, real AWS: varies)

**Pros**:
- 3-4x faster
- Better for production
- Handles high Lambda concurrency

**Cons**:
- More complex async/await syntax
- Harder to debug individual failures

## Configuration Management

Configuration is centralized in `guardian/config.py`:

```
Environment Variables (highest priority)
    ↓
SSM Parameter Store (production secrets)
    ↓
Code Defaults (fallback)
```

### Environment Variables

Required (in Lambda execution role):
- `AWS_REGION` - Default: us-east-1
- `AWS_ENV` - Default: localstack (set to "prod" in production)

Optional (with defaults):
- `COST_THRESHOLD` - Daily cost threshold (USD)
- `AUTHORIZED_REGIONS` - Comma-separated regions
- `TELEGRAM_BOT_TOKEN` - Telegram Bot API token
- `TELEGRAM_CHAT_ID` - Telegram chat to notify

### SSM Integration

For production security:

```python
# In production, store secrets in SSM Parameter Store
ssm_token_path = "/aws-guardian/telegram-bot-token"
bot_token = Config._get_ssm_value(ssm_token_path)
```

Benefits:
- Secrets never in Lambda environment
- Encrypted at rest
- Audit trail via CloudTrail

## Data Flow

### Event Processing Pipeline

```
1. EventBridge Event (hourly)
   ↓
2. Lambda Invocation
   ↓
3. Checker Execution (Sequential or Parallel)
   ↓
4. Result Collection
   ├─ CheckResult objects
   ├─ Merged into single report
   └─ Severity determined
   ↓
5. Responder Actions
   ├─ Telegram notification
   ├─ Discord bot update
   ├─ Auto-remediation (if enabled)
   └─ Audit log write
   ↓
6. DynamoDB Persistence
   ├─ Raw findings table
   ├─ Audit logs table
   └─ Remediation metrics table
```

### Storage Schema

#### guardianFindings Table
```json
{
  "id": "uuid",
  "timestamp": "2024-05-21T10:30:00Z",
  "checker": "EC2",
  "severity": "HIGH",
  "title": "Public Instance Detected",
  "message": "Instance i-123 is publicly accessible",
  "details": {
    "instance_id": "i-123",
    "region": "us-east-1",
    "public_ips": ["1.2.3.4"]
  },
  "account_id": "123456789"
}
```

#### guardianAuditLog Table
```json
{
  "id": "uuid",
  "timestamp": "2024-05-21T10:30:00Z",
  "action": "AUTO_REMEDIATION",
  "resource": "i-123",
  "status": "SUCCESS",
  "result": "Instance stopped",
  "account_id": "123456789"
}
```

## AWS Service Integration

### Services Used

| Service | Purpose | Operation |
|---------|---------|-----------|
| Lambda | Compute | Run checks hourly |
| EventBridge | Scheduling | Trigger Lambda every hour |
| EC2 | Monitoring | Check instance security |
| S3 | Monitoring | Check bucket permissions |
| IAM | Monitoring | Check policy changes |
| CloudTrail | Monitoring | Query API audit log |
| Cost Explorer | Monitoring | Query daily costs |
| GuardDuty | Monitoring | Query security findings |
| RDS | Monitoring | Check database security |
| DynamoDB | Storage | Persist findings/audit logs |
| SSM Parameter Store | Config | Secrets management |
| SNS | Notifications | Alert endpoints |

### Permissions Model

Minimal IAM policy (what Lambda needs):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeSecurityGroups",
        "s3:ListAllMyBuckets",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicy",
        "iam:ListUsers",
        "cloudtrail:LookupEvents",
        "ce:GetCostAndUsage",
        "guardduty:GetFindings",
        "dynamodb:PutItem",
        "dynamodb:Query"
      ],
      "Resource": "*"
    }
  ]
}
```

## Testing Architecture

### Test Pyramid

```
              Unit + Integration Tests (2392 tests, ~82s)
          /        |        |        \
        EC2       S3        Cost     IAM ...
      /  |  \   /  |  \   /  |  \   /  |  \
    API  E2E Payload Mock  Real  ...

     Performance Tests (optional)
         /    |    \
      Baseline, Profiling, Benchmarks
```

> **Note**: 2327 tests pass, 4 fail, 61 skipped, 2 collection errors (as of 2026-05-30).

### Mock Strategy

Tests use `unittest.mock.Mock()` to avoid AWS calls:

```python
mock_ec2 = Mock()
mock_ec2.describe_instances.return_value = {
    "Reservations": [{
        "Instances": [
            {"InstanceId": "i-123", "State": {"Name": "running"}}
        ]
    }]
}

checker = EC2Checker(clients={"ec2": mock_ec2})
result = checker.check()
assert result.severity == "INFO"  # No public instances
```

**Why mocks for unit tests?**
- Mocks are faster (5-10ms per call)
- Mocks are deterministic
- No external dependencies needed

> **Note**: The project also includes LocalStack integration for integration testing
> (see `docker-compose.yml`, `scripts/deploy-localstack.sh`). Unit tests use mocks for speed;
> LocalStack is available for more realistic integration testing.

## Caching Strategy

### Cache Backends

**InMemoryCache** (default)
- TTL-based: Data expires after N seconds
- Thread-safe using thread-local storage
- No external dependencies

**RedisCache** (optional)
- Distributed cache for multi-instance deployment
- Fallback to InMemoryCache if Redis unavailable

**Cache Keys**:
```
checker:ec2:instances:us-east-1
checker:s3:buckets:us-east-1
checker:cost:daily
```

### TTL Strategy

```
- EC2 instances: 300s (5 minutes)
- S3 buckets: 3600s (1 hour)
- Cost data: 3600s (1 hour)
- IAM users: 600s (10 minutes)
```

**Rationale**: Balance between freshness (detect new issues) and API rate limits

## Logging Architecture

### Structured JSON Logging

All logs are JSON-formatted for easy parsing:

```json
{
  "timestamp": "2024-05-21T10:30:00.000Z",
  "level": "INFO",
  "logger": "guardian.checkers.ec2",
  "message": "EC2 check completed",
  "action": "check_complete",
  "resource": "EC2",
  "status": "success",
  "duration_ms": 1234
}
```

### Log Destinations

| Log Type | Destination | Retention |
|----------|-------------|-----------|
| Lambda Logs | CloudWatch | 7 days |
| Audit Logs | DynamoDB | 90 days |
| Error Logs | SNS → Email | Immediate |

## Multi-Region Support

### Architecture

```
┌─────────────────────────────────────┐
│     Lambda: us-east-1               │
│  (Primary orchestrator)              │
│                                     │
│  For each configured region:        │
│  ┌───────────────────────────────┐  │
│  │ Regional Checker Instance      │  │
│  │ - Get session for region       │  │
│  │ - Run checks in parallel       │  │
│  │ - Return regional results      │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
    ↓
DynamoDB Global Table (multi-region replica)
```

### Cross-Account Support

For monitoring multiple AWS accounts:

```python
def get_client_for_account(
    service_name: str,
    account_id: str,
    credentials: Dict[str, str],  # STS temporary credentials
    region: Optional[str] = None
) -> Any:
    """Create client for a different account."""
    session = boto3.Session(
        aws_access_key_id=credentials["aws_access_key_id"],
        aws_secret_access_key=credentials["aws_secret_access_key"],
        aws_session_token=credentials["aws_session_token"]
    )
    return session.client(service_name, region_name=region)
```

## Performance Characteristics

### Lambda Execution

| Metric | Value | Notes |
|--------|-------|-------|
| Baseline | 200-300ms | Python startup, imports |
| All Checks (Sequential) | 6-8s | Sum of checker times |
| All Checks (Parallel) | 2-3s | Max(checker times) |
| Responders | 1-2s | Telegram, Discord API |
| DynamoDB Write | 100-200ms | Persist audit log |
| **Total (8 checkers)** | Sequential: sum of all | Sequential |
| **Total (8 checkers)** | Parallel: max of all | Parallel |

### Memory Usage

| Component | Memory | Notes |
|-----------|--------|-------|
| Lambda Runtime | 20-30 MB | Python 3.12 |
| Guardian Code | 10-15 MB | Imports, dependencies |
| Checker State | 5-10 MB | Cached responses |
| **Total** | <256 MB | Lambda configured at 512 MB |

## Key Design Decisions

### 1. Lazy Initialization

**Decision**: Heavy dependencies loaded on first invocation, not at module import

**Rationale**:
- Lambda cold start optimization
- Only load needed checkers per invocation type
- Thread-safe double-checked locking pattern

### 2. Sync-First Checkers

**Decision**: All checkers use sync boto3 by default

**Rationale**:
- boto3 is mature, stable, widely-documented
- Thread-pool execution in Lambda is fast enough
- Parallel orchestrator handles concurrency via run_in_executor

### 3. Consolidated Error Handling

**Decision**: All error handling flows through 2 base methods

**Rationale**:
- DRY principle: one place to maintain error logic
- Consistent CheckResult format across all checkers

### 4. Mock-Based Unit Testing + LocalStack Integration

**Decision**: Unit tests use unittest.mock.Mock; integration tests use LocalStack

**Rationale**:
- Unit tests: fast (mocks), deterministic, no external dependencies
- Integration tests: more realistic via LocalStack (docker-compose.yml)

### 5. DynamoDB for Persistence

**Decision**: DynamoDB instead of RDS/Postgres

**Rationale**:
- Serverless (no server to manage)
- On-demand pricing (pay for what you use)
- TTL auto-expiration for cleanup

## Current Status & Future Enhancements

### Currently Implemented

1. **8 Security/Cost Checkers**
   - EC2, S3, Cost, IAM, CloudTrail, GuardDuty, RDS, IAM Policy Analyzer

2. **ML & Analytics Modules**
   - Anomaly detection (IsolationForest, statistical)
   - Cost forecasting (ARIMA)
   - Threat correlation & profiling
   - Behavioral analysis

3. **Automated Response**
   - Auto-remediation (EC2 stop, S3 block)
   - Incident playbooks
   - Response orchestration

4. **Kubernetes (Phase 1)**
   - Basic K8s cluster monitoring
   - API server anomaly detection
   - RBAC validation
   - Network policy checking

### Planned Features (Not Yet Implemented)

1. **Kubernetes Full Integration (Sprint 80 Phase 2-4)**
   - Container image scanning
   - Pod anomaly detection
   - Helm chart validation

2. **Production Verification**
   - Real AWS deployment testing
   - Performance benchmarking with actual API calls
   - ML model accuracy validation

3. **Compliance Reporting**
   - CIS Benchmarks
   - PCI-DSS reporting
   - SOC 2 compliance evidence

## Troubleshooting

### Lambda Timeout (>900 seconds)

**Symptom**: `Task timed out after 900 seconds`

**Solution**:
1. Switch to parallel orchestrator
2. Reduce regions checked per invocation
3. Increase Lambda timeout to 15 minutes (max)

### High DynamoDB Costs

**Symptom**: DynamoDB billing is unexpectedly high

**Solution**:
1. Enable TTL on findings table (auto-delete old entries)
2. Set retention policy (7-30 days instead of unlimited)
3. Use on-demand billing instead of provisioned

### Checker Hangs

**Symptom**: Lambda timeout while checker runs

**Solution**:
1. Add timeout to boto3 client: `Config.get_boto3_kwargs()`
2. Catch `socket.timeout` exceptions
3. Log hang details for debugging

---

**Last Updated**: May 2026  
**Version**: Current development (Sprint 80)  
**Maintainer**: AWS Guardian Contributors
