# Sprint 45 계획: CI/CD 파이프라인 & 코드 리펙토링

**상태:** 📋 계획 중  
**예상 기간:** 1주  
**기준 테스트:** 595 (Sprint 44 완료)  
**목표 테스트:** 650+ (55개 이상 추가)

---

## 목표 (Objectives)

Sprint 44에서 구축한 **Automated Incident Response Platform**을 프로덕션 레디 상태로 만들기 위해:

1. **CI/CD 자동화** - GitHub Actions로 완전한 자동화 파이프라인 구축
2. **코드 리펙토링** - 중복 제거, 에러 처리 개선, 성능 최적화
3. **통합 테스트** - 마이크로서비스 간 상호작용 검증
4. **배포 자동화** - AWS Lambda에 자동 배포

---

## Phase 별 구현 계획

### Phase 1: CI/CD 파이프라인 구축 (15 tests)

**목표:** GitHub Actions를 통한 완전한 자동화 파이프라인 구축

#### 1.1 Unit Test CI 파이프라인

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `.github/workflows/unit-tests.yml` | pytest 자동 실행 | - |
| `.github/workflows/coverage.yml` | 코드 커버리지 검사 | - |
| `tests/backend/test_ci_pipeline.py` | CI 파이프라인 동작 검증 | 5 |

**구현 내용:**

```yaml
# .github/workflows/unit-tests.yml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - run: pip install -r requirements.txt
      - run: python3 -m pytest tests/backend/ -v --cov=lambda/guardian
      - uses: codecov/codecov-action@v3
```

**테스트 시나리오:**
- ✅ test_ci_pipeline_runs_all_unit_tests
- ✅ test_ci_pipeline_fails_on_test_failure
- ✅ test_ci_pipeline_checks_coverage_threshold (80%+)
- ✅ test_ci_pipeline_generates_coverage_report
- ✅ test_ci_pipeline_uploads_to_codecov

#### 1.2 코드 품질 검사 (Linting & Type Checking)

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `.github/workflows/lint.yml` | Linting 자동 실행 | - |
| `tests/backend/test_code_quality.py` | 코드 품질 검증 | 5 |

**구현 내용:**

```yaml
# .github/workflows/lint.yml
name: Code Quality

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install pylint flake8 black mypy
      - run: pylint lambda/guardian --fail-under=8.0
      - run: flake8 lambda/guardian --max-line-length=100
      - run: black --check lambda/guardian
      - run: mypy lambda/guardian --ignore-missing-imports
```

**테스트 시나리오:**
- ✅ test_code_quality_pylint_score
- ✅ test_code_quality_flake8_compliance
- ✅ test_code_quality_black_formatting
- ✅ test_code_quality_mypy_types
- ✅ test_code_quality_no_warnings

#### 1.3 보안 스캔

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `.github/workflows/security.yml` | 보안 취약점 스캔 | - |
| `tests/backend/test_security_scan.py` | 보안 검증 | 5 |

**구현 내용:**

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install bandit safety
      - run: bandit -r lambda/guardian -f json -o bandit-report.json
      - run: safety check --json > safety-report.json
      - uses: github/codeql-action/init@v2
      - uses: github/codeql-action/autobuild@v2
      - uses: github/codeql-action/analyze@v2
```

**테스트 시나리오:**
- ✅ test_security_no_sql_injection_vulnerabilities
- ✅ test_security_no_hardcoded_credentials
- ✅ test_security_dependencies_up_to_date
- ✅ test_security_no_known_vulnerabilities
- ✅ test_security_code_ql_analysis_passes

---

### Phase 2: 코드 리펙토링 & 최적화 (20 tests)

**목표:** 코드 품질 향상, 중복 제거, 성능 최적화

#### 2.1 중복 코드 제거 (Refactoring)

| 파일 | 변경 사항 | 테스트 수 |
|------|---------|---------|
| `lambda/guardian/services/base_ticket_service.py` | 신규: BaseTicketService 추상 클래스 | 3 |
| `lambda/guardian/services/jira_service.py` | 수정: BaseTicketService 상속 | - |
| `lambda/guardian/services/servicenow_service.py` | 수정: BaseTicketService 상속 | - |
| `tests/backend/test_refactoring.py` | 신규: 리펙토링 검증 테스트 | 8 |

**리펙토링 항목:**

```python
# 공통 추상 클래스 생성
class BaseTicketService(ABC):
    """Jira/ServiceNow 공통 인터페이스"""
    
    @abstractmethod
    def create_ticket(self, threat: Dict) -> Dict:
        pass
    
    @abstractmethod
    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        pass
    
    @abstractmethod
    def add_comment(self, ticket_id: str, comment: str) -> bool:
        pass
    
    # 공통 로직 (Jira/ServiceNow 모두 사용)
    def _convert_severity(self, severity: int) -> str:
        """AWS 심각도를 티켓 우선순위로 변환"""
        # 공통 구현
        pass
    
    def _format_evidence(self, evidence: Dict) -> str:
        """CloudTrail 증거 포맷팅"""
        # 공통 구현
        pass
