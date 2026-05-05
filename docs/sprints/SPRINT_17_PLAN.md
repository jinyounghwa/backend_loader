# Sprint 17: Lambda Test Harness (v1.1)

**Status**: 🔄 IN PROGRESS  
**Duration**: May 5 - May 12, 2026 (estimated)  
**Goal**: Lambda 실행 환경의 테스트 하네스 구축으로 LocalStack과 실제 AWS Lambda 간의 동작 일관성 확보

---

## Context

Sprint 16 (v1.0) 완료로 AWS Guardian은 프로덕션 레디 상태에 도달했습니다. 그러나 다음 갭이 있습니다:

1. **Jest 테스트**: Mock 기반 (실제 Lambda 호출 안 함)
2. **Python 테스트**: Unit test 위주 (전체 Lambda 핸들러 검증 안 함)
3. **LocalStack ↔ AWS**: 환경 동작 일관성 미검증
4. **Cold Start**: 성능 기준치 없음
5. **IAM 권한**: 로컬 테스트에서는 권한 검증 안 함

**Sprint 17은 이 갭들을 메우는 테스트 하네스를 구축합니다.**

---

## Phase 1: Lambda Test Harness (SAM Local)

### Objective
AWS SAM CLI를 활용하여 로컬 Lambda 핸들러를 실제 환경처럼 호출할 수 있는 테스트 하네스를 구축합니다.

### Deliverables

#### 1.1 SAM Local Harness Base Class
**File**: `tests/lambda/harness.py`

```python
class LambdaHarness:
    """LocalStack SAM을 통한 실제 Lambda 호출 테스트"""
    
    def invoke_local(self, event: dict, context: dict = None) -> dict:
        """SAM local invoke"""
        # sam local invoke GuardianChecker --event <event-json>
        # Return parsed response
        
    def measure_cold_start(self) -> float:
        """Cold start 시간 측정"""
        
    def validate_iam_permissions(self) -> bool:
        """IAM role 권한 검증"""
```

#### 1.2 Checker Integration Tests
각 Checker를 실제 Lambda 환경에서 테스트합니다.

**Files**:
- `tests/lambda/test_cost_checker_harness.py` (5 test cases)
  - EventBridge event format 검증
  - Cost Explorer API mock 응답
  - Response 형식 검증
  - Error handling (missing API key, API error)
  
- `tests/lambda/test_ec2_checker_harness.py` (5 test cases)
  - EC2 instance 감지 event
  - Multi-region invocation
  - SecurityGroup vulnerability detection
  - Response 형식 검증
  
- `tests/lambda/test_s3_checker_harness.py` (5 test cases)
  - S3 bucket discovery event
  - Public ACL detection
  - Bucket policy analysis
  - Response 형식 검증
  
- `tests/lambda/test_orchestrator_harness.py` (3 test cases)
  - Full handler invocation (all checkers)
  - Responder chain execution
  - Error propagation
  
- `tests/lambda/test_handler_harness.py` (4 test cases)
  - EventBridge scheduled event
  - Handler entry point validation
  - DynamoDB persistence
  - Telegram/Discord notification trigger

**Total**: 22 test cases

#### 1.3 Test Infrastructure
**Files**:
- `tests/lambda/conftest.py` - pytest fixtures (SAM setup, DynamoDB container, mock AWS client)
- `tests/lambda/__init__.py` - package init
- `sam.yaml` - SAM template (if not exists)
- `tests/lambda/fixtures/events/` - EventBridge event examples

#### 1.4 Package Updates
**File**: `lambda/guardian/requirements.txt` and `lambda/requirements-dev.txt`

Add for testing:
- `pytest-aws-lambda` (SAM local integration)
- `moto>=5.0` (AWS mock for integration tests)
- `localstack` (docker container management)

### Auth Testing Strategy

**Pattern**: SAM local invoke uses actual DynamoDB container + mock AWS services

**401/403 Tests**: Mock IAM role validation in handler

**Success Path**: Actual boto3 calls against LocalStack

### Key Implementation Notes

