# Sprint 22 Plan - Code Quality Refactoring & Test Infrastructure

**Project**: AWS Guardian - Lambda Backend  
**Planned Date**: Next Session After May 16, 2026  
**Duration**: Single Session (3-4 hours recommended)  
**Status**: 📋 PLANNED

---

## Context

Sprint 21 (May 16, 2026) successfully stabilized test infrastructure and implemented async/sync patterns across all checkers. Current status:
- ✅ 36/78 core tests passing (stable baseline)
- ✅ All 6 checkers have proper async/sync implementation
- ❌ 42 tests blocked (missing SAM template infrastructure)
- 📊 Code quality baseline established with identified refactoring opportunities

**Sprint 22 Focus**: Code quality improvements + SAM infrastructure to unblock remaining tests

---

## Objectives

### Primary (MUST DO)
- [ ] Fix pytest asyncio_mode warning
- [ ] Add return type hints to all BaseChecker logging methods
- [ ] Create comprehensive docstrings for public checker methods
- [ ] Create minimal SAM template (sam.yaml)
- [ ] Verify 36+ core tests still passing

### Secondary (SHOULD DO)
- [ ] Consolidate duplicate error handling patterns
- [ ] Replace catch-all Exception with specific ClientError handling
- [ ] Add type hints to all public methods

### Tertiary (NICE TO HAVE)
- [ ] Create CONTRIBUTING.md with test instructions
- [ ] Document performance baseline expectations
- [ ] Add code coverage configuration

---

## Phase 1: Code Quality Refactoring (2-3 hours)

### 1.1 Fix pytest Configuration Warning

**Task**: Remove "Unknown config option: asyncio_mode" warning

**File**: `pytest.ini`

**Change Required**:
```ini
[pytest]
# ... existing config ...
asyncio_mode = auto
```

**Verification**:
```bash
source venv/bin/activate
python3 -m pytest tests/lambda -v
# Check: No "PytestConfigWarning: Unknown config option: asyncio_mode"
```

**Effort**: 5 minutes

---

### 1.2 Add Return Type Hints to BaseChecker

**File**: `lambda/guardian/checkers/base.py`

**Methods to Update**:
```python
def _log_check_start(self, service_name: str) -> None:
    """Log start of checker execution"""
    logger.info(f"{service_name} check started")

def _log_error(self, service_name: str, error: Exception) -> None:
    """Log checker error with context"""
    logger.error(f"{service_name} check failed: {error}")

def _log_check_end(self, service_name: str, severity: str) -> None:
    """Log end of checker execution with result severity"""
    logger.info(f"{service_name} check completed: {severity}")
```

**Current State**: Missing `-> None` return types

**Expected Result**: All 3 methods have proper return type hints

**Effort**: 10 minutes

---

### 1.3 Add Comprehensive Docstrings

**Target Files**:
1. `lambda/guardian/checkers/ec2.py`
2. `lambda/guardian/checkers/s3.py`
3. `lambda/guardian/checkers/cloudtrail.py`
4. `lambda/guardian/checkers/iam.py`
5. `lambda/guardian/checkers/guardduty.py`
6. `lambda/guardian/checkers/cost.py`

**Docstring Template**:
```python
async def check_async(self) -> CheckResult:
    """Check for [specific anomalies/findings].
    
    This method:
    1. Fetches resources from AWS using async I/O (aioboto3)
    2. Analyzes resources for security/cost anomalies
    3. Returns structured CheckResult with findings
    
    For tests with mocked sync methods, this automatically falls back
    to calling sync versions via mock detection pattern.
    
    Returns:
        CheckResult: Contains severity, title, message, and detailed findings
            - severity: "CRITICAL", "HIGH", "MEDIUM", "LOW", or "INFO"
            - details: Dict with anomalies and contextual data
            
    Raises:
        Caught internally: ClientError, Exception are caught and returned as errors
    """
```

**Per-Checker Specific Docstrings**:

