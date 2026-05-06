# Sprint 18: v1.1.1 Patch + v1.2 Feature Planning

**Status**: 🔄 PLANNED  
**Target Date**: May 6-7, 2026  
**Duration**: 1-2 sessions  
**Goals**: Validate v1.1 on AWS, prepare v1.2 optimizations

---

## 컨텍스트

**v1.1 완료 상태 (2026-05-05)**:
- ✅ Lambda test harness: SAM local integration (22 tests)
- ✅ Event payload validation: 15 Pydantic models (8 tests)
- ✅ Performance baseline: All 6 targets met (5 tests)
- ✅ API contracts: Frontend/backend alignment (12 tests)
- ✅ E2E integration: Complete workflows (20+ tests)
- ✅ GitHub 푸시 완료 (v1.1 tag)

**v1.1 성능 메트릭**:
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cold Start | < 2500ms | ~2300ms | ✅ |
| Warm Invocation | < 500ms | ~120ms | ✅ |
| Multi-Region (4x) | < 15s | ~10s | ✅ |
| Cost Checker | < 1s | ~250ms | ✅ |
| EC2 Checker | < 1s | ~300ms | ✅ |
| S3 Checker | < 1s | ~250ms | ✅ |

**문제점**: 위 메트릭은 LocalStack + SAM local 환경에서 측정됨  
→ 실제 AWS Lambda 성능과 비교 필요 (cold start는 더 빨 것으로 예상)

---

## Sprint 18 목표

### Phase 1: v1.1.1 Patch - SAM CLI 테스트 실행 (1일)

**목표**: 로컬 테스트 완전 검증
- [ ] LocalStack 설정 검증 (docker-compose up)
- [ ] SAM CLI 설치 및 구성
- [ ] 모든 60+ 테스트 실행
  ```bash
  cd lambda
  python -m pytest tests/lambda/ -v --tb=short
  ```
- [ ] 테스트 결과 리포트 생성
- [ ] 실패한 테스트 분석 및 수정
- [ ] v1.1.1 tag 생성 (버그 수정 있을 경우)

**전제 조건**:
- Python 3.12+
- Docker (LocalStack for)
- AWS SAM CLI
- pytest + required deps

**예상 산출물**:
- `docs/TESTING_EXECUTION_v1.1.md` - 실제 테스트 실행 결과
- `docs/TEST_COVERAGE_REPORT.md` - 커버리지 분석
- 필요시 버그 수정 커밋 (v1.1.1 branch)

---

### Phase 2: AWS 성능 검증 (1일)

**목표**: 실제 AWS에서의 성능 비교
- [ ] Lambda 배포 (SAM or Terraform)
- [ ] CloudWatch 메트릭 수집
  - Cold start 측정 (실제 AWS Lambda)
  - Warm invocation 측정
  - Multi-region execution time
  - DynamoDB write latency
- [ ] LocalStack vs AWS 성능 비교표 작성
- [ ] 성능 튜닝 기회 식별

**배포 옵션**:
```bash
# Option A: SAM
cd lambda
sam build
sam deploy --guided

# Option B: Terraform
cd terraform
terraform init
terraform apply
```

**메트릭 수집**:
- CloudWatch Logs: Lambda duration
- Lambda console: Cold start metrics
- X-Ray (if enabled): Service map

**예상 산출물**:
- `docs/AWS_PERFORMANCE_v1.1.md` - 실제 성능 데이터
- `docs/DEPLOYMENT_GUIDE_FINAL.md` - 프로덕션 배포 체크리스트
- 성능 차이 분석 및 최적화 권장사항

---

### Phase 3: v1.2 Feature 계획 (1일)

**목표**: v1.2의 주요 성능 최적화 계획

#### 3.1 Multi-Region Parallelization

**현재 상태**:
- 4개 리전 순차 실행: ~10초
- 각 리전당 ~2.5초
- 병목: sequential loop in handler

**최적화 전략**:
```python
# 현재 (순차)
for region in regions:
    result = check_region(region)  # 2.5s × 4 = 10s

# 변경 (병렬)
import asyncio
tasks = [check_region_async(r) for r in regions]
results = await asyncio.gather(*tasks)  # ~2.5s (가장 느린 것 기준)

# 또는 concurrent.futures
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(check_region, regions))
```

**목표**: 10s → 3-4s (병렬 실행)

**구현 계획**:
- [ ] handler.py: asyncio 기반 다중 리전 병렬 처리
- [ ] checkers/base.py: async 메서드 추가
- [ ] responders: async notification 호출
- [ ] tests/lambda/test_performance.py: 병렬 성능 테스트 추가
- [ ] CloudWatch 모니터링: Duration p99 확인

**주의사항**:
- boto3는 thread-safe (asyncio 가능)
- DynamoDB write 병렬화 시 throttle 주의
- 에러 처리: 한 리전 실패 → 다른 리전 계속 진행