1. **SAM Configuration**: `sam.yaml` should define GuardianChecker and supporting resources
2. **Event Payloads**: Use realistic EventBridge scheduled event format
3. **Mock Services**: Cost Explorer, CloudTrail, GuardDuty mocked via moto
4. **LocalStack Integration**: DynamoDB and SSM Parameter Store via container
5. **Performance Baseline**: Capture cold start time for each invocation

---

## Phase 2: Event Payload Validation

### Objective
EventBridge와 Lambda 간의 데이터 계약을 검증하는 하네스를 구축합니다.

### Deliverables

#### 2.1 Event Schema Definitions
**Files**:
- `tests/lambda/fixtures/events/eventbridge_scheduled.json` - Scheduled event
- `tests/lambda/fixtures/events/cost_event.json` - Cost check trigger
- `tests/lambda/fixtures/events/ec2_event.json` - EC2 check trigger
- `tests/lambda/fixtures/events/s3_event.json` - S3 check trigger

#### 2.2 Payload Validation Tests
**File**: `tests/lambda/test_payload_contracts.py` (8 test cases)

- EventBridge event schema validation
- Checker response payload validation
- Responder input format validation
- DynamoDB record schema validation
- API response schema alignment (Jest vs Lambda)

#### 2.3 Pydantic Models (Optional)
**File**: `lambda/guardian/models.py`

```python
class EventBridgeScheduledEvent(BaseModel):
    version: str
    id: str
    detail_type: str
    source: str
    account: str
    time: datetime
    region: str
    resources: List[str]
    detail: dict

class CheckerResponse(BaseModel):
    checker_name: str
    findings: List[dict]
    timestamp: datetime
    region: str
```

---

## Phase 3: Performance Baseline

### Objective
Lambda 성능 특성을 측정하고 기준치를 설정합니다.

### Deliverables

#### 3.1 Performance Test Suite
**File**: `tests/lambda/test_performance.py` (5 test cases)

- Cold start (first invocation): target < 2.5s
- Warm start (subsequent invocation): target < 500ms
- Multi-region (4 regions, sequential): target < 15s
- DynamoDB write performance: target < 100ms per record
- API response latency (p95): target < 500ms

#### 3.2 Performance Metrics Collection
**File**: `tests/lambda/metrics.py`

```python
@measure_performance
def test_cold_start():
    """Capture: invocation_time, memory_used, duration_ms"""
    
def print_performance_baseline():
    """Generate docs/PERFORMANCE_BASELINE_v1.1.md"""
```

#### 3.3 Performance Documentation
**File**: `docs/PERFORMANCE_BASELINE_v1.1.md`

| Metric | Target | Current (v1.0) | Notes |
|--------|--------|-----------------|-------|
| Lambda Cold Start | < 2.5s | ~2.3s | ✅ |
| Warm Invocation | < 500ms | ~100ms | ✅ |
| Multi-Region (4x) | < 15s | ~8-12s | ✅ |
| DynamoDB Write | < 100ms | ~50ms | ✅ |
| API Response (p95) | < 500ms | ~300-500ms | ✅ |

---

## Technical Decisions

### Decision 1: SAM Local vs Docker Lambda

**Chose**: SAM Local (for local testing) + Actual Lambda (for E2E)

**Rationale**:
- SAM local invoke matches real Lambda environment more closely than mocks
- Docker lambda would add complexity
- LocalStack containers already provide AWS service mocks
- CI/CD can use SAM local for pre-deploy validation

### Decision 2: Unit vs Integration Tests

**Chose**: Integration tests (SAM local) complementing existing unit tests

**Rationale**:
- Unit tests (existing) validate business logic
- Integration tests (new) validate Lambda infrastructure
- Both together ensure end-to-end correctness

### Decision 3: Test File Organization

**Chose**: Separate `tests/lambda/` directory with harness pattern

**Rationale**:
- Clear separation from unit tests
- Reusable LambdaHarness base class
- Easy to add more test types later (E2E, load testing, etc.)

---

## Verification Steps

