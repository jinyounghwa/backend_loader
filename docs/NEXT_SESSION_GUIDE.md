# Next Session 시작 가이드

**Created**: 2026-05-06  
**Target Date**: 2026-05-07 (또는 그 이후)  
**Sprint**: Sprint 19 - v1.2 성능 최적화

---

## 🚀 세션 시작 5분 안내

### 1단계: 환경 확인 (1분)

```bash
# 터미널에서 확인
$ cd /Users/younghwa.jin/Documents/backend_loader

# Python 버전 확인 (3.14.4 필요)
$ python --version
Python 3.14.4

# Virtual environment 활성화
$ source venv/bin/activate

# SAM CLI 버전 확인 (1.159.1)
$ sam --version
SAM CLI, version 1.159.1
```

### 2단계: 코드 상태 확인 (1분)

```bash
# Git 상태 확인
$ git status
On branch main
nothing to commit, working tree clean

# 최근 커밋 확인
$ git log --oneline -3
```

### 3단계: 테스트 상태 확인 (1분)

```bash
# 77/82 테스트 통과 확인
$ PYTHONPATH=/Users/younghwa.jin/Documents/backend_loader/tests/lambda:/Users/younghwa.jin/Documents/backend_loader/lambda \
python -m pytest tests/lambda/ -v --tb=no | tail -5
# Expected: 77 passed, 5 failed, 1 error
```

### 4단계: 다음 스프린트 계획 읽기 (2분)

```bash
# 구현 계획 읽기
cat docs/sprints/SPRINT_19_PLAN.md | head -100
```

---

## 📋 현재 상태 요약

### 완료된 것
```
✅ SAM 템플릿 생성 (sam.yaml)
✅ Lambda 함수 구조 최적화
✅ 77개 기능 테스트 통과 (93.9%)
✅ Gemini 협업 제거 (계정 이용정지 방지)
✅ Sprint 19 상세 계획 문서화
✅ 마무리 문서화 완료
```

### 남은 작업 (5개 성능 테스트)
```
⏳ Multi-region 성능 (순차 10s → 병렬 2.5s)
⏳ Status endpoint 캐싱 (500ms → 50ms)
⏳ Circuit breaker 구현 (Gemini API 안정성)
⏳ S3 버킷 정책 분석 최적화
⏳ 성능 회귀 테스트
```

---

## 🎯 Sprint 19 목표

### Phase 1: Multi-Region Parallelization (4시간)

**기대 효과**: 멀티 리전 실행 시간 10s → 2.5s (75% 단축)

**구현 파일**:
- `lambda/guardian/handler.py` - asyncio 다중 리전 병렬
- `lambda/guardian/checkers/base.py` - async 메서드 추가
- `tests/lambda/test_performance.py` - 성능 테스트

**검증 기준**:
```
Multi-region 4x: < 4초 ✓
Cold start: < 2.5초 (유지) ✓
에러 처리: 한 리전 실패 → 다른 리전 계속 ✓
```

**참고 코드**:
```python
# async 패턴
import asyncio

async def check_region_async(region):
    # EC2, S3, Cost 확인
    return {region: result}

# 병렬 실행
tasks = [check_region_async(r) for r in regions]
results = await asyncio.gather(*tasks)  # 동시 실행
```

---

### Phase 2: Request Caching (2시간)

**기대 효과**: Status API 응답 500ms → 50ms (95% 단축)

**구현 파일**:
- `lambda/guardian/handler.py` - @lru_cache 추가
- `tests/lambda/test_performance.py` - 캐시 동작 테스트

**캐시 전략**:
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_status_cached():
    """5분 TTL 캐시"""
    return get_status_from_dynamodb()

# 캐시 무효화
get_status_cached.cache_clear()  # 새 체크 완료 시
```

---

### Phase 3: Circuit Breaker (2시간)

**기대 효과**: Gemini API 실패 5회 후 자동 차단 + 자동 복구

**구현 파일**:
- `lambda/guardian/responders/alert_formatter.py` - circuit breaker
- `tests/lambda/test_circuit_breaker.py` - 상태 전이 테스트

**회로 상태**:
```
정상 (Closed)
    ↓ (5회 연속 실패)
차단 (Open) → 즉시 폴백 (MOCK_ANALYSIS)
    ↓ (60초 후)
반개방 (Half-Open) → 복구 시도
    ↓ (성공 시)
정상 (Closed)
```

---

## 📚 준비 문서

### 필독 (5분)
1. `docs/sprints/SPRINT_19_PLAN.md` - 상세 구현 계획
2. `docs/SPRINT_18_COMPLETION_SUMMARY.md` - 현재 상태

### 참고 (필요시)
3. `docs/SPRINT_18_SESSION_NOTES.md` - 기술 상세 기록
4. `docs/SPRINT_18_PHASE1_REPORT.md` - 테스트 분석
5. `NEXT_STEPS.md` - 전체 프로젝트 진행

### 코드 참고
- `sam.yaml` - Lambda 함수 정의
- `lambda/guardian/handler.py` - 메인 핸들러
- `tests/lambda/harness.py` - 테스트 헬퍼

---

## 🔧 시작 명령어

### Branch 생성
```bash
git checkout -b feature/v1.2-parallelization
```

### 테스트 실행 (검증)
```bash
source venv/bin/activate
PYTHONPATH=/Users/younghwa.jin/Documents/backend_loader/tests/lambda:/Users/younghwa.jin/Documents/backend_loader/lambda \
python -m pytest tests/lambda/test_performance.py -v
```

### SAM 로컬 테스트 (필요시)
```bash
sam build
sam local invoke GuardianChecker \
  --event events/sample_event.json \
  --env-vars lambda/env.json
