# AWS Guardian Checker Catalog

Complete reference for all 8 security and cost checkers available in AWS Guardian.

---

## Overview

AWS Guardian implements a modular checker system where each checker focuses on a specific AWS service or concern. All checkers follow the unified `CheckResult` format and can be executed individually or as part of the full orchestration.

| Checker | Type | Purpose | Performance |
|---------|------|---------|-------------|
| CostChecker | Cost | Daily cost anomaly detection | ~10ms (mock) |
| EC2Checker | Security | Compute instance security analysis | ~10ms (mock) |
| S3Checker | Security | Object storage access control | ~10ms (mock) |
| CloudTrailChecker | Security | Audit logging configuration | ~10ms (mock) |
| IAMChecker | Security | Identity & access management | ~10ms (mock) |
| GuardDutyChecker | Security | Threat detection status | ~10ms (mock) |
| RDSChecker | Security | Database instance security | ~10ms (mock) |
| IAMPolicyAnalyzer | Security | Inline policy risk analysis | ~10ms (mock) |

---

## 1. CostChecker

**Location**: `lambda/guardian/checkers/cost.py`

### Purpose
Detects anomalous daily AWS spending patterns compared to a configurable threshold.

### Security Issues Detected
- **Daily cost spike** exceeds threshold (default: $10/day)
- Unusual spending pattern identified

### Configuration
```python
CostChecker(
    clients={"ce": boto3.client("ce")},
    config={"cost_threshold": 10.0},  # Default $10/day
)
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| Cost ≤ threshold | INFO |
| Cost > threshold | HIGH |

### Example Finding
```json
{
  "severity": "HIGH",
  "title": "Unexpected AWS Cost Spike",
  "message": "Found $25.34 in charges today (threshold: $10.00)",
  "details": {
    "is_anomaly": true,
    "daily_cost": 25.34,
    "threshold": 10.0,
    "recommendation": "Review recent resource changes"
  }
}
```

### Remediation Actions
1. Check EC2 instance launch history
2. Review new S3 bucket creation
3. Check RDS instance creation
4. Review data transfer charges
5. Stop/terminate unnecessary resources

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~200-300ms (Cost Explorer API latency)
- **API calls**: 1 (GetCostAndUsage)

---

## 2. EC2Checker

**Location**: `lambda/guardian/checkers/ec2.py`

### Purpose
Monitors EC2 instances for security misconfigurations and unusual resource states.

### Security Issues Detected
- **Instances in unexpected regions** (restricted to approved regions)
- **Publicly accessible security groups** (0.0.0.0/0 on ports 22, 3389, 443)
- **New instances** detected (change management)
- **Stopped instances** lingering without termination

### Configuration
```python
EC2Checker(
    clients={"ec2": boto3.client("ec2")},
    config={
        "restricted_regions": ["us-east-1", "us-west-2"],
        "approved_amis": [],
    }
)
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| No anomalies | INFO |
| Public security group (22/3389) | CRITICAL |
| Instance in restricted region | HIGH |
| New instance detected | MEDIUM |

### Example Finding
```json
{
  "severity": "CRITICAL",
  "title": "EC2 Security Group Exposure",
  "message": "Found 1 security group with public SSH access",
  "details": {
    "publicly_accessible": ["sg-12345678"],
    "new_instances": [],
    "restricted_region_instances": [],
    "instance_count": 5
  }
}
```

### Remediation Actions
1. Restrict security group ingress to specific IPs
2. Terminate instances in restricted regions
3. Implement resource tagging
4. Use Systems Manager Session Manager instead of SSH
5. Enable VPC Flow Logs for network monitoring

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~300-600ms
- **API calls**: 2 (DescribeInstances, DescribeSecurityGroups)

---

## 3. S3Checker

**Location**: `lambda/guardian/checkers/s3.py`

### Purpose
Identifies S3 buckets with overly permissive access controls.

### Security Issues Detected
- **Public buckets** (bucket policy or ACL allows public read/write)
- **Authenticated users** (anyone with AWS account)
- **New buckets** (change management)
- **Encryption disabled** buckets