**EC2Checker.check_async()**:
```
Check for EC2 security anomalies across all regions.

Detects:
- Unauthorized region instances
- Security groups with 0.0.0.0/0 exposure
- New instances launched in last hour

Uses region-by-region async checking with semaphore (max 10 concurrent).
```

**S3Checker.check_async()**:
```
Check for S3 bucket security issues.

Detects:
- Public buckets (ACL, policy, or disabled public access block)
- New buckets created in last 24 hours

Uses parallel async checks for all buckets.
```

**CloudTrailChecker.check_async()**:
```
Check for suspicious CloudTrail events.

Detects:
- Failed authentication attempts
- Root account usage
- Unusual API activity patterns

Uses async event pagination with caching.
```

**IAMChecker.check_async()**:
```
Check for IAM security anomalies.

Detects:
- New IAM users created
- Access key usage patterns
- Permission changes

Compares against baseline to identify new activity.
```

**GuardDutyChecker.check_async()**:
```
Check for GuardDuty findings.

Detects:
- Active security findings from AWS GuardDuty
- Threat intelligence matches
- Anomalous API calls

Aggregates findings across all detectors.
```

**CostChecker.check_async()**:
```
Check for cost anomalies.

Detects:
- Daily cost exceeding threshold
- Cost trending upward
- Unusual service usage spikes

Compares current vs previous day and monthly trends.
```

**Effort**: 45 minutes (9-10 lines per method × 6 checkers)

---

### 1.4 Consolidate Duplicate Error Handling

**Problem**: Error handling pattern repeated in 3+ checkers

**Current Pattern** (EC2Checker, S3Checker, CloudTrailChecker):
```python
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "Unknown")
    self._log_error("SERVICE", e)
    return CheckResult.error(
        "SERVICE Check Failed",
        f'AWS error ({error_code}): {e.response.get("Error", {}).get("Message", str(e))}',
    )
except Exception as e:
    self._log_error("SERVICE", e)
    return CheckResult.error("SERVICE Check Failed", f"Failed to check SERVICE: {str(e)}")
```

**Solution** - Add to BaseChecker:
```python
def _handle_client_error(self, service_name: str, error: ClientError) -> CheckResult:
    """Handle AWS ClientError with logging and CheckResult."""
    error_code = error.response.get("Error", {}).get("Code", "Unknown")
    error_message = error.response.get("Error", {}).get("Message", str(error))
    self._log_error(service_name, error)
    return CheckResult.error(
        f"{service_name} Check Failed",
        f"AWS error ({error_code}): {error_message}",
    )

def _handle_generic_error(self, service_name: str, error: Exception) -> CheckResult:
    """Handle generic Exception with logging and CheckResult."""
    self._log_error(service_name, error)
    return CheckResult.error(
        f"{service_name} Check Failed",
        f"Failed to check {service_name}: {str(error)}",
    )
```

**Usage in Each Checker**:
```python
async def check_async(self) -> CheckResult:
    self._log_check_start("EC2")
    try:
        # ... check logic ...
    except ClientError as e:
        return self._handle_client_error("EC2", e)
    except Exception as e:
        return self._handle_generic_error("EC2", e)
```

**Files to Update**:
1. `lambda/guardian/checkers/base.py` (add 2 methods)
2. `lambda/guardian/checkers/ec2.py` (use 2 methods)
3. `lambda/guardian/checkers/s3.py` (use 2 methods)
4. `lambda/guardian/checkers/cloudtrail.py` (use 2 methods)
5. Other checkers as needed

**Benefits**:
- DRY principle
- Consistent error handling
- Easier to update error format globally
- Better logging

**Effort**: 1 hour (implement + update all checkers)

---

## Phase 2: SAM Template Creation (30 minutes)

### 2.1 Create Minimal sam.yaml

**File Location**: `/Users/younghwa.jin/Documents/backend_loader/sam.yaml`

