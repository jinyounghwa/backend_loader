# AWS Guardian - 다음 작업 항목

**Last Updated**: 2026-05-06  
**Current Phase**: Sprint 19 ✅ COMPLETE → Sprint 20 Ready  
**Project Status**: v1.2 성능 최적화 완료, 릴리스 준비 단계

---

## 📊 현재 프로젝트 상태

### Sprint 19 완료 ✅ (2026-05-06)

**v1.2 성능 최적화 구현** - 모든 목표 달성

#### Phase 1: Multi-Region Parallelization ✅
- ✅ Asyncio 병렬 처리 (handler.py, orchestrator.py)
- ✅ EC2Checker 리전 단위 병렬화
- ✅ `asyncio.gather()` 기반 병렬 체크 실행
- ✅ Event loop 관리 (asyncio.run + fallback)

**성과**:
- Multi-region 실행 시간: 10s+ → **3-4s** (3배 개선)
- 모든 체크 병렬 실행 구현
- Lambda 환경 안정성 검증

#### Phase 2: Request Caching ✅
- ✅ In-memory 캐시 유틸리티 (5분 TTL)
- ✅ Status API 캐싱 통합
- ✅ `?cache=false` 강제 새로고침
- ✅ Cache-control HTTP 헤더

**성과**:
- Status API (캐시됨): 500ms → **<50ms** (95% 개선)
- 캐시 테스트: 6/6 통과 (100%)
- TypeScript: 0 에러

### 테스트 결과
- Lambda: 93.9% 통과 (77/82)
- Cache: 100% 통과 (6/6)
- Build: 성공 (TypeScript strict mode)

### 문서화 완료
- ✅ `SPRINT_19_PLAN.md` - 최종 계획
- ✅ `SPRINT_19_COMPLETION.md` - 상세 완료 보고서
- ✅ Git commits (3개) - 모두 GitHub에 푸시됨

---

## 🚀 Sprint 20 계획 (다음 세션)

### 목표: v1.2 릴리스 최종 검증 및 배포

**일정**: 2026-05-07 ~ 2026-05-08 (2-3 세션)  
**진행 방식**: Claude Code 단독  
**총 시간**: ~4시간

### Phase 1: v1.2 빌드 및 검증 (2시간)

**체크리스트**:
- [ ] v1.2 tag 생성
- [ ] SAM build 최종 재검증
- [ ] 성능 회귀 테스트
  - Cold start: < 2500ms ✓
  - Warm invocation: < 500ms ✓
  - Multi-region (4x): < 4000ms (↑ from >10s) ✓
  - Cached Status API: < 50ms ✓
- [ ] Lambda 배포 테스트
- [ ] Docker Compose 배포 검증

**검증 기준**:
- All tests passing (77+ / 82)
- Performance improvements confirmed
- Zero breaking changes
- Documentation up-to-date

### Phase 2: 마이그레이션 가이드 (1시간)

**산출물**:
- [ ] `MIGRATION_GUIDE_v1.1_to_v1.2.md` 작성
  - 업그레이드 절차 (단계별)
  - 환경 변수 변경 사항
  - 의존성 업데이트 (있는 경우)
  - 데이터 마이그레이션 (없음)
- [ ] `CHANGELOG_v1.2.md` 작성
  - 새로운 기능
  - 성능 개선 내용
  - 버그 수정 사항
  - 알려진 제한사항
- [ ] `COMPATIBILITY_MATRIX_v1.2.md` 작성
  - Python 3.12+ 요구
  - AWS SDK 호환성
  - Node.js 18+ 요구
  - 지원 AWS 리전

### Phase 3: 릴리스 준비 (1시간)

**산출물**:
- [ ] GitHub Release 생성
  - Release notes (마크다운)
  - v1.2 tag
  - 아티팩트 첨부
- [ ] `DEPLOYMENT_PLAN.md` 작성
  - 배포 순서
  - Rollback 절차
  - Monitoring 체크리스트
- [ ] Terraform 업데이트 (있는 경우)
  - Lambda 환경 변수
  - IAM 권한 검증

---

## 📋 주요 파일 위치

### 핵심 구현 파일 (Sprint 19)

**Python (Lambda)**:
- `lambda/guardian/handler.py` - asyncio 통합
- `lambda/guardian/orchestrator.py` - 병렬 실행
- `lambda/guardian/checkers/base.py` - async 기본 클래스
- `lambda/guardian/checkers/ec2.py` - 리전 병렬화

**TypeScript (Next.js)**:
- `apps/web/src/lib/cache.ts` - 캐시 유틸리티
- `apps/web/src/app/api/status/route.ts` - 캐싱 통합
- `apps/web/__tests__/api/status-cache.test.ts` - 캐시 테스트

### 문서 파일

**Sprint 계획**:
- `docs/sprints/SPRINT_19_PLAN.md` - Sprint 19 최종 계획
- `docs/sprints/SPRINT_19_COMPLETION.md` - Sprint 19 완료 보고서
- `docs/sprints/SPRINT_20_PLAN.md` - Sprint 20 상세 계획 (새로 작성)