```

---

## 📊 성공 지표

### Phase별 체크리스트

**Phase 1 완료 기준**:
- [ ] Asyncio 기반 병렬화 구현
- [ ] 모든 checker (Cost, EC2, S3)가 async 메서드 제공
- [ ] Multi-region 테스트 4개 리전 < 4초
- [ ] Cold start 여전히 < 2.5초
- [ ] 개별 리전 실패해도 다른 리전 계속 처리

**Phase 2 완료 기준**:
- [ ] @lru_cache 적용 (TTL 5분)
- [ ] Status API 첫 요청 ~500ms
- [ ] 캐시된 요청 < 50ms
- [ ] 새 체크 완료 시 캐시 무효화

**Phase 3 완료 기준**:
- [ ] pybreaker 통합
- [ ] 5회 연속 실패 후 circuit open
- [ ] Open 상태에서 MOCK_ANALYSIS 폴백
- [ ] 60초 후 반개방 → 자동 복구 시도

---

## ⚠️ 주의사항

### Asyncio 사용 시
- Lambda 콜드 스타트 영향 최소화
- Event loop 재사용 (warm invocation)
- 에러 처리: 한 리전 실패 → 다른 리전 계속

### 캐싱 전략
- TTL = 5분 (데이터 신선도 vs 계산 비용 균형)
- Cache invalidation 명확하게 (새 체크 완료 시)
- `?cache=false` 강제 새로고침 지원

### Circuit Breaker
- 상태 변화 로깅 (디버깅용)
- Half-open에서 recovery 시도 신중함
- Fallback (MOCK_ANALYSIS) 확실하게

---

## 🎓 기술 참고자료

### Asyncio 패턴
```python
import asyncio

async def main():
    # 동시 실행
    results = await asyncio.gather(
        check_region_async('us-east-1'),
        check_region_async('eu-west-1'),
        check_region_async('ap-northeast-1'),
        return_exceptions=True  # 한 개 실패해도 나머지 계속
    )
    return [r for r in results if not isinstance(r, Exception)]

# boto3는 thread-safe (asyncio와 호환)
# 하지만 async 버전이 아니므로 별도 처리 필요
```

### LRU Cache 패턴
```python
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def expensive_operation():
    return "cached_result"

# 캐시 상태 확인
print(expensive_operation.cache_info())
# CacheInfo(hits=10, misses=1, maxsize=1, currsize=1)

# 캐시 초기화
expensive_operation.cache_clear()
```

### Circuit Breaker 패턴
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_external_api():
    # 5회 연속 실패 후 60초 차단
    return external_api.call()

# 상태 확인
print(call_external_api.opened)  # True/False
```

---

## 📞 문제 해결

### 테스트 실패 시
1. `PYTHONPATH` 설정 확인
   ```bash
   echo $PYTHONPATH
   # Should include: tests/lambda, lambda directories
   ```

2. SAM 빌드 확인
   ```bash
   sam build --debug
   ```

3. 개별 테스트 실행
   ```bash
   pytest tests/lambda/test_performance.py::TestPerformanceRegression -v
   ```

### SAM invoke 오류 시
1. Docker 실행 확인 (LocalStack 필요할 경우)
2. SAM cache 초기화
   ```bash
   rm -rf .aws-sam/build/
   sam build
   ```

3. Python 경로 확인
   ```bash
   which python
   python -c "import sys; print(sys.path)"
   ```

---

## ✅ 최종 체크리스트

### 세션 시작 전
- [ ] 이 문서 읽음
- [ ] SPRINT_19_PLAN.md 읽음
- [ ] 현재 테스트 상태 확인 (77/82)
- [ ] Python 3.14.4 확인
- [ ] SAM CLI 설치 확인

### 세션 중
- [ ] Branch 생성 (feature/v1.2-*)
- [ ] Phase 1, 2, 3 순차 구현
- [ ] 각 phase 후 테스트 실행
- [ ] Performance baseline 수집

### 세션 종료 전
- [ ] 모든 변경사항 커밋
- [ ] 테스트 통과 확인
- [ ] 다음 세션용 문서 업데이트
- [ ] Branch push (또는 draft PR)

---

## 🎉 예상 결과

Sprint 19 완료 후:
```
✅ Multi-region 4x: 10s → 3-4s (실행 시간 75% 단축)
✅ Status API: 500ms → 50ms (응답 시간 90% 단축)
✅ Circuit Breaker: 자동 장애 격리 (5회 실패 후 폴백)
✅ 모든 77개 기능 테스트 + 성능 최적화 5개
✅ v1.2 tag 생성 → Sprint 20 릴리스 준비
```

---

**Ready to Start**: ✅  
**Next Sprint**: Sprint 19  
**Estimated Duration**: 8 hours (1-2 sessions)  
**Target Completion**: 2026-05-07 ~ 2026-05-08