### Phase 1 Verification
```bash
cd lambda
python -m pytest tests/lambda/test_*_harness.py -v
# Expected: 22 tests pass
# Expected cold start time printed
```

### Phase 2 Verification
```bash
python -m pytest tests/lambda/test_payload_contracts.py -v
# Expected: 8 tests pass
# Expected schema validation errors caught
```

### Phase 3 Verification
```bash
python -m pytest tests/lambda/test_performance.py -v
# Expected: 5 tests pass
# Expected: docs/PERFORMANCE_BASELINE_v1.1.md generated
```

---

## Known Issues & Mitigations

### Issue 1: SAM CLI Version Mismatch
**Problem**: SAM CLI versions may differ between local and CI
**Mitigation**: Pin SAM version in requirements-dev.txt
**Status**: ⚠️ Monitor

### Issue 2: LocalStack Container Startup Time
**Problem**: First test run may be slow (container initialization)
**Mitigation**: Use pytest-timeout with skip for slow container startup
**Status**: ⚠️ Known limitation

### Issue 3: IAM Role Assumption
**Problem**: LocalStack doesn't fully validate IAM assumptions
**Mitigation**: Test IAM in actual AWS separately (E2E suite)
**Status**: ⚠️ Scoped out

---

## File Checklist

### Phase 1 Files
- ✅ `tests/lambda/harness.py`
- ✅ `tests/lambda/conftest.py`
- ✅ `tests/lambda/__init__.py`
- ✅ `tests/lambda/test_cost_checker_harness.py`
- ✅ `tests/lambda/test_ec2_checker_harness.py`
- ✅ `tests/lambda/test_s3_checker_harness.py`
- ✅ `tests/lambda/test_orchestrator_harness.py`
- ✅ `tests/lambda/test_handler_harness.py`
- ✅ `tests/lambda/fixtures/events/*.json`
- ✅ `lambda/requirements-dev.txt` (updated)

### Phase 2 Files
- ✅ `tests/lambda/fixtures/events/` (all event JSONs)
- ✅ `tests/lambda/test_payload_contracts.py`
- ✅ `lambda/guardian/models.py` (optional)

### Phase 3 Files
- ✅ `tests/lambda/test_performance.py`
- ✅ `tests/lambda/metrics.py`
- ✅ `docs/PERFORMANCE_BASELINE_v1.1.md`

---

## Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| Lambda harness tests passing | 22/22 | ⏳ |
| Payload contract tests passing | 8/8 | ⏳ |
| Performance tests passing | 5/5 | ⏳ |
| Cold start baseline documented | < 2.5s | ⏳ |
| Python tests still passing | 116+/116+ | ⏳ |
| No build errors | 0 errors | ⏳ |

---

## v1.1 Commit Strategy

**Important**: 이 Sprint 부터는 main에 커밋하지만, v1.1이 충분히 갖춰질 때까지 푸시하지 않습니다.

```bash
# Phase 1 완료
git add tests/lambda/
git commit -m "🧪 Sprint 17 Phase 1: Lambda Test Harness with SAM Local"

# Phase 2 완료  
git add tests/lambda/fixtures/ lambda/guardian/models.py
git commit -m "📋 Sprint 17 Phase 2: Event Payload Contract Validation"

# Phase 3 완료
git add tests/lambda/metrics.py tests/lambda/test_performance.py docs/PERFORMANCE_BASELINE_v1.1.md
git commit -m "📊 Sprint 17 Phase 3: Performance Baseline & Metrics"

# v1.1 준비 완료 후 → git push
```

---

## References

- **Sprint 16 Completion**: `docs/sprints/SPRINT_16_COMPLETION_SUMMARY.md`
- **AWS SAM Docs**: https://docs.aws.amazon.com/serverless-application-model/
- **LocalStack Docs**: https://docs.localstack.cloud/
- **Moto (AWS Mock)**: https://docs.getmoto.org/

---

**Sprint 17 Status**: 🔄 IN PROGRESS  
**Total Test Cases to Add**: 35 (Phase 1: 22, Phase 2: 8, Phase 3: 5)  
**Version Target**: v1.1 (commits only, push after Phase 3)
