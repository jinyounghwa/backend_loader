# Contributing to AWS Guardian

Welcome to AWS Guardian development! This guide covers setup, testing, and development patterns.

## Getting Started

### Prerequisites
- Python 3.12+
- git
- Virtual environment (venv)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/jinyounghwa/backend_loader.git
cd backend_loader
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Environment variables (optional for local testing):
```bash
export AWS_ENV=localstack
export AWS_REGION=us-east-1
export PYTHONPATH=/path/to/lambda
```

## Running Tests

### Core Tests (42 tests, ~2 seconds)
```bash
python3 -m pytest tests/lambda -k "not harness and not performance" -v
# Expected: 42 passed, 3 skipped
```

### All Tests (with performance harness)
```bash
python3 -m pytest tests/ -v
# Expected: 75+ tests
```

### Watch Mode
```bash
pip install pytest-watch
ptw -- -k "not harness"
```

### Coverage
```bash
python3 -m pytest tests/lambda -v --cov=lambda/guardian --cov-report=html
# View: htmlcov/index.html
```

## Code Style

### Type Checking (mypy)
```bash
mypy lambda/guardian
```

Configuration: `mypy.ini`

### Code Formatting (black)
```bash
black lambda/
```

### Import Sorting (isort)
```bash
isort lambda/
```

### Linting (pylint)
```bash
pylint lambda/guardian
```

## Project Structure

```
lambda/
├── guardian/
│   ├── checkers/           # Security checkers (EC2, S3, IAM, etc)
│   │   ├── base.py         # BaseChecker abstract class
│   │   ├── ec2.py
│   │   ├── s3.py
│   │   ├── iam.py
│   │   ├── cloudtrail.py
│   │   ├── cost.py
│   │   └── guardduty.py
│   ├── responders/         # Alert and remediation logic
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   └── auto_remediation.py
│   ├── storage/            # DynamoDB persistence
│   │   ├── dynamodb.py
│   │   ├── response_rules.py
│   │   └── event_exporter.py
│   ├── handler.py          # Lambda entry point
│   ├── orchestrator.py     # Sequential execution
│   ├── parallel_orchestrator.py  # Async execution
│   ├── config.py           # Configuration management
│   ├── logging_config.py   # JSON logging
│   └── cache/              # Caching backends
├── requirements.txt        # Production dependencies
└── requirements-dev.txt    # Development dependencies

tests/
├── lambda/
│   ├── test_api_contracts.py       # API endpoint tests
│   ├── test_payload_contracts.py   # Event/response schema tests
│   ├── test_e2e_integration.py     # End-to-end workflows
│   ├── test_async_checkers.py      # Async execution tests
│   ├── test_cache.py               # Cache backend tests
│   └── test_multi_account.py       # Multi-account tests
└── test_orchestrator.py            # Orchestration tests
```

## Adding a New Checker

### Step 1: Create Checker Class

```python
# lambda/guardian/checkers/new_service.py
from guardian.checkers.base import BaseChecker, CheckResult

class NewServiceChecker(BaseChecker):
    def __init__(self, clients=None, config=None, account_id=None, credentials=None):
        super().__init__(clients or {}, config or {}, account_id, credentials)
        self.service_client = clients.get("new_service") or self._create_client()
    
    def check(self) -> CheckResult:
        """Synchronous check implementation."""
        try:
            findings = self._analyze_resources()
            if findings:
                return CheckResult(
                    severity="HIGH",
                    title="Issues Detected",
                    message=f"Found {len(findings)} issues",
                    details={"findings": findings}
                )
            return CheckResult.info("NewService Check", "All resources secure")
        except Exception as e:
            return self._handle_generic_error("NewService", e)
    
    async def check_async(self) -> CheckResult:
        """Native async implementation (optional)."""
        # Use aioboto3 for truly async I/O
        findings = await self._analyze_resources_async()
        # Return same CheckResult format
```

### Step 2: Register in Orchestrator

```python
# lambda/guardian/orchestrator.py
from guardian.checkers.new_service import NewServiceChecker

checkers = [
    ...
    NewServiceChecker,
]
```

### Step 3: Write Tests

```python
# tests/lambda/test_new_service.py
import unittest
from unittest.mock import Mock
from lambda.guardian.checkers.new_service import NewServiceChecker

class TestNewServiceChecker(unittest.TestCase):
    def setUp(self):
        self.mock_client = Mock()
        self.checker = NewServiceChecker(
            clients={"new_service": self.mock_client},
            config={"threshold": 10}
        )
    
    def test_check_returns_info_when_secure(self):
        self.mock_client.describe_resources.return_value = {"Resources": []}
        result = self.checker.check()
        self.assertEqual(result.severity, "INFO")
    
    def test_check_detects_issues(self):
        self.mock_client.describe_resources.return_value = {
            "Resources": [{"Id": "bad-resource"}]
        }
        result = self.checker.check()
        self.assertEqual(result.severity, "HIGH")
```

## Mock Detection Pattern

All checkers support both sync testing (mock) and async production (real AWS):

