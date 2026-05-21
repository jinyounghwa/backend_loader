# Contributing to AWS Guardian

Thank you for your interest in contributing to AWS Guardian! This guide explains how to add new checkers, tests, and documentation.

---

## Adding a New Checker

### Overview

AWS Guardian uses a **modular checker system** where each checker inherits from `BaseChecker` and analyzes one AWS service or concern. This guide walks through adding a new checker using two real examples: `RDSChecker` and `IAMPolicyAnalyzer`.

### Step 1: Understand the Checker Pattern

All checkers follow this template:

```python
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

class NewChecker(BaseChecker):
    """Brief description of what this checker does."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients or {}, config or {}, account_id, credentials)
        # Initialize service client
        self.service_client = self.clients.get("service")
        if self.service_client is None:
            import boto3
            self.service_client = boto3.client("service", **Config.get_boto3_kwargs())

    def check(self) -> CheckResult:
        """Main entry point — must be implemented by subclass."""
        self._log_check_start("NewChecker")
        try:
            findings = self._analyze_resources()
            return self._build_result(findings)
        except ClientError as e:
            return self._handle_client_error("NewChecker", e)
        except Exception as e:
            return self._handle_generic_error("NewChecker", e)

    def _analyze_resources(self) -> List[Dict[str, Any]]:
        """Fetch and analyze resources."""
        # Your implementation here
        pass

    def _build_result(self, findings: List[Dict[str, Any]]) -> CheckResult:
        """Convert findings into CheckResult."""
        if not findings:
            return CheckResult(
                severity="INFO",
                title="No Issues Found",
                message="All resources are compliant",
                details={"is_anomaly": False, "findings": []},
            )
        
        # Determine severity from findings
        severity = self._determine_severity(findings)
        return CheckResult(
            severity=severity,
            title="Issues Detected",
            message=f"Found {len(findings)} issue(s)",
            details={"is_anomaly": True, "findings": findings},
            suggested_action="Review and remediate issues",
        )
```

### Step 2: Real Example - RDSChecker

Here's how `RDSChecker` was implemented:

**File**: `lambda/guardian/checkers/rds.py`

```python
class RDSChecker(BaseChecker):
    """Detect RDS security anomalies: public accessibility, encryption, backups."""

    def __init__(self, ...):
        super().__init__(...)
        self.rds_client = self.clients.get("rds")
        if self.rds_client is None:
            import boto3
            self.rds_client = boto3.client("rds", **Config.get_boto3_kwargs())

    def check(self) -> CheckResult:
        self._log_check_start("RDS")
        try:
            instances = self._get_rds_instances()
            return self._analyze_instances(instances)
        except ClientError as e:
            return self._handle_client_error("RDS", e)
        except Exception as e:
            return self._handle_generic_error("RDS", e)

    def _get_rds_instances(self) -> List[Dict[str, Any]]:
        """Fetch all RDS instances using paginator."""
        instances = []
        try:
            paginator = self.rds_client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                instances.extend(page.get("DBInstances", []))
        except ClientError as e:
            logger.error("ClientError fetching RDS instances: %s", e)
        except Exception as e:
            logger.error("Error fetching RDS instances: %s", e)
        return instances

    def _analyze_instances(self, instances: List[Dict[str, Any]]) -> CheckResult:
        """Analyze RDS instances for security issues."""
        anomalies: List[str] = []
        details: Dict[str, Any] = {
            "is_anomaly": False,
            "publicly_accessible": [],
            "unencrypted": [],
            "backup_disabled": [],
            "iam_auth_disabled": [],
            "cloudwatch_logs_disabled": [],
            "instance_count": len(instances),
        }

        for instance in instances:
            db_id = instance.get("DBInstanceIdentifier", "unknown")

            # Check 1: Public accessibility
            if instance.get("PubliclyAccessible", False):
                anomalies.append(f"RDS instance {db_id} is publicly accessible")
                details["publicly_accessible"].append(db_id)
                details["is_anomaly"] = True

            # Check 2: Storage encryption
            if not instance.get("StorageEncrypted", False):
                anomalies.append(f"RDS instance {db_id} has encryption disabled")
                details["unencrypted"].append(db_id)
                details["is_anomaly"] = True

            # Check 3-5: Additional checks...

        # Determine severity based on findings
        if len(details["publicly_accessible"]) > 0:
            severity = "HIGH"
        elif len(details["unencrypted"]) > 0:
            severity = "MEDIUM"
        else:
            severity = "LOW" if anomalies else "INFO"

        # Return appropriate result
        if not anomalies:
            return CheckResult(severity="INFO", ...)
        
        message = f"Found {len(anomalies)} security issues in {len(instances)} RDS instances"
        return CheckResult(
            severity=severity,
            title="RDS Security Issues Detected",
            message=message,
            details=details,
            suggested_action="Review and remediate RDS security configurations",
        )
```