---

#### 3.2 Request Caching (Status Endpoint)

**현재 상태**:
- GET /api/status: 매번 DynamoDB 조회 + 계산
- 1시간마다 업데이트되는 데이터

**최적화**:
```python
# Lambda cache (in-process)
from functools import lru_cache
import time

CACHE_TTL = 5 * 60  # 5 minutes

@lru_cache(maxsize=1)
def get_status_cached():
    # 실제 조회
    return get_status_from_dynamodb()

# 또는 ElastiCache/DynamoDB TTL 사용
# GET /api/status?cache=false → 강제 새로고침
```

**목표**: Status endpoint 응답 시간 50% 단축

**구현 계획**:
- [ ] Status API: in-memory cache 추가
- [ ] Cache invalidation: 새로운 check 완료 시
- [ ] cache-control headers 설정
- [ ] tests: 캐시 동작 검증

---

#### 3.3 Circuit Breaker for Gemini API

**현재 상태**:
- Gemini 호출 실패 → 즉시 timeout
- 폴백: MOCK_ANALYSIS

**최적화**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_gemini_api(events):
    # 5번 연속 실패 → 60초 동안 호출 안 함
    # 자동 복구 시도
    return gemini.analyze(events)

# 사용
try:
    result = call_gemini_api(events)
except CircuitBreakerListener:
    result = get_mock_analysis()
```

**목표**: Gemini 장애 → 빠른 폴백, 캐스케이드 실패 방지

**구현 계획**:
- [ ] responders/alert_formatter.py: circuit breaker 패턴 추가
- [ ] 설정: failure_threshold, recovery_timeout
- [ ] 모니터링: Circuit state 로깅
- [ ] tests: 회로 차단/복구 동작 테스트

---

## Sprint 18 구성

### Phase별 진행

```
Day 1: Phase 1 - SAM CLI 테스트 실행
├─ LocalStack 준비
├─ 모든 테스트 실행
├─ 버그 수정
└─ v1.1.1 tag (if needed)

Day 2: Phase 2 - AWS 성능 검증
├─ Lambda 배포
├─ 메트릭 수집
├─ 비교 분석
└─ 최적화 권장사항 문서화

Day 3: Phase 3 - v1.2 계획 상세화
├─ Multi-region parallelization 설계
├─ Caching 전략 수립
├─ Circuit breaker 구현 계획
└─ SPRINT_19_PLAN.md 작성
```

---

---

## 성공 지표

| 항목 | 대상 | 상태 |
|------|------|------|
| 모든 로컬 테스트 통과 | 60/60 | 🔄 |
| AWS 배포 성공 | 1회 | 🔄 |
| Cold start 비교 | LocalStack vs AWS | 🔄 |
| Multi-region parallel 설계 완료 | Design doc | 🔄 |
| v1.2 상세 계획 완료 | SPRINT_19_PLAN | 🔄 |

---

## 주의사항

1. **SAM CLI 요구사항**
   - 로컬 환경에 SAM CLI 필수
   - Docker 실행 중이어야 함 (LocalStack)
   - 첫 실행 시 초기화에 시간 소요 (~5분)

2. **AWS 배포**
   - AWS 계정 필요
   - 비용 고려 (Lambda: 무료 티어 범위 내, DynamoDB: 온디맨드)
   - 배포 후 cleanup 권장 (불필요한 리소스 삭제)

3. **성능 테스트**
   - 5회 이상 반복 테스트 (변동성 평균화)
   - 다양한 시간대 테스트 (Lambda 콜드 스타트 변동)
   - 네트워크 지연 고려

4. **Parallelization 위험**
   - 리전 수 × 체커 수 = 병렬 작업 수
   - API throttle 주의 (AWS API rate limit)
   - 에러 처리 강화 필요

---

## 산출물

- ✅ `docs/TESTING_EXECUTION_v1.1.md` - 테스트 결과
- ✅ `docs/AWS_PERFORMANCE_v1.1.md` - AWS 성능 데이터
- ✅ `docs/v1.2_DESIGN.md` - v1.2 기능 설계
- ✅ `docs/sprints/SPRINT_19_PLAN.md` - 다음 스프린트 계획
- 📦 `v1.1.1` tag (if bug fixes needed)

---

## 다음 스프린트 (Sprint 19)

Sprint 18의 계획 단계가 완료되면:
- **Phase 1**: Multi-region parallelization 구현
- **Phase 2**: Request caching 구현
- **Phase 3**: Circuit breaker 구현
- **Phase 4**: 성능 재측정 및 비교
- **Phase 5**: v1.2 릴리스 준비

---

**Sprint 18 Ready**: ✅ Plan Document Complete  
**Start Date**: 2026-05-06  
**Expected Completion**: 2026-05-07

---

*Last Updated*: 2026-05-05  
*Author*: Claude Code  
*Status*: 🔄 Awaiting Implementation