### Configuration
```python
S3Checker(clients={"s3": boto3.client("s3")})
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| No anomalies | INFO |
| Public read bucket | HIGH |
| Public write bucket | CRITICAL |
| New bucket detected | MEDIUM |

### Example Finding
```json
{
  "severity": "CRITICAL",
  "title": "S3 Bucket Public Write Access",
  "message": "Found 1 publicly writable bucket",
  "details": {
    "publicly_readable": [],
    "publicly_writable": ["my-public-bucket"],
    "new_buckets": [],
    "bucket_count": 10
  }
}
```

### Remediation Actions
1. Enable Block Public Access (all 4 settings)
2. Replace bucket policy with IAM-based access
3. Implement object-level ACLs instead of bucket ACLs
4. Enable versioning and MFA delete
5. Enable bucket encryption by default
6. Enable CloudTrail logging

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~400-800ms
- **API calls**: 3-5 per bucket (ListBuckets, GetBucketAcl, GetPublicAccessBlock, GetBucketPolicy)

---

## 4. CloudTrailChecker

**Location**: `lambda/guardian/checkers/cloudtrail.py`

### Purpose
Validates CloudTrail is properly configured for audit logging.

### Security Issues Detected
- **CloudTrail not enabled** in primary region
- **Log file validation disabled** (allows tampering)
- **CloudTrail stopped** (no active logging)
- **Encryption key issues** (using default AWS key)

### Configuration
```python
CloudTrailChecker(
    clients={
        "cloudtrail": boto3.client("cloudtrail"),
        "s3": boto3.client("s3"),
    }
)
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| CloudTrail enabled + validated | INFO |
| CloudTrail not enabled | CRITICAL |
| Log validation disabled | HIGH |
| CloudTrail stopped | HIGH |

### Example Finding
```json
{
  "severity": "CRITICAL",
  "title": "CloudTrail Not Enabled",
  "message": "CloudTrail is not logging API calls in this region",
  "details": {
    "is_anomaly": true,
    "cloudtrail_enabled": false,
    "log_validation_enabled": false,
    "trails": []
  }
}
```

### Remediation Actions
1. Enable CloudTrail in primary region
2. Enable log file validation
3. Configure S3 bucket for logs with encryption
4. Enable MFA delete on log bucket
5. Set up CloudWatch alerts for critical API calls
6. Implement log archival to Glacier

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~200-400ms
- **API calls**: 2-3 (DescribeTrails, GetTrailStatus)

---

## 5. IAMChecker

**Location**: `lambda/guardian/checkers/iam.py`

### Purpose
Analyzes IAM identity configuration for security risks.

### Security Issues Detected
- **Access keys > 90 days old** (credential rotation)
- **Root account access keys** (should not exist)
- **Users without MFA** (weak authentication)
- **Unused users** (>30 days inactive)
- **Overly permissive policies** (AdministratorAccess)

### Configuration
```python
IAMChecker(
    clients={
        "iam": boto3.client("iam"),
        "dynamodb_resource": boto3.resource("dynamodb"),
    }
)
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| No anomalies | INFO |
| Root has access keys | CRITICAL |
| User without MFA | HIGH |
| Access key > 90 days | HIGH |
| Unused user | MEDIUM |

### Example Finding
```json
{
  "severity": "CRITICAL",
  "title": "Root Account Access Keys Detected",
  "message": "Found 1 access key for root account",
  "details": {
    "is_anomaly": true,
    "root_access_keys": 1,
    "users_without_mfa": 0,
    "old_access_keys": []
  }
}
```

### Remediation Actions
1. Delete root account access keys immediately
2. Enable MFA for all users
3. Rotate access keys quarterly
4. Implement password policy (min length 14, complexity)
5. Use temporary credentials via STS AssumeRole
6. Remove AdministratorAccess from users

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~500-1000ms
- **API calls**: 5+ (ListUsers, GetLoginProfile, ListAccessKeys, GetAccessKeyLastUsed)

---

## 6. GuardDutyChecker

**Location**: `lambda/guardian/checkers/guardduty.py`

### Purpose
Validates AWS GuardDuty threat detection service is active.

### Security Issues Detected
- **GuardDuty not enabled** (no threat detection)
- **GuardDuty suspended** (active threat detection disabled)
- **No detectors** in primary regions

### Configuration
```python
GuardDutyChecker(
    clients={"guardduty": boto3.client("guardduty")}
)
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| GuardDuty enabled | INFO |
| GuardDuty not enabled | HIGH |
| GuardDuty suspended | CRITICAL |

