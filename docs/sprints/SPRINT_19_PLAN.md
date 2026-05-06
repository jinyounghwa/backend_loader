# Sprint 19: v1.2 성능 최적화 구현

**Status**: 🔄 PLANNED  
**Start Date**: 2026-05-06 (이후)  
**Duration**: 1-2 sessions  
**Goals**: Multi-region parallelization, request caching, circuit breaker 구현

---

## 컨텍스트

**Sprint 18 완료 상태**:
- ✅ Phase 1: SAM CLI 테스트 검증 (82/82 tests passing 목표)
- ✅ SAM 템플릿 생성 및 최적화
- ⏳ Phase 2: AWS 성능 검증 (예정)
- ⏳ Phase 3: v1.2 설계 (예정)

**v1.2 성능 목표**:
- Multi-region: 10s → **3-4s** (3배 향상)
- Status endpoint: 원본 → **50% 단축** (캐싱)
- Gemini API 안정성: **Circuit breaker** 추가

---

## Sprint 19 목표

### Phase 1: Multi-Region Parallelization (4시간)

**현재 상태**:
```python
# Sequential (10초)
for region in regions:
    result = check_region(region)  # 2.5s × 4 = 10s
```

**최적화 목표**:
```python
# Parallel (2.5초)
tasks = [check_region_async(r) for r in regions]
results = await asyncio.gather(*tasks)
```

**구현 항목**:
- [ ] handler.py: asyncio 다중 리전 병렬 처리
- [ ] checkers/base.py: async 메서드 추가 (cost, ec2, s3)
- [ ] responders: async notification 호출 수정
- [ ] tests/lambda/test_performance.py: 병렬 성능 테스트
- [ ] CloudWatch 모니터링 설정

**검증**:
- Cold start: < 2.5s (baseline 유지)
- Warm: < 500ms (baseline 유지)
- Multi-region 4x: < 4s (목표: 3-4s)

**주의사항**:
- boto3는 thread-safe ✅
- DynamoDB 병렬 write 시 throttle 주의
- 한 리전 실패 → 다른 리전 계속 진행

---

### Phase 2: Request Caching (2시간)

**현재 상태**:
- GET /api/status: 매번 DynamoDB 조회 + 계산
- 1시간마다 업데이트되는 데이터

**최적화**:
```python
@lru_cache(maxsize=1)
def get_status_cached():
    return get_status_from_dynamodb()

# 또는 ElastiCache 사용
# GET /api/status?cache=false → 강제 새로고침
```

**구현 항목**:
- [ ] Status API: in-memory cache 추가
- [ ] Cache TTL: 5분 설정
- [ ] Cache invalidation: 새 check 완료 시 무효화
- [ ] cache-control 헤더 설정
- [ ] tests: 캐시 동작 검증

**검증**:
- 첫 요청: ~500ms (full computation)
- 캐시된 요청: < 50ms (95% 단축)
- 캐시 만료 후: 재계산

---

### Phase 3: Circuit Breaker (2시간)

**현재 상태**:
```python
# Gemini 호출 실패 → 즉시 timeout
# 폴백: MOCK_ANALYSIS
```

**최적화**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_gemini_api(events):
    # 5번 연속 실패 → 60초 동안 호출 안 함
    # 자동 복구 시도
    return gemini.analyze(events)
```

**구현 항목**:
- [ ] responders/alert_formatter.py: circuit breaker 패턴
- [ ] 설정: failure_threshold=5, recovery_timeout=60
- [ ] 모니터링: Circuit state 로깅
- [ ] tests: 회로 차단/복구 테스트

**검증**:
- 연속 5번 실패 시 circuit open ✅
- Open 상태에서 즉시 폴백 ✅
- 60초 후 half-open → 자동 복구 시도 ✅
- 로그에 circuit state 변화 기록 ✅

---

## Sprint 19 구성

### Phase별 진행

```
Phase 1: Multi-Region Parallelization (4시간)
├─ asyncio 설계 및 구현
├─ 성능 테스트
└─ CloudWatch 메트릭 수집

Phase 2: Request Caching (2시간)
├─ LRU cache 구현
├─ TTL 관리
└─ 캐시 무효화 로직

Phase 3: Circuit Breaker (2시간)
├─ Circuit breaker 라이브러리 선택
├─ 통합 및 테스트
└─ 모니터링 설정
```

**Total Duration**: ~8시간

---

## 기술 결정

### Multi-Region Parallelization
**선택**: asyncio (가볍고 Lambda 환경에 적합)
- boto3는 thread-safe ✅
- 이미 Python 3.12+ 표준 라이브러리 ✅
- Lambda 콜드 스타트에 유리 ✅

### Request Caching
**선택**: functools.lru_cache (simple) + optional ElastiCache
- 간단한 구현 ✅
- Lambda stateless 설계와 일치 ✅
- 향후 ElastiCache로 확장 가능 ✅

### Circuit Breaker
**선택**: pybreaker 라이브러리 (또는 custom)
- 가벼운 라이브러리 ✅
- explicit state 추적 가능 ✅
- 로깅 및 모니터링 용이 ✅

---

## 성공 지표

| 항목 | 대상 | 상태 |
|------|------|------|
| Multi-region 성능 | 10s → 3-4s | 🔄 |
| Status endpoint | 원본 → 50% 단축 | 🔄 |
| Circuit breaker | 5회 실패 후 open | 🔄 |
| 모든 테스트 | 82/82 passing | 🔄 |
| CloudWatch 메트릭 | Duration p99 수집 | 🔄 |

---

## 주의사항

1. **Asyncio 사용 시**
   - Lambda 콜드 스타트 영향 최소화
   - Event loop 재사용 (warm invocation)
   - 에러 처리: 한 리전 실패 → 다른 리전 계속

2. **캐싱 전략**
   - TTL = 5분 (balance freshness vs computation)
   - Cache invalidation 명확하게
   - `?cache=false` 강제 새로고침 지원

3. **Circuit Breaker**
   - State 변화 로깅 (디버깅용)
   - Half-open 상태에서 recovery 시도
   - Fallback (MOCK_ANALYSIS) 확실하게

---

## 산출물

- ✅ `lambda/guardian/handler.py` - asyncio 기반 병렬 처리
- ✅ `lambda/guardian/checkers/base.py` - async 메서드
- ✅ `lambda/guardian/responders/alert_formatter.py` - circuit breaker
- ✅ `tests/lambda/test_performance.py` - 병렬 성능 테스트
- ✅ `docs/v1.2_PERFORMANCE.md` - 성능 비교 문서
- ✅ `docs/v1.2_DESIGN.md` - 최종 설계 문서
- ✅ `v1.2` tag

---

## 다음 스프린트 (Sprint 20)

Sprint 19 완료 후:
- **Phase 1**: v1.2 릴리스 준비
- **Phase 2**: 성능 회귀 테스트
- **Phase 3**: 프로덕션 배포 검증

---

**Sprint 19 Ready**: 🔄 계획 중  
**Target Start**: 2026-05-07 (이후)  
**Target Completion**: 2026-05-07 ~ 2026-05-08  
**Implementation**: Claude Code (단독)

---

*Created*: 2026-05-06  
*Status*: 🔄 Planning Phase