**Content**:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2010-05-13
Description: 'AWS Guardian - Serverless Security Monitoring'

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues:
      - dev
      - test
      - prod

Globals:
  Function:
    Timeout: 300
    MemorySize: 512
    Runtime: python3.12
    Environment:
      Variables:
        AWS_ENV: localstack

Resources:
  GuardianCheckerFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: GuardianChecker
      CodeUri: lambda/
      Handler: guardian/handler.lambda_handler
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - ec2:*
                - s3:*
                - cloudtrail:*
                - iam:*
                - guardduty:*
                - ce:*
              Resource: '*'
            - Effect: Allow
              Action:
                - dynamodb:*
              Resource: '*'
      Environment:
        Variables:
          PYTHONPATH: /var/task/lambda

  GuardianEventBridgeRule:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: 'rate(1 hour)'
      State: ENABLED
      Targets:
        - Arn: !GetAtt GuardianCheckerFunction.Arn
          RoleArn: !GetAtt EventBridgeRole.Arn

  EventBridgeRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: events.amazonaws.com
            Action: 'sts:AssumeRole'
      Policies:
        - PolicyName: InvokeLambda
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: 'lambda:InvokeFunction'
                Resource: !GetAtt GuardianCheckerFunction.Arn

Outputs:
  GuardianCheckerFunctionArn:
    Value: !GetAtt GuardianCheckerFunction.Arn
    Description: ARN of Guardian Checker Lambda Function

  GuardianCheckerFunctionName:
    Value: !Ref GuardianCheckerFunction
    Description: Name of Guardian Checker Lambda Function
```

**Effort**: 20 minutes

### 2.2 Verify SAM Works

**Commands**:
```bash
# Install SAM CLI (if not installed)
brew install aws-sam-cli

# Validate template
sam validate --template sam.yaml

# Try local invocation (optional - for verification)
sam local start-api

# Run with test event
sam local invoke GuardianCheckerFunction \
  --event tests/lambda/fixtures/eventbridge_event.json
```

**Effort**: 10 minutes

---

## Phase 3: Test Validation (30 minutes)

### 3.1 Run Core Tests

```bash
source venv/bin/activate

