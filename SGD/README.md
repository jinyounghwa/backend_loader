# SGD: Sprint-Guided Development Methodology

**한국어 | [English](#english-version)**

---

## 탄생 배경

### 문제: Vibe Coding + AI 세션 단절

대규모 프로젝트를 AI(Claude)와 협업할 때 발생하는 문제들:

**1. 세션 단절 문제**
- Claude의 컨텍스트 윈도우는 약 200K 토큰 (충분하지만 제한적)
- 장시간 개발 후 컨텍스트가 압축되면 이전 결정사항을 잃음
- 같은 실수를 반복하거나 아키텍처 일관성이 깨짐
- 프로젝트 진행률을 파악하기 어려움

**2. Vibe Coding의 한계**
- 기분 따라 개발하면 구조가 산탄총처럼 흩어짐
- 테스트 없이 진행하면 나중에 대규모 버그 수정 필요
- 어떤 기능이 완성되었는지 불명확함
- 팀원(또는 미래의 자신)이 이해하기 어려움

**3. 결과**
```
┌─────────────────────────────────┐
│ 큰 기능 설계                     │
│ (흐릿함, 테스트 없음)           │
└────────────┬────────────────────┘
             │
    ┌────────▼───────┬──────────┬──────────┐
    │ 부분 구현      │ 부분 구현│ 부분 구현│
    │ (일관성 없음)  │(누락)    │(버그)    │
    └────────┬───────┴──────────┴──────────┘
             │
    ┌────────▼──────────────┐
    │ 나중에 대규모 수정     │
    │ (시간 낭비, 스트레스) │
    └───────────────────────┘
```

---

## SGD의 해결책

### Core Idea: Sprint Gate (스프린트 게이트)

각 Phase 완료 시 **"모든 테스트 PASS"** = 이전 상태로 복구 가능

```
Phase 1 (15 tests ✅)
    ↓
    [Git Commit + Snapshot]
    ↓
Phase 2 (10 tests ✅)  
    ↓
    [Git Commit + Snapshot]
    ↓
Phase 3 (8 tests ✅)
    ↓
    [Git Commit + Snapshot]
```

**핵심:**
- 각 Phase는 **원자적(atomic)** - 완전히 작동하거나 아예 없거나
- 세션이 끊겨도 마지막 성공한 Phase부터 재개 가능
- 테스트 = 신뢰도 증명서

---

## SDD와의 차이

| 항목 | SDD (Structured Design Dev) | SGD (Sprint-Guided Dev) |
|------|---------------------------|------------------------|
| **방향** | 위에서 아래로 (하향식) | 양방향 루프 (설계 ↔ 검증) |
| **테스트** | 사후 검증 | 사전 정의, 지속적 검증 |
| **커밋** | 기능 완성 시 | 각 Phase 완료 시 |
| **세션 단절** | 컨텍스트 손실 심각 | 복구 지점이 많음 (안전) |
| **AI 협업** | 어려움 (메모리 필요) | 용이 (Phase별 독립) |
| **1인 개발** | 가능하지만 힘듦 | 최적화됨 |

**예시:**

SDD는:
```
전체 설계 (50 페이지) → 구현 (3주) → 테스트 (2주) → 버그 수정 (?)
```

SGD는:
```
Sprint 계획 (1시간) → Phase 1 (2시간 + 테스트) ✅
                  → Phase 2 (3시간 + 테스트) ✅
                  → Phase 3 (2시간 + 테스트) ✅
                  → 누적 검증 + 커밋
```

---

## 개요

**SGD (Sprint-Guided Development)**는 대규모 소프트웨어 프로젝트를 구조화된 스프린트로 나누어 체계적으로 개발하는 방법론입니다.

AWS Guardian 프로젝트(263+ 테스트, 76,000+ 줄 코드)에서 검증된 실전 개발 방법론입니다.

---

## 핵심 원칙

### 1️⃣ **Phase 기반 분해**
- 각 Sprint를 3-5개의 작은 Phase로 나눔
- 각 Phase = 구체적인 기능 + 테스트 + 커밋
- Phase별 독립적 실행 가능 (의존성 최소화)

### 2️⃣ **명확한 테스트 목표**
- 각 Phase마다 구체적인 테스트 수 설정 (예: Phase 1 = 15 tests)
- 모든 테스트가 PASS할 때까지 Phase 완료 안 함
- 테스트 커버리지 = 신뢰성 증명

### 3️⃣ **매일 커밋**
- 각 Phase 완료 시 1개 커밋
- 커밋 메시지 = 변경사항 + 테스트 수 + 누적 진행도
- 이력 관리 & 진행도 시각화

### 4️⃣ **상세한 계획 문서**
- Sprint 시작 전 전체 계획 수립 (SPRINT_XX_PLAN.md)
- Phase별 구현 파일 목록 명시
- 성공 지표 정의

### 5️⃣ **실시간 메트릭 추적**
- 테스트 누적 수
- 코드 라인 수
- 개발 시간
- 버그율

---

## Sprint 구조

```
Sprint N (전체 목표)
├── Phase 1 (기능 A, Y 테스트)
│   ├── 구현 파일 목록
│   ├── 테스트 (Y개)
│   └── 커밋
├── Phase 2 (기능 B, Y 테스트)
│   ├── 구현 파일 목록
│   ├── 테스트 (Y개)
│   └── 커밋
├── Phase 3 (기능 C, Y 테스트)
└── ...
└── 최종 커밋 (누적 정보)
```

---

## 개발 사이클

### 1. Sprint 계획 (1-2시간)

```markdown
# Sprint N: 스프린트 제목

## 현황
- 이전 Sprint 완료: X 테스트
- 누적: Y 테스트
- 아키텍처 상태: [설명]

## 목표
- Phase 1: [기능], Z 테스트
- Phase 2: [기능], Z 테스트
- ...

## 파일 목록
- `path/file1.py` - [설명]
- `path/file2.py` - [설명]

## 구현 전략
[각 Phase별 상세 전략]
```

### 2. Phase 구현 (2-4시간)

```
1. 핵심 클래스/함수 구현
   └── imports 최소화 (상대 경로 사용)
   
2. 포괄적 테스트 작성
   └── fixtures 사용 (테스트 코드 간결화)
   └── 엣지 케이스 포함
   
3. 모든 테스트 PASS 확인
   └── pytest -v [test_file]
   
4. Phase 커밋
   └── git commit -m "feat: Sprint N Phase M - [설명] (Z tests)"
```

### 3. 커밋 메시지 템플릿

```
feat: Sprint 38 Phase 2 - Rule Performance Optimization (16 tests)

[상세 설명]

Components:
- Feature A: [설명]
- Feature B: [설명]

Test Coverage:
- Category 1: X tests
- Category 2: Y tests

Performance:
- Metric 1: value
- Metric 2: value

Cumulative: [prev] + [new] = [total] tests

Co-Authored-By: [Your Name] <noreply@[domain]>
```

---

## 문서 템플릿 (프로젝트 구성)

### 필수 파일 3가지

#### 1. CLAUDE.md (프로젝트 개요)

```markdown
# AWS Guardian System

> 간단한 설명 (1줄)

## 개요
- 배포 방식: AWS Lambda
- 주요 기능: ...
- 기술 스택: Python, DynamoDB, EventBridge

## 디렉토리 구조
```

**목적:**
- AI와 협업할 때 프로젝트 이해도 높이기
- 새로운 팀원 온보딩
- 핵심 설계 결정 문서화

#### 2. SKILL.md (메타 방법론)

```markdown
# SGD 적용 현황

## Sprint 구조
- Sprint 35: 규칙 테스트 (22 tests) ✅
- Sprint 36: 배포 시스템 (36 tests) ✅
- Sprint 37: 자동 대응 확장 (56 tests) ✅
- Sprint 38: 실시간 평가 (39 tests +)

## Phase 체크리스트
- [ ] 계획 수립
- [ ] Phase 구현 + 테스트
- [ ] 모든 테스트 PASS
- [ ] Git commit
```

**목적:**
- 전체 프로젝트 진행률 추적
- 다음 Phase 예측 가능
- 팀/협업자와 상태 공유

#### 3. SPRINT_XX_PLAN.md (상세 계획)

```markdown
# Sprint 38: 실시간 규칙 평가 및 성능 최적화

## 현황
- 이전 스프린트: 263 tests
- 누적: 263 tests

## 목표
- Phase 1: 실시간 규칙 평가 (23 tests)
- Phase 2: 성능 최적화 (16 tests)
- Phase 3: 비용 관리 (8 tests)
- Phase 4: 대시보드 UI (12 tests)
- Phase 5: 다중 계정 (10 tests)

## 파일 목록
| Phase | 파일 | 설명 |
|-------|------|------|
| 1 | handlers/rule_evaluation_handler.py | EventBridge 핸들러 |
| 2 | storage/rule_cache.py | TTL 캐시 |

## 구현 전략
[각 Phase별 구체적 전략]
```

**목적:**
- 각 Sprint의 완전한 로드맵
- 구현할 파일 목록 (메모리 용량 절약)
- AI 협업자가 이전 컨텍스트 없이도 이해 가능

---

## 1인 개발자를 위한 실전 예시

### Case Study: AWS Guardian (1인 개발)

**상황:**
- 프로젝트: AWS 계정 자동 감시 시스템
- 개발자: 1명
- 크기: 중대형 (263+ tests, 76,000+ lines)
- AI 협업: Claude와 함께 (세션 단절 빈번)

### 실제 진행 과정

**Sprint 35: 규칙 테스트 및 배포 시스템**

```
Day 1 (1시간 - 계획)
├─ SPRINT_35_PLAN.md 작성
├─ Phase 1-4 분해
├─ 파일 목록 명시
└─ 예상 시간: 22 tests

Day 1-2 (3시간 - Phase 1 구현)
├─ 핵심 클래스 작성
│  └─ TestExecutor: 샘플 로그로 규칙 테스트
├─ 포괄적 테스트 작성
│  └─ 9개 테스트 (6 백엔드 + 3 프론트엔드)
├─ 모든 테스트 PASS 확인
│  └─ pytest tests/backend/test_rule_testing.py -v ✅
└─ Git Commit
   └─ feat: Sprint 35 Phase 1 - Rule Dry-Run Testing (9 tests)

Day 2 (2시간 - Phase 2 구현)
├─ RuleDeploymentRepository 구현
├─ 배포 API 엔드포인트 작성
├─ 5개 테스트 모두 PASS
└─ Git Commit
   └─ feat: Sprint 35 Phase 2 - Rule Deployment System (5 tests)

[마찬가지로 Phase 3, 4 진행]

Result: 22 tests ✅
```

### 세션 단절 시나리오

**상황:** Phase 3 중간에 Claude 세션이 끊김

```
[Phase 1 ✅ - Git Commit] ← 안전한 체크포인트
[Phase 2 ✅ - Git Commit] ← 안전한 체크포인트
[Phase 3 진행 중... 세션 단절!]

재개 방법:
1. SPRINT_35_PLAN.md 읽기 (전체 컨텍스트)
2. git log --oneline (완료된 Phase 확인)
3. Phase 3 구현 재개
   └─ "지난번 완료: Phase 1, 2 (15 tests)"
   └─ "지금 하는 것: Phase 3 (4 tests)"
```

### AI 협업 팁

**Good Practice:**
```markdown
현황:
- 완료: Sprint 35 Phase 1-2 (14 tests)
- 진행: Sprint 35 Phase 3 (진도 50%)
- 계획: SPRINT_35_PLAN.md 참고

방금 작성한 코드:
[테스트 코드 일부]

다음 할 일:
- Phase 3 나머지 구현
- 모든 테스트 PASS 확인
```

**Bad Practice (컨텍스트 낭비):**
```
지금까지의 전체 코드를 보여주기
모든 파일의 이력을 설명하기
테스트 없이 구현 진행
```

### 실제 타이밍 계획

```
Sprint 35 (총 4시간, 22 tests)
├─ 1시간: 계획 (SPRINT_35_PLAN.md)
├─ 30분: Phase 1 구현
├─ 30분: Phase 1 테스트
├─ Git Commit
├─ 30분: Phase 2 구현
├─ 30분: Phase 2 테스트
├─ Git Commit
├─ [마찬가지로 Phase 3, 4]
└─ 최종: git log로 검증 (모든 커밋이 메타데이터)

Sprint 36 (다음 스프린트)
├─ 이전: 263 tests
├─ 이번: 36 tests 추가
└─ 누적: 299 tests

[보이는 진행률 = 객관적 성과]
```

---

## 실제 예시: AWS Guardian

### Sprint 37 (고급 자동 대응)
- **목표**: Lambda/RDS/VPC 자동 대응 지원
- **Phase 1-4**: 56 테스트
- **누적**: 263 테스트
- **코드 추가**: ~2,000줄
- **개발 시간**: ~8시간

### Sprint 38 Phase 1-2 (진행 중)
- **Phase 1**: 실시간 규칙 평가 (23 tests)
- **Phase 2**: 성능 최적화 (16 tests)
- **누적**: 302 테스트
- **대기**: Phase 3-5 (48 tests 예정)

---

## 장점

✅ **높은 품질**
- 테스트 기반 개발로 버그 최소화
- Phase별 독립 검증

✅ **진행도 명확**
- 누적 테스트 수로 객관적 진행도 측정
- 매일 커밋으로 히스토리 추적

✅ **팀 협업**
- 상세한 계획으로 역할 분담 용이
- 커밋 메시지로 변경사항 한눈에 파악

✅ **유지보수 용이**
- Phase별 기능 분리
- 테스트로 리팩토링 안전성 보장

---

## 체크리스트

### Sprint 시작 전
- [ ] SPRINT_XX_PLAN.md 작성
- [ ] Phase별 구현 파일 명시
- [ ] 테스트 수 목표 설정
- [ ] 팀원과 계획 공유

### Phase 완료 후
- [ ] 모든 테스트 PASS 확인
- [ ] 코드 리뷰 (가능시)
- [ ] 커밋 메시지 작성
- [ ] README 업데이트 (누적 정보)

### Sprint 완료 후
- [ ] 전체 테스트 PASS 확인
- [ ] 누적 통계 정리
- [ ] 다음 Sprint 계획 검토
- [ ] 레슨 런 (선택사항)

---

## 팁 & 트릭

### 1. 테스트 수 목표 설정
- 기능의 복잡도에 따라 5-20 테스트
- 일반적인 비율: 기능당 1-3 테스트/100줄 코드

### 2. Phase 크기 조정
- 너무 작음: 개별 커밋이 너무 많음
- 너무 큼: Phase 내에 실패 위험
- 권장: 30분~2시간 개발 = 1 Phase

### 3. 커밋 메시지 작성
- 첫 줄: 간결한 설명 (50자 이하)
- 본문: 변경사항 + 테스트 + 메트릭
- 정보성: 1-2년 뒤에도 이해 가능하도록

### 4. 성능 메트릭 추적
```
테스트 수 / 누적 시간 = 속도
코드 라인 / 테스트 = 커버리지 비율
버그 / 테스트 = 품질 지표
```

---

## 다른 프로젝트에 적용하기

### 1단계: 프로젝트 분석
```
큰 기능 → Sprint 분해 → Phase 분해 → 구현
(예: 인증 시스템 → Sprint N → Phase 1-3 → OAuth, JWT, 2FA)
```

### 2단계: 초기 계획
- 전체 Sprint 개수 예측
- 각 Sprint의 Phase 수 결정
- 테스트 수 목표 설정

### 3단계: 첫 Sprint 실행
- SPRINT_1_PLAN.md 작성
- Phase 1 구현 & 테스트
- 학습 & 조정

### 4단계: 지속적 개선
- 각 Sprint 후 회고
- 속도, 품질, 팀 만족도 추적
- 프로세스 조정

---

## 참고 자료

- `METHODOLOGY.md` - 상세한 방법론 가이드
- `TEMPLATE.md` - Sprint 계획 템플릿
- `EXAMPLES/` - 실제 Sprint 예시

---

<br>

# English Version

## Overview

**SGD (Sprint-Guided Development)** is a systematic development methodology for large-scale software projects, dividing work into structured sprints with clear phases and measurable test goals.

Validated on AWS Guardian project (263+ tests, 76,000+ lines of code).

---

## Core Principles

### 1️⃣ **Phase-Based Decomposition**
- Divide each Sprint into 3-5 small phases
- Each phase = specific feature + tests + commit
- Phases are independently executable (minimal dependencies)

### 2️⃣ **Clear Test Goals**
- Set specific test count per phase (e.g., Phase 1 = 15 tests)
- Phase not complete until all tests PASS
- Test coverage = reliability proof

### 3️⃣ **Daily Commits**
- 1 commit per phase completion
- Commit message = changes + test count + cumulative progress
- Version history & progress visualization

### 4️⃣ **Detailed Planning**
- Complete plan before sprint start (SPRINT_XX_PLAN.md)
- Explicit list of implementation files per phase
- Define success metrics

### 5️⃣ **Real-time Metrics**
- Cumulative test count
- Lines of code
- Development time
- Bug rate

---

## Sprint Structure

```
Sprint N (Overall Goal)
├── Phase 1 (Feature A, Y tests)
│   ├── File list
│   ├── Tests (Y)
│   └── Commit
├── Phase 2 (Feature B, Y tests)
├── Phase 3 (Feature C, Y tests)
└── ...
```

---

## Development Cycle

### Step 1: Sprint Planning (1-2 hours)
- Create SPRINT_XX_PLAN.md
- Define phases with test counts
- List all implementation files
- Describe implementation strategy per phase

### Step 2: Phase Implementation (2-4 hours)
1. Implement core classes/functions
2. Write comprehensive tests
3. Verify all tests PASS
4. Commit with detailed message

### Step 3: Commit Message Template
```
feat: Sprint 38 Phase 2 - Rule Performance Optimization (16 tests)

[Detailed description]

Components:
- Feature A: [description]
- Feature B: [description]

Test Coverage:
- Category 1: X tests
- Category 2: Y tests

Cumulative: [prev] + [new] = [total] tests
```

---

## Benefits

✅ **High Quality** - Test-based development minimizes bugs
✅ **Clear Progress** - Objective measurement via cumulative tests
✅ **Team Collaboration** - Detailed plans enable role division
✅ **Easy Maintenance** - Feature separation + tests ensure safety

---

## Applying to Other Projects

### Step 1: Analyze Project
```
Large Feature → Sprint Decomposition → Phase Decomposition → Implementation
Example: Auth System → Sprint N → Phase 1-3 (OAuth, JWT, 2FA)
```

### Step 2: Initial Planning
- Estimate total sprint count
- Decide phase count per sprint
- Set test count targets

### Step 3: Execute First Sprint
- Write SPRINT_1_PLAN.md
- Implement Phase 1 + tests
- Learn & adjust

### Step 4: Continuous Improvement
- Retrospective after each sprint
- Track velocity, quality, team satisfaction
- Adjust process

---

## Resources

- `METHODOLOGY.md` - Detailed methodology guide
- `TEMPLATE.md` - Sprint planning template
- `EXAMPLES/` - Real sprint examples

---

**Last Updated**: 2026-05-24
**Version**: 1.0
**Status**: Production-ready