```

**테스트 시나리오:**
- ✅ test_base_ticket_service_abstract
- ✅ test_jira_inherits_base_service
- ✅ test_servicenow_inherits_base_service
- ✅ test_shared_severity_conversion
- ✅ test_shared_evidence_formatting
- ✅ test_code_duplication_reduced
- ✅ test_api_consistency_between_implementations
- ✅ test_error_handling_unified

#### 2.2 에러 처리 개선

| 파일 | 변경 사항 | 테스트 수 |
|------|---------|---------|
| `lambda/guardian/exceptions/__init__.py` | 신규: Custom exception 클래스 | - |
| `lambda/guardian/handlers/*.py` | 수정: try-except 통일화 | - |
| `tests/backend/test_error_handling.py` | 신규: 에러 처리 검증 | 6 |

**Custom Exception 클래스:**

```python
# lambda/guardian/exceptions/__init__.py

class GuardianException(Exception):
    """모든 Guardian 예외의 기본 클래스"""
    pass

class TicketingException(GuardianException):
    """티켓팅 관련 예외"""
    pass

class WorkflowExecutionException(GuardianException):
    """워크플로우 실행 예외"""
    pass

class SOARIntegrationException(GuardianException):
    """SOAR 통합 예외"""
    pass

class ValidationException(GuardianException):
    """검증 실패 예외"""
    pass

class RetryableException(GuardianException):
    """재시도 가능한 예외 (네트워크 오류 등)"""
    pass
```

**테스트 시나리오:**
- ✅ test_custom_exceptions_properly_raised
- ✅ test_retry_logic_for_retryable_exceptions
- ✅ test_error_logging_captures_full_context
- ✅ test_error_recovery_strategies
- ✅ test_graceful_degradation_on_service_failure
- ✅ test_error_metrics_tracking

#### 2.3 성능 최적화

| 파일 | 변경 사항 | 테스트 수 |
|------|---------|---------|
| `lambda/guardian/cache/incident_cache.py` | 신규: 인시던트 캐싱 | 3 |
| `lambda/guardian/orchestrators/incident_orchestrator.py` | 수정: 캐싱 적용 | - |
| `tests/backend/test_performance.py` | 신규: 성능 검증 | 3 |

**최적화 내용:**

```python
# lambda/guardian/cache/incident_cache.py

class IncidentCache:
    """조회 성능 향상을 위한 인시던트 캐시"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, incident_id: str) -> Optional[Dict]:
        """캐시에서 인시던트 조회"""
        if incident_id in self.cache:
            entry = self.cache[incident_id]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
            else:
                del self.cache[incident_id]
        return None
    
    def set(self, incident_id: str, incident: Dict):
        """캐시에 인시던트 저장"""
        self.cache[incident_id] = {
            'data': incident,
            'timestamp': time.time()
        }
```

**테스트 시나리오:**
- ✅ test_caching_reduces_lookup_time_by_90_percent
- ✅ test_cache_ttl_expiration
- ✅ test_parallel_orchestration_performance
- ✅ test_workflow_execution_time_optimization
- ✅ test_soar_submission_batch_optimization

---

### Phase 3: 통합 테스트 & 엔드투엔드 테스트 (12 tests)

**목표:** 마이크로서비스 간 상호작용 검증

#### 3.1 통합 테스트

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `tests/integration/test_ticketing_workflow_integration.py` | 신규: Ticketing ↔ Workflow | 3 |
| `tests/integration/test_workflow_soar_integration.py` | 신규: Workflow ↔ SOAR | 3 |
| `tests/integration/test_orchestration_integration.py` | 신규: 완전한 통합 | 3 |

**테스트 시나리오:**

```python
# tests/integration/test_orchestration_integration.py

class TestFullIncidentOrchestrationFlow:
    """완전한 인시던트 대응 흐름 검증"""
    
    def test_threat_detection_to_ticket_creation_to_workflow_execution_to_soar_submission(self):
        """
        1. 위협 탐지
        2. 티켓 생성 (Jira/ServiceNow)
        3. 워크플로우 실행
        4. SOAR 제출
        5. 결과 추적
        
        모든 단계가 순서대로 실행되고 데이터가 전달되는지 확인
        """
        pass
    
    def test_cross_service_error_propagation(self):
        """한 서비스의 에러가 다른 서비스로 전파되지 않도록 격리"""
        pass
    
    def test_component_timeout_doesnt_block_others(self):
        """한 컴포넌트 timeout이 다른 컴포넌트 실행을 막지 않도록"""
        pass
```

#### 3.2 엔드투엔드 테스트

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `tests/e2e/test_incident_response_e2e.py` | 신규: 완전한 E2E 시나리오 | 3 |

**테스트 시나리오:**
- ✅ test_e2e_critical_threat_detection_and_response
- ✅ test_e2e_multiple_concurrent_incidents
- ✅ test_e2e_incident_with_network_failures

---

### Phase 4: 배포 자동화 & 모니터링 (8 tests)

**목표:** AWS Lambda 자동 배포 및 프로덕션 모니터링

#### 4.1 배포 자동화

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `.github/workflows/deploy.yml` | 신규: AWS Lambda 자동 배포 | - |
| `sam/template.yaml` | 수정: CI/CD 배포 구성 | - |
| `tests/backend/test_deployment.py` | 신규: 배포 검증 | 4 |

**구현 내용:**

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install aws-sam-cli
      
      - name: Build SAM application
        run: sam build
      
      - name: Deploy to AWS
        run: |
          sam deploy \
            --template-file .aws-sam/build/template.yaml \
            --stack-name aws-guardian-stack \
            --s3-bucket ${{ secrets.AWS_DEPLOYMENT_BUCKET }} \
            --region us-east-1 \
            --capabilities CAPABILITY_IAM \
            --no-confirm-changeset
      
      - name: Run smoke tests
        run: python3 tests/smoke/test_deployment.py
```

**테스트 시나리오:**
- ✅ test_deployment_artifacts_generated_correctly
- ✅ test_cloudformation_template_valid
- ✅ test_lambda_function_deployed_successfully
- ✅ test_environment_variables_set_correctly

#### 4.2 모니터링 & 알람

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `lambda/guardian/monitoring/metrics.py` | 신규: CloudWatch 메트릭 | - |
| `tests/backend/test_monitoring.py` | 신규: 모니터링 검증 | 4 |

**구현 내용:**

```python
# lambda/guardian/monitoring/metrics.py

class GuardianMetrics:
    """CloudWatch 메트릭 수집"""
    
    def __init__(self, namespace: str = 'AWSGuardian'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
    
    def record_incident_orchestration(self, incident_id: str, duration_ms: float):
        """인시던트 오케스트레이션 메트릭"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'IncidentOrchestrationDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds'
            }]
        )
    
    def record_workflow_execution(self, workflow_id: str, success: bool):
        """워크플로우 실행 결과"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'WorkflowExecutionResult',
                'Value': 1 if success else 0,
                'Dimensions': [{'Name': 'WorkflowId', 'Value': workflow_id}]
            }]
        )
    
    def record_error(self, error_type: str, service: str):
        """에러 발생"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'ErrorCount',
                'Value': 1,
                'Dimensions': [
                    {'Name': 'ErrorType', 'Value': error_type},
                    {'Name': 'Service', 'Value': service}
                ]
            }]
        )
```

**테스트 시나리오:**
- ✅ test_metrics_collected_on_incident_orchestration
- ✅ test_errors_tracked_by_type_and_service
- ✅ test_performance_metrics_within_sla
- ✅ test_alarms_triggered_on_error_threshold

---

## 구현 일정

| Phase | 항목 | 예상 일수 | 테스트 수 |
|-------|------|---------|---------|
| 1 | CI/CD 파이프라인 | 2일 | 15 |
| 2 | 코드 리펙토링 | 2일 | 20 |
| 3 | 통합 & E2E 테스트 | 1일 | 12 |
| 4 | 배포 & 모니터링 | 1일 | 8 |
| **합계** | **모든 Phase** | **6일** | **55** |

---

## 성공 기준

| 기준 | 목표 | 검증 방법 |
|------|------|---------|
| 테스트 커버리지 | 80%+ | codecov.io |
| 코드 품질 점수 | 8.0+ (pylint) | GitHub Actions |
| 배포 시간 | 5분 이내 | GitHub Actions 로그 |
| 엔드투엔드 테스트 | 100% 통과 | pytest E2E suite |
| 보안 취약점 | 0개 | bandit + safety |
| 성능 개선 | 30% 향상 | 성능 테스트 |

---

## 상세 파일 변경 목록

### 신규 파일

```
.github/workflows/
├── unit-tests.yml          (CI: pytest 자동 실행)
├── lint.yml                (CI: 코드 품질 검사)
├── security.yml            (CI: 보안 스캔)
└── deploy.yml              (CD: AWS 자동 배포)

lambda/guardian/
├── exceptions/
│   └── __init__.py         (Custom exception 클래스)
├── services/
│   └── base_ticket_service.py  (공통 인터페이스)
├── cache/
│   └── incident_cache.py   (성능 최적화 캐싱)
└── monitoring/
    └── metrics.py          (CloudWatch 메트릭)

tests/backend/
├── test_ci_pipeline.py     (5 tests)
├── test_code_quality.py    (5 tests)
├── test_security_scan.py   (5 tests)
├── test_refactoring.py     (8 tests)
├── test_error_handling.py  (6 tests)
├── test_performance.py     (3 tests)
├── test_deployment.py      (4 tests)
└── test_monitoring.py      (4 tests)

tests/integration/
├── test_ticketing_workflow_integration.py   (3 tests)
├── test_workflow_soar_integration.py        (3 tests)
└── test_orchestration_integration.py        (3 tests)

tests/e2e/
└── test_incident_response_e2e.py           (3 tests)

tests/smoke/
└── test_deployment.py
```

### 수정 파일

```
lambda/guardian/services/
├── jira_service.py         (BaseTicketService 상속)
└── servicenow_service.py   (BaseTicketService 상속)

lambda/guardian/handlers/
├── ticketing_handler.py    (에러 처리 통일화)
└── *.py                    (Custom exception 적용)

lambda/guardian/orchestrators/
└── incident_orchestrator.py (캐싱 적용)

sam/template.yaml           (CI/CD 배포 구성)

requirements.txt            (새로운 의존성 추가)
```

---

## 기대 효과

### 개발 생산성
- ✅ 자동화된 품질 검증 → PR 리뷰 시간 50% 감소
- ✅ 배포 자동화 → 배포 시간 5분 단축
- ✅ 코드 리펙토링 → 신기능 개발 속도 향상

### 코드 품질
- ✅ 일관된 코드 스타일 (black formatting)
- ✅ 타입 안정성 (mypy checking)
- ✅ 낮은 기술 부채 (중복 코드 제거)

### 운영 안정성
- ✅ 자동화된 보안 스캔 → 취약점 사전 탐지
- ✅ 모니터링 & 알람 → 빠른 문제 탐지
- ✅ 통합 테스트 → 서비스 간 호환성 보장

### 비즈니스 가치
- ✅ 더 빠른 버그 픽스 (CI 자동화)
- ✅ 더 높은 안정성 (E2E 테스트)
- ✅ 더 나은 운영 가시성 (모니터링)

---

## 다음 단계 (Sprint 46+)

### Sprint 46: Auto-Remediation Actions
- 위협 자동 대응 (EC2 자동 중지, S3 자동 차단)
- IAM 권한 자동 취소
- 네트워크 격리 자동화

### Sprint 47: Advanced Analytics
- 인시던트 상관관계 분석
- 위협 패턴 인식
- 이상 탐지 개선

### Sprint 48: Multi-Account Management
- 다중 AWS 계정 지원
- 중앙 집중식 대시보드
- 계정별 정책 설정

---

## 리소스 및 참고 자료

### 도구
- **CI/CD:** GitHub Actions
- **Testing:** pytest, unittest.mock, pytest-cov
- **Code Quality:** pylint, flake8, black, mypy
- **Security:** bandit, safety, CodeQL
- **Deployment:** AWS SAM, CloudFormation
- **Monitoring:** CloudWatch, CloudWatch Alarms

### 문서
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/)
- [pytest Documentation](https://docs.pytest.org/)
- [pylint Documentation](https://pylint.pycqa.org/)

---

## 승인 및 시작

**계획 작성 날짜:** 2026-05-24  
**예상 시작 날짜:** 2026-05-25  
**예상 완료 날짜:** 2026-05-31

**승인 서명:**
- [ ] 팀 리드 승인
- [ ] 아키텍처 리뷰
- [ ] 보안 리뷰

---

**Sprint 45는 Sprint 44의 Automated Incident Response Platform을 프로덕션 레디 상태로 만드는 중요한 마일스톤입니다.**