# Should see: 36 passed (from Phase 1 refactoring should not break tests)
python3 -m pytest tests/lambda -k "not harness and not performance" -v
```

**Expected**:
- 36 tests passing
- 0 new failures from refactoring

**Effort**: 5 minutes

### 3.2 Run Harness Tests

```bash
# Should see: 33+ passed (now that SAM template exists)
python3 -m pytest tests/lambda -k "harness" -v
```

**Expected**:
- 30+ tests passing (SAM infrastructure unblocked)
- May have LocalStack-related failures (OK for now)

**Effort**: 10 minutes

### 3.3 Full Test Suite

```bash
# Should see: 60+ passed total
python3 -m pytest tests/lambda -v --tb=short
```

**Expected**:
- 60+ tests passing
- Some E2E/performance tests may still require LocalStack setup
- Clear understanding of remaining blockers

**Effort**: 10 minutes

---

## Phase 4: Documentation (Optional, Low Priority)

### 4.1 Create CONTRIBUTING.md (Optional)

**File**: `CONTRIBUTING.md`

**Sections**:
1. Test Environment Setup (venv activation)
2. Running Tests (with SAM)
3. Code Style Guidelines
4. Async/Sync Pattern Explanation
5. Mock Detection Pattern
6. Adding New Checkers

**Effort**: 30 minutes

### 4.2 Update Architecture Docs (Optional)

**File**: `docs/ARCHITECTURE.md`

**Sections to Add**:
- Async/Sync Dual Implementation
- Mock Detection Pattern
- Cache TTL Strategy
- Region-by-Region Checking
- Performance Expectations

**Effort**: 30 minutes

---

## Success Criteria

### Must Have (for Sprint 22 completion)
- ✓ 36+ core tests still passing
- ✓ pytest asyncio_mode warning resolved
- ✓ All BaseChecker methods have return type hints
- ✓ All public checker methods have docstrings
- ✓ SAM template created (sam.yaml)
- ✓ sam validate passes

### Should Have
- ✓ 40+ tests passing (after SAM unblocks harness tests)
- ✓ Duplicate error handling consolidated
- ✓ Exception handling uses ClientError

### Nice to Have
- ✓ CONTRIBUTING.md created
- ✓ Code coverage report generated
- ✓ Performance baseline documented

---

## Risk Assessment

### Low Risk
- Adding docstrings (documentation only, no logic change)
- Adding return type hints (type hints only, no runtime change)
- Creating SAM template (new infrastructure, doesn't affect existing code)

### Medium Risk
- Consolidating error handling (refactoring, could introduce bugs)
- Pytest config change (could affect test execution)

### Mitigation
- Run core tests after each change
- Review refactored code for logic changes
- Test SAM template before full test run

---

## Time Estimate

| Task | Estimate |
|------|----------|
| Phase 1.1: pytest config | 5 min |
| Phase 1.2: Return type hints | 10 min |
| Phase 1.3: Docstrings | 45 min |
| Phase 1.4: Error consolidation | 60 min |
| Phase 2.1: SAM template | 20 min |
| Phase 2.2: SAM validation | 10 min |
| Phase 3: Test validation | 30 min |
| **Phase 4 (optional)**: Documentation | 60 min |
| **TOTAL (Required)** | **~180 minutes (3 hours)** |
| **TOTAL (With Optional)** | **~240 minutes (4 hours)** |

---

## Recommended Execution Order

1. **Start with Phase 1.1** (pytest config) - Simplest, quick win
2. **Then Phase 1.2** (return type hints) - Low risk, isolated
3. **Then Phase 1.3** (docstrings) - Time-consuming but mechanical
4. **Then Phase 1.4** (error consolidation) - Most complex, test after
5. **Then Phase 2** (SAM template) - Create infrastructure
6. **Then Phase 3** (test validation) - Verify everything works
7. **Optional Phase 4** (documentation) - If time permits

---

## What NOT to Do in Sprint 22

❌ Don't refactor checker algorithms (too risky)  
❌ Don't add new checkers (out of scope)  
❌ Don't optimize performance (without baseline)  
❌ Don't work on mobile app (explicitly excluded)  
❌ Don't modify web dashboard (PC version is mature)  
❌ Don't change async/sync patterns (core pattern works)  

---

## Rollback Plan

If refactoring breaks tests:

```bash
# Reset to previous commit
git reset --hard HEAD~1

# Check which change broke it
git log --oneline -5

# Fix specific issue
# (adjust the problematic change)
```

Keep commits atomic so rollback is easy.

---

## User Constraints to Maintain

✅ **PC Version Only** - Focus on backend/Lambda, not mobile  
✅ **Backend Priority** - Checkers over web dashboard  
✅ **Async/Sync Patterns** - Keep dual implementation for tests  
✅ **Pydantic V2** - Maintain V2 syntax  
✅ **Mock Detection** - Keep pattern for test compatibility  

---

## Related Documentation

- **Previous Session**: `SPRINT_21_SESSION_MAY16_COMPLETION.md`
- **Handoff Document**: `../../SPRINT_22_HANDOFF.md`
- **Architecture**: `../ARCHITECTURE.md` (if exists)
- **Contributing**: Will be created in Phase 4 (optional)

---

## Questions for Sprint 22 Planning

1. Should SAM template be minimal (current) or full (all infrastructure)?
2. Should performance tests have strict thresholds or just informational?
3. Should CONTRIBUTING.md be priority or lower?
4. Should code coverage be added to CI/CD?
5. Should LocalStack be Docker Compose or GitHub Actions?

---

**Prepared**: May 16, 2026  
**Status**: Ready for Implementation  
**Expected Duration**: 3-4 hours (with optional documentation)  
**Estimated Outcome**: 60+ tests passing, improved code quality