### Example Finding
```json
{
  "severity": "HIGH",
  "title": "GuardDuty Not Enabled",
  "message": "GuardDuty threat detection is not active",
  "details": {
    "is_anomaly": true,
    "detector_enabled": false,
    "detector_count": 0
  }
}
```

### Remediation Actions
1. Enable GuardDuty in primary region
2. Enable for all AWS regions
3. Configure SNS notifications for findings
4. Integrate with SIEM (Splunk, Datadog, etc.)
5. Review existing findings in 30 days
6. Automate response to high-severity findings

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~200-300ms
- **API calls**: 2-3 (ListDetectors, GetDetector)

---

## 7. RDSChecker

**Location**: `lambda/guardian/checkers/rds.py`

### Purpose
Audits RDS database instances for security and backup configuration.

### Security Issues Detected
- **Publicly accessible** RDS instances (should be private)
- **Storage encryption disabled** (unencrypted data at rest)
- **Backup retention < 7 days** (insufficient backup history)
- **IAM authentication disabled** (should use temp credentials)
- **CloudWatch logs disabled** (no audit trail)

### Configuration
```python
RDSChecker(clients={"rds": boto3.client("rds")})
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| No anomalies | INFO |
| Publicly accessible | HIGH |
| Encryption disabled | MEDIUM |
| Backup < 7 days | LOW |
| IAM auth disabled | MEDIUM |
| No CloudWatch logs | LOW |

### Example Finding
```json
{
  "severity": "HIGH",
  "title": "RDS Security Issues Detected",
  "message": "Found 1 security issue in 1 RDS instance",
  "details": {
    "is_anomaly": true,
    "publicly_accessible": ["prod-db-1"],
    "unencrypted": [],
    "backup_disabled": [],
    "iam_auth_disabled": [],
    "cloudwatch_logs_disabled": [],
    "instance_count": 1
  }
}
```

### Remediation Actions
1. Move RDS to VPC (remove public accessibility)
2. Use security group for database access
3. Enable storage encryption (apply immediately if possible)
4. Set backup retention to ≥30 days
5. Enable IAM database authentication
6. Enable error and general query logs in CloudWatch
7. Enable automated backups with point-in-time restore

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~300-500ms
- **API calls**: 1 (DescribeDBInstances)

---

## 8. IAMPolicyAnalyzer

**Location**: `lambda/guardian/checkers/iam_policy_analyzer.py`

### Purpose
Scans inline IAM policies for overly permissive or dangerous permissions.

### Security Issues Detected
- **Action: "*" with Resource: "*"** (full AWS access)
- **Wildcard actions** (iam:\*, ec2:\*, s3:\*, dynamodb:\*)
- **S3 GetObject with Resource: "*"** (public read access)
- **NotAction with Deny effect** (overly broad deny rules)

### Configuration
```python
IAMPolicyAnalyzer(clients={"iam": boto3.client("iam")})
```

### Severity Levels
| Condition | Severity |
|-----------|----------|
| No risky policies | INFO |
| Action:\* + Resource:\* | CRITICAL |
| Wildcard service actions | HIGH |
| S3 public read | HIGH |
| NotAction Deny | MEDIUM |

### Example Finding
```json
{
  "severity": "CRITICAL",
  "title": "Risky IAM Policies Detected",
  "message": "Found 1 risky policies",
  "details": {
    "is_anomaly": true,
    "total_policies_scanned": 5,
    "risky_policies": 1,
    "findings": [
      {
        "entity": "admin-user",
        "entity_type": "users",
        "severity": "CRITICAL",
        "issue": "Action: \"*\" with Resource: \"*\"",
        "remediation": "Remove or restrict to specific actions and resources"
      }
    ]
  }
}
```

### Remediation Actions
1. Remove overly permissive policies
2. Apply principle of least privilege
3. Use AWS managed policies as baseline
4. Scope resources to specific ARNs
5. Use condition keys to restrict by IP, source, etc.
6. Implement policy boundaries for delegation
7. Use access analyzer to identify unused permissions

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~400-800ms
- **API calls**: 4-6+ (ListUsers, ListUserPolicies, GetUserPolicy, ListRoles, ListRolePolicies, GetRolePolicy)

---

## Checker Integration

### Using Individual Checkers

```python
from guardian.checkers.rds import RDSChecker
from guardian.checkers.iam_policy_analyzer import IAMPolicyAnalyzer
import boto3