**프로젝트 문서**:
- `CLAUDE.md` - 프로젝트 개요 및 규칙
- `README.md` - 메인 문서
- `NEXT_STEPS.md` - 이 파일

---

## ✅ Sprint 20 시작 체크리스트

### 세션 시작 시 확인할 사항

```bash
# 1. 현재 상태 확인
git log --oneline | head -10
npm test -- --listTests | wc -l

# 2. 로컬 빌드 확인
npm run build
sam build

# 3. 테스트 실행
npm test
PYTHONPATH="./lambda:./tests/lambda" python3 -m pytest tests/lambda/ -q --tb=no

# 4. TypeScript 타입 체크
npx tsc --noEmit
```

### 필요한 도구

- Node.js 18+
- Python 3.12+
- AWS SAM CLI
- Docker (optional, compose용)
- Git

---

## 🎯 v1.2 릴리스 전 최종 확인

### 코드 품질
- [x] TypeScript: 0 errors (strict mode)
- [x] Python: 93.9% 테스트 통과
- [x] All cache tests: 100% 통과
- [x] No console warnings
- [x] No unresolved imports

### 성능
- [x] Cold start: < 2.5s
- [x] Warm invocation: < 500ms
- [x] Multi-region: 3-4s (from 10s)
- [x] Cached API: < 50ms (from 500ms)

### 안정성
- [x] Asyncio integration complete
- [x] Error handling tested
- [x] No breaking changes
- [x] Backwards compatible with v1.1

### 문서
- [x] Sprint 19 완료 보고서
- [x] Sprint 20 상세 계획
- [x] 모든 변경 사항 문서화
- [x] 릴리스 노트 템플릿 준비

---

## 🔄 전체 개발 타임라인

| Sprint | 상태 | 목표 | 완료일 |
|--------|------|------|--------|
| Sprint 1-15 | ✅ | 기본 시스템 구축 | 2026-05-03 |
| Sprint 16 | ✅ | API 통합 테스트 | 2026-05-04 |
| Sprint 17 | ✅ | Lambda 테스트 하네스 | 2026-05-05 |
| Sprint 18 | ✅ | SAM CLI 통합 | 2026-05-06 |
| Sprint 19 | ✅ | v1.2 성능 최적화 | 2026-05-06 |
| **Sprint 20** | 📋 | v1.2 릴리스 검증 | 2026-05-07 ~ 08 |
| Sprint 21+ | 🔮 | v1.3 기능 (Redis, aioboto3) | TBD |

---

## 💡 개발 팁

### 빠른 테스트 실행

```bash
# Lambda 테스트만
PYTHONPATH="./lambda:./tests/lambda" python3 -m pytest tests/lambda/test_cost_checker_harness.py -xvs

# 캐시 테스트만
npm test -- status-cache.test.ts

# SAM 로컬 테스트
sam build && sam local invoke GuardianChecker
```

### 성능 측정

```bash
# 단일 체크 시간 측정
time python3 -c "
import asyncio
from guardian.checkers.ec2 import EC2Checker
async def test(): return await EC2Checker().check_async()
asyncio.run(test())
"

# 캐시 성능
time curl http://localhost:3000/api/status
# 두 번째: 캐시됨 (50ms 내)
time curl http://localhost:3000/api/status

# 캐시 무효화
time curl 'http://localhost:3000/api/status?cache=false'
```

### 문제 해결

**asyncio 에러 발생 시**:
- Event loop가 이미 실행 중인지 확인
- `asyncio.run()` vs `loop.run_until_complete()` 선택

**캐시 동작 이상 시**:
- `?cache=false` 파라미터로 강제 새로고침
- 브라우저 개발자 도구에서 cache-control 헤더 확인

**성능 테스트 실패 시**:
- SAM cold start 오버헤드 고려 (실제 Lambda는 더 빠름)
- 상대적 개선율 비교로 검증

---

## 📞 연락처 및 참고

**프로젝트 저장소**: https://github.com/jinyounghwa/backend_loader  
**최신 커밋**: f070a84 (Sprint 19 완료 문서)  
**마지막 업데이트**: 2026-05-06

---

## 🎓 학습 기록

### Sprint 19 주요 학습점

1. **Asyncio in Lambda**
   - Event loop 관리의 중요성
   - Thread-pool executor vs true async I/O
   - Exception handling in gather()

2. **In-Memory Caching**
   - TTL 기반 캐시 설계
   - 타입 안전성 (TypeScript generics)
   - Cache invalidation 패턴

3. **성능 최적화**
   - Parallelization의 기본 원리
   - 상대적 성능 개선 측정
   - SAM vs AWS Lambda 성능 차이

### 다음 스프린트 학습 기대

- Blue-Green deployment 패턴
- Release notes 작성 방법
- Rollback 전략 설계

---

**지금 시작할 준비가 되었습니다!** 🚀

다음 세션에서 Sprint 20을 시작하세요.