```python
def _get_resources(self):
    """Returns real AWS data or mock data based on client type."""
    try:
        response = self.client.describe_resources()
        # If self.client is a Mock object, it will have _mock_name attribute
        if hasattr(self.client, '_mock_name'):
            return self._handle_mock_response(response)
        return response  # Real AWS response
    except Exception:
        return []
```

**Key**: Tests pass `unittest.mock.Mock()` objects which are auto-detected and routed to sync code paths without AWS credentials.

## Error Handling

All checkers use consolidated error handling:

```python
except ClientError as e:
    return self._handle_client_error("ServiceName", e)
except Exception as e:
    return self._handle_generic_error("ServiceName", e)
```

These helpers log the error and return a CheckResult with severity="HIGH" and suggested remediation.

## Async/Sync Dual Pattern

### Subclass chooses ONE pattern:

**Pattern 1: Sync-first (default)**
- Override `check()` with boto3
- `check_async()` auto-wraps via `run_in_executor`

**Pattern 2: Async-native**
- Override `check_async()` with aioboto3
- `check()` auto-wraps via `_run_sync()`

### Example (Pattern 1):
```python
def check(self) -> CheckResult:
    users = self.iam_client.list_users()  # boto3 sync
    return CheckResult(...)

# check_async() auto-generated; no override needed
```

### Example (Pattern 2):
```python
async def check_async(self) -> CheckResult:
    async with self.aioboto3_session.client("iam") as iam:
        users = await iam.list_users()  # aioboto3 async
    return CheckResult(...)

# check() auto-generated using _run_sync()
```

## Configuration Management

All configuration flows through `guardian.config.Config`:

```python
from guardian.config import Config

threshold = Config.get_cost_threshold()  # Float from env/SSM
regions = Config.get_authorized_regions()  # List[str]
boto_kwargs = Config.get_boto3_kwargs()    # Dict for boto3.client()
```

**Precedence**: Environment variables → SSM Parameter Store → Defaults

## Logging

Use structured JSON logging for all messages:

```python
import logging
from guardian.logging_config import JSONFormatter, setup_logger

logger = setup_logger(__name__)
logger.info("Checker completed", extra={
    "action": "check_complete",
    "resource": "EC2",
    "status": "success"
})
```

Output format:
```json
{
  "timestamp": "2024-05-21T10:30:00.000Z",
  "level": "INFO",
  "logger": "guardian.checkers.ec2",
  "message": "Checker completed",
  "action": "check_complete",
  "resource": "EC2",
  "status": "success"
}
```

## Common Testing Patterns

### Mock AWS Responses
```python
mock_client = Mock()
mock_client.list_resources.return_value = {
    "Resources": [{"Id": "r-123", "Status": "running"}]
}
checker = SomeChecker(clients={"service": mock_client})
result = checker.check()
```

### Mock DynamoDB
```python
from unittest.mock import Mock

mock_table = Mock()
mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
mock_dynamodb = Mock()
mock_dynamodb.Table.return_value = mock_table

checker = SomeChecker(
    clients={"dynamodb_resource": mock_dynamodb}
)
```

### Suppress AWS SDK Warnings
```python
import warnings
import botocore
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

## Debugging

### Enable debug logging:
```bash
export DEBUG=1
export LOG_LEVEL=DEBUG
python3 -m pytest tests/lambda -v -s --log-cli-level=DEBUG
```

### Run single test:
```bash
python3 -m pytest tests/lambda/test_ec2.py::TestEC2Checker::test_detects_public_instances -v
```

### Inspect checker state:
```python
checker = EC2Checker(config={"threshold": 50})
print(checker.config)
print(checker.clients)
print(dir(checker))  # List all methods
```

## Performance Baselines

Latency targets (single region, single checker):
- Cost Checker: < 500ms
- EC2 Checker: < 1000ms
- S3 Checker: < 2000ms
- CloudTrail Checker: < 3000ms
- IAM Checker: < 2000ms
- GuardDuty Checker: < 1000ms

**Note**: LocalStack (mock) typically 5-10x faster than real AWS

## CI/CD

### GitHub Actions
Tests run automatically on:
- Push to main
- Pull requests
- Daily at 3 AM UTC

See `.github/workflows/` for configuration.

## Release Checklist

Before releasing a new version:

- [ ] All 42+ core tests passing
- [ ] mypy clean (`mypy lambda/guardian`)
- [ ] Code formatted (`black lambda/`)
- [ ] Imports sorted (`isort lambda/`)
- [ ] Git status clean (`git status`)
- [ ] Changelog updated
- [ ] Version bumped (see `sam.yaml`)
- [ ] Commit with message: "chore: release v1.X.X"
- [ ] Tag: `git tag v1.X.X && git push origin v1.X.X`

## Getting Help

- **Questions**: Open an issue or ask in discussions
- **Bug Reports**: Include logs, reproduce steps, and environment
- **Feature Requests**: Describe use case and expected behavior
- **Documentation**: Suggest improvements via PR

## Code of Conduct

Please be respectful and constructive in all interactions. We follow the Contributor Covenant 2.1.

## License

This project is licensed under MIT. See LICENSE file for details.

---

**Happy coding!** 🚀