### Step 3: Real Example - IAMPolicyAnalyzer

Here's how `IAMPolicyAnalyzer` was implemented:

**File**: `lambda/guardian/checkers/iam_policy_analyzer.py`

```python
class IAMPolicyAnalyzer(BaseChecker):
    """Analyze IAM policies for overly-permissive actions."""

    RISKY_ACTIONS = {
        "*": "CRITICAL",
        "iam:*": "HIGH",
        "ec2:*": "HIGH",
        "s3:*": "HIGH",
        "dynamodb:*": "HIGH",
    }

    def __init__(self, ...):
        super().__init__(...)
        self.iam_client = self.clients.get("iam")
        if self.iam_client is None:
            import boto3
            self.iam_client = boto3.client("iam", **Config.get_boto3_kwargs())

    def check(self) -> CheckResult:
        self._log_check_start("IAMPolicyAnalyzer")
        try:
            policies = self._get_all_policies()
            return self._analyze_policies(policies)
        except ClientError as e:
            return self._handle_client_error("IAMPolicyAnalyzer", e)
        except Exception as e:
            return self._handle_generic_error("IAMPolicyAnalyzer", e)

    def _get_all_policies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all inline policies from users and roles."""
        policies = {"users": [], "roles": []}

        # Get user policies
        try:
            paginator = self.iam_client.get_paginator("list_users")
            for page in paginator.paginate():
                for user in page.get("Users", []):
                    user_policies = self._get_user_inline_policies(user["UserName"])
                    for policy_doc in user_policies:
                        policies["users"].append({
                            "entity": user["UserName"],
                            "type": "user",
                            "policy": policy_doc,
                        })
        except ClientError as e:
            logger.error("Error fetching users: %s", e)

        # Get role policies (similar pattern)
        # ...

        return policies

    def _analyze_policies(self, policies: Dict) -> CheckResult:
        """Analyze policies for risky patterns."""
        findings = []
        severity_map = set()

        for entity_type, entity_list in policies.items():
            for entity_policy in entity_list:
                entity = entity_policy["entity"]
                policy_doc = entity_policy["policy"]

                policy_findings = self._analyze_policy_document(policy_doc, entity, entity_type)
                findings.extend(policy_findings)
                for finding in policy_findings:
                    severity_map.add(finding["severity"])

        if not findings:
            return CheckResult(severity="INFO", ...)

        # Determine overall severity
        if "CRITICAL" in severity_map:
            overall_severity = "CRITICAL"
        elif "HIGH" in severity_map:
            overall_severity = "HIGH"
        else:
            overall_severity = "MEDIUM"

        return CheckResult(
            severity=overall_severity,
            title="Risky IAM Policies Detected",
            message=f"Found {len(findings)} risky policies",
            details={
                "is_anomaly": True,
                "total_policies_scanned": len(policies["users"]) + len(policies["roles"]),
                "risky_policies": len(findings),
                "findings": findings,
            },
            suggested_action="Review and restrict overly-permissive policies",
        )

    def _analyze_policy_document(self, policy_doc, entity, entity_type):
        """Analyze a single policy document for risky patterns."""
        findings = []
        statements = policy_doc.get("Statement", [])

        for statement in statements:
            effect = statement.get("Effect", "Allow")
            actions = self._normalize_actions(statement.get("Action", []))
            resources = self._normalize_resources(statement.get("Resource", []))

            # Check 1: Action: "*" with Resource: "*"
            if "*" in actions and "*" in resources and effect == "Allow":
                findings.append({
                    "entity": entity,
                    "severity": "CRITICAL",
                    "issue": 'Action: "*" with Resource: "*"',
                    "remediation": "Remove or restrict to specific actions and resources",
                })
                continue

            # Check 2: Wildcard actions
            for action in actions:
                if action in self.RISKY_ACTIONS:
                    findings.append({
                        "entity": entity,
                        "severity": self.RISKY_ACTIONS[action],
                        "issue": f'Action: "{action}"',
                        "remediation": f"Restrict to specific {action.split(':')[0]} actions",
                    })
                    break

        return findings
```