# Create clients
clients = {
    "rds": boto3.client("rds"),
    "iam": boto3.client("iam"),
}

# Create and run checker
rds_checker = RDSChecker(clients={"rds": clients["rds"]})
result = rds_checker.check()

print(f"Severity: {result.severity}")
print(f"Message: {result.message}")
print(f"Details: {result.details}")
```

### Using GuardianOrchestrator

```python
from guardian.orchestrator import GuardianOrchestrator

orchestrator = GuardianOrchestrator(
    logger=logger,
    cost_checker=cost_checker,
    ec2_checker=ec2_checker,
    s3_checker=s3_checker,
    storage=dynamodb_storage,
    cloudtrail_checker=cloudtrail_checker,
    iam_checker=iam_checker,
    guardduty_checker=guardduty_checker,
    rds_checker=rds_checker,
    iam_policy_analyzer=iam_policy_analyzer,
)

# Run all checks
result = orchestrator.run_all_checks({"check_type": "all"})

# Run only security checks
result = orchestrator.run_all_checks({"check_type": "security"})

# Run only cost check
result = orchestrator.run_all_checks({"check_type": "cost"})
```

### Using ParallelOrchestrator

```python
from guardian.parallel_orchestrator import ParallelOrchestrator
import asyncio

parallel = ParallelOrchestrator(orchestrator)
result = asyncio.run(parallel.run_all_checks_parallel({"check_type": "all"}))
```

---

## CheckResult Format

All checkers return a unified `CheckResult`:

```python
@dataclass
class CheckResult:
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    title: str
    message: str
    details: Dict[str, Any]
    suggested_action: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
```

---

## Performance Characteristics

### Mock Environment (Test)
- **Individual checker**: ~10ms
- **8 checkers combined**: ~80ms
- **Total with orchestration**: ~100ms

### Real AWS (Production)
- **Individual checker**: 200-1000ms depending on service
- **8 checkers combined**: ~1500-3500ms
- **Total with orchestration**: ~2000-4000ms
- **Network latency**: 100-300ms per API call

> **Note**: Real AWS figures are estimates based on typical API latencies.
> Actual measurements in a real AWS environment have not been conducted.

### Optimization Tips
1. **Parallel execution**: Use `ParallelOrchestrator` for ~3x speedup
2. **Selective checks**: Run only needed check types (cost vs security)
3. **Regional scope**: Reduce DescribeInstances across all regions
4. **Caching**: Results cached for 5 minutes by default
5. **Batch operations**: Use paginators efficiently

---

## Adding New Checkers

To add a new checker:

1. **Create checker class** (inherit from `BaseChecker`)
   ```python
   from guardian.checkers.base import BaseChecker, CheckResult
   
   class NewChecker(BaseChecker):
       def check(self) -> CheckResult:
           # Sync implementation
           pass
   ```

2. **Register in orchestrator**
   ```python
   from guardian.checkers.new import NewChecker
   
   # Add to __init__ parameters
   new_checker: Optional[NewChecker] = None,
   
   # Add to self.checkers dict
   self.checkers["new"] = new_checker
   
   # Add to _get_checks_for_type()
   elif check_type == "security":
       return [..., "new"]
   ```

3. **Add account-specific creation in _create_account_checkers()**
   ```python
   if self.checkers.get("new"):
       new_clients = {...}
       account_checkers["new"] = NewChecker(...)
   ```

4. **Add tests** in `tests/lambda/test_new_harness.py`

5. **Update documentation** (this file)

---

## Support & Troubleshooting

### Checker Not Running
- Verify client is properly instantiated
- Check AWS credentials and IAM permissions
- Review `orchestrator.py` registration

### High Latency
- Check AWS API throttling
- Consider using parallel execution
- Enable result caching

### Unexpected Findings
- Verify checker logic matches expected behavior
- Check example findings in this document
- Review test cases for validation

### Adding Custom Logic
- Extend checker class with custom methods
- Override `check()` to customize behavior
- Emit custom `CheckResult` with details