### Step 4: Register Checker in Orchestrator

Update `lambda/guardian/orchestrator.py`:

```python
# Step 1: Add import
from guardian.checkers.new_service import NewServiceChecker

# Step 2: Add parameter to __init__
def __init__(
    self,
    ...,
    new_service_checker: Optional[NewServiceChecker] = None,
):

# Step 3: Add to self.checkers dictionary
self.checkers: Dict[str, Optional[BaseChecker]] = {
    ...,
    "new_service": new_service_checker,
}

# Step 4: Update _get_checks_for_type()
def _get_checks_for_type(self, check_type: str) -> List[str]:
    if check_type == "cost":
        return ["cost"]
    elif check_type == "security":
        return [..., "new_service"]  # If security-related
    return [..., "new_service"]

# Step 5: Add account-specific creation (for multi-account support)
def _create_account_checkers(self, account_id: str, credentials: Dict[str, str]):
    account_checkers = dict(self.checkers)
    
    if self.checkers.get("new_service"):
        new_service_clients = {
            "service": AWSClientProvider.get_client_for_account(
                "service", account_id, credentials
            ),
        }
        account_checkers["new_service"] = NewServiceChecker(
            new_service_clients, {}, account_id=account_id, credentials=credentials
        )
    
    return account_checkers
```

### Step 5: Create Comprehensive Tests

Create `tests/lambda/test_new_service_harness.py`:

```python
import os
import unittest
from unittest.mock import Mock

os.environ["AWS_ENV"] = "localstack"

import sys
from pathlib import Path

lambda_dir = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))

from guardian.checkers.new_service import NewServiceChecker


class TestNewServiceChecker(unittest.TestCase):
    """Test NewService security checks."""

    def setUp(self):
        """Setup mock clients."""
        self.mock_service = Mock()
        self.mock_clients = {"service": self.mock_service}

        # Configure paginator
        paginator = Mock()
        paginator.paginate.return_value = [{"Resources": []}]
        self.mock_service.get_paginator.return_value = paginator

    def test_no_resources(self):
        """Return INFO when no resources exist."""
        checker = NewServiceChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertEqual(result.details["resource_count"], 0)

    def test_non_compliant_resource(self):
        """Detect non-compliant resource."""
        # Mock response with non-compliant resource
        non_compliant = {
            "ResourceId": "res-123",
            "CompliantProperty": False,
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"Resources": [non_compliant]}]
        self.mock_service.get_paginator.return_value = paginator

        checker = NewServiceChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")
        self.assertGreater(result.details["non_compliant"], 0)

    def test_compliant_resource(self):
        """Return INFO for compliant resources."""
        compliant = {
            "ResourceId": "res-456",
            "CompliantProperty": True,
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"Resources": [compliant]}]
        self.mock_service.get_paginator.return_value = paginator

        checker = NewServiceChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertEqual(result.details["non_compliant"], 0)


if __name__ == "__main__":
    unittest.main()
```

### Step 6: Update Performance Baseline Tests

Add individual and combined tests in `tests/lambda/test_performance_baseline.py`:

```python
# Add import
from guardian.checkers.new_service import NewServiceChecker

# Add to setUp() mock_clients
self.mock_clients["service"] = Mock()

# Add individual test
@patch("guardian.aws_client_provider.AWSClientProvider.get_client")
def test_new_service_checker_performance(self, mock_get_client):
    """NewService checker should complete in < 500ms."""
    mock_get_client.return_value = self.mock_clients["service"]
    checker = NewServiceChecker(clients=self.mock_clients)

    start = time.perf_counter()
    result = checker.check()
    elapsed = time.perf_counter() - start

    self.assertLess(elapsed, 0.5)
    self.assertIsNotNone(result.severity)

# Update test_all_checkers_combined()
# - Increase combined checker count
# - Adjust expected time based on added checkers
# - Add NewServiceChecker to checkers list
```

### Step 7: Document the Checker

Add to `docs/CHECKER_CATALOG.md`:

```markdown
## X. NewServiceChecker

**Location**: `lambda/guardian/checkers/new_service.py`

### Purpose
[What this checker does]

### Security Issues Detected
- Issue 1
- Issue 2

### Configuration
[Configuration options]

### Severity Levels
[Table of conditions and severity levels]

### Example Finding
[JSON example]

### Remediation Actions
[Numbered list of actions]

### Performance
- **Baseline**: ~10ms (mock environment)
- **Real AWS**: ~XXXms
- **API calls**: N
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/new-checker
```

### 2. Implement Checker

- Create `lambda/guardian/checkers/new_service.py`
- Implement `check()` method
- Add proper error handling
- Add logging via `self._log_check_start()`

### 3. Create Tests

- Create `tests/lambda/test_new_service_harness.py`
- Add 5-10 test cases covering main scenarios
- Use Mock clients (no real AWS calls)
- Test both positive and negative cases

### 4. Run Tests

```bash
python3 -m pytest tests/lambda/test_new_service_harness.py -v
python3 -m pytest tests/lambda/test_performance_baseline.py -v
```

### 5. Register in Orchestrator

- Update `lambda/guardian/orchestrator.py` imports, __init__, self.checkers, _get_checks_for_type(), _create_account_checkers()
- Update `lambda/guardian/parallel_orchestrator.py` if needed

### 6. Document

- Add entry to `docs/CHECKER_CATALOG.md`
- Update `docs/ARCHITECTURE.md` checker count
- Add examples and remediation guidance

### 7. Commit and Push

```bash
git add -A
git commit -m "feat: Add NewServiceChecker"
git push origin feature/new-checker
```

---

## Code Quality Standards

### CheckResult Requirements

All checkers must return a `CheckResult` with:
- **severity**: One of "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
- **title**: Clear, concise title (< 50 chars)
- **message**: Brief summary (< 100 chars)
- **details**: Machine-readable dict with at least:
  - `is_anomaly`: boolean indicating if issues found
  - `timestamp`: ISO 8601 timestamp
  - Custom fields specific to the checker

### Error Handling

All checkers must:
- Catch `ClientError` from boto3
- Catch generic `Exception` as fallback
- Return `CheckResult.error()` for failures
- Log errors with context via `self._log_error()`

### Testing

All checkers must have:
- ≥ 5 test cases covering main scenarios
- Mock clients (no real AWS calls)
- Test both INFO and non-INFO severity levels
- Assert on `severity`, `message`, and `details`

### Performance

All checkers should:
- Complete in < 500ms with mock clients
- Complete in < 1000ms with real AWS
- Use paginators for large result sets
- Implement early returns for optimization

---

## Examples in Codebase

For real, working examples, see:

1. **RDSChecker** (`lambda/guardian/checkers/rds.py`)
   - Simple security checks (✓ public, ✓ encrypted, ✓ backups)
   - Paginator usage
   - Severity determination

2. **IAMPolicyAnalyzer** (`lambda/guardian/checkers/iam_policy_analyzer.py`)
   - Complex policy analysis
   - Multi-level checking
   - Multiple findings per resource

3. **EC2Checker** (`lambda/guardian/checkers/ec2.py`)
   - Multiple check types
   - Security group analysis
   - Region-based filtering

---

## Questions?

Refer to:
- `docs/CHECKER_CATALOG.md` - Complete reference for all 8 checkers
- `docs/ARCHITECTURE.md` - System design and patterns
- `lambda/guardian/checkers/base.py` - BaseChecker interface
- Existing checkers in `lambda/guardian/checkers/` - Real working examples
