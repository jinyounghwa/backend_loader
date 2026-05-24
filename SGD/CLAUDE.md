# AWS Guardian: 자동 감시 & 자동 대응 시스템

> AWS 계정을 실시간으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응 + Discord 대시보드로 제어하는 서버리스 보안/비용 감시 시스템

---

## 프로젝트 정보

| 항목 | 내용 |
|------|------|
| **상태** | 활발히 진행 중 (Sprint 38) |
| **규모** | 263+ tests, 76,000+ LOC |
| **개발 방식** | SGD (Sprint-Guided Development) |
| **배포** | AWS Lambda (서버리스) |
| **주기** | EventBridge (1분/5분/1시간) |
| **알림** | Telegram Bot |
| **제어** | Discord Bot + Slash Command |

---

## 아키텍처

```
CloudTrail / Cost Explorer
        ↓
   DynamoDB Streams
        ↓
EventBridge (1h 주기)
        ↓
   Lambda Handler
   ├─ AnomalyDetector (규칙 평가)
   ├─ ResponseOrchestrator (자동 대응)
   └─ AuditLogger (이력 기록)
        ↓
    ┌───┴───┬────────┐
    ↓       ↓        ↓
Telegram Discord DynamoDB
 Alert   Dashboard  Storage
```

---

## 핵심 기능

### 1. 규칙 기반 탐지
- **규칙 저장소**: SecurityRulesTable (DynamoDB)
- **규칙 캐시**: RuleCache (TTL 300s, 메모리)
- **병렬 평가**: ParallelEvaluator (asyncio)

### 2. 자동 대응
- EC2: 인스턴스 자동 중지
- S3: 퍼블릭 액세스 자동 차단
- Lambda: 함수 버전 관리
- RDS: 데이터베이스 백업 및 스냅샷
- VPC: 보안 그룹 규칙 자동 수정

### 3. 실시간 모니터링
- WebSocket 기반 실시간 업데이트
- 규칙별 상태 표시
- 대응 이력 타임라인
- 비용 추이 그래프

---

## 디렉토리 구조

```
aws-guardian/
├── SGD/                          # Sprint-Guided Development 방법론
│   ├── README.md                 # 전체 가이드
│   ├── CLAUDE.md                 # 프로젝트 개요 (이 파일)
│   ├── SKILL.md                  # 메타 진행률
│   └── SPRINT_TEMPLATE.md        # Sprint 계획 템플릿
│
├── lambda/guardian/              # Lambda 함수 (메인)
│   ├── handlers/
│   │   ├── rule_evaluation_handler.py      # 규칙 평가 (EventBridge)
│   │   ├── remediation_handler.py          # 자동 대응 실행
│   │   └── audit_handler.py                # 감사 로그
│   │
│   ├── detectors/
│   │   ├── anomaly_detector.py             # 이상 탐지
│   │   ├── parallel_evaluator.py           # 병렬 평가
│   │   └── threat_classifier.py            # 위협 분류
│   │
│   ├── responders/
│   │   ├── ec2_responder.py                # EC2 자동 대응
│   │   ├── s3_responder.py                 # S3 자동 대응
│   │   ├── lambda_responder.py             # Lambda 자동 대응
│   │   ├── rds_responder.py                # RDS 자동 대응
│   │   └── vpc_responder.py                # VPC 자동 대응
│   │
│   ├── storage/
│   │   ├── security_rules.py               # 규칙 저장소
│   │   ├── rule_cache.py                   # 규칙 캐시
│   │   ├── cost_history.py                 # 비용 이력
│   │   ├── audit_logs.py                   # 감사 로그
│   │   └── threat_history.py               # 위협 이력
│   │
│   └── analyzers/
│       ├── anomaly_detector.py             # 이상 탐지 분석
│       └── cost_analyzer.py                # 비용 분석
│
├── apps/web/                     # Next.js 웹 대시보드
│   ├── src/components/Dashboard/
│   │   ├── RealTimeMonitoring.tsx          # 실시간 모니터링
│   │   ├── ResponseHistory.tsx             # 대응 이력
│   │   ├── CostMonitor.tsx                 # 비용 모니터
│   │   └── RuleManagement.tsx              # 규칙 관리
│   │
│   └── src/app/api/guardian/
│       ├── rules/route.ts                  # 규칙 CRUD
│       ├── threats/route.ts                # 위협 조회
│       ├── responses/route.ts              # 대응 이력
│       └── realtime/route.ts               # WebSocket
│
├── sam/                          # AWS SAM (Infrastructure)
│   ├── template.yaml             # 전체 CloudFormation
│   └── samconfig.toml            # SAM 설정
│
├── tests/                        # 테스트 (263+ tests)
│   ├── backend/
│   │   ├── test_rule_evaluation_realtime.py     (23 tests)
│   │   ├── test_rule_performance.py             (16 tests)
│   │   ├── test_cost_analysis.py                (8 tests)
│   │   ├── test_anomaly_detection.py            (18 tests)
│   │   └── ...
│   │
│   └── frontend/
│       ├── test_realtime_dashboard.tsx          (12 tests)
│       ├── test_rule_management.tsx             (8 tests)
│       └── ...
│
├── CLAUDE.md                     # 프로젝트 개요
├── SKILL.md                      # 메타 진행률
├── SPRINT_38_PLAN.md             # 현재 Sprint 계획
├── README.md                     # 프로젝트 README
└── package.json, requirements.txt, sam.yaml 등
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| **Compute** | AWS Lambda (Python 3.12) |
| **Scheduling** | AWS EventBridge (cron) |
| **Storage** | AWS DynamoDB |
| **Analysis** | AWS Cost Explorer API |
| **Infrastructure** | AWS SAM (CloudFormation) |
| **Alerts** | Telegram Bot API |
| **Dashboard** | Discord Bot (interactions.py) |
| **Frontend** | Next.js 16.2, React 19, TailwindCSS |
| **Testing** | pytest (백엔드), Jest (프론트엔드) |

---

## 개발 진행 (Sprint별)

### 완료된 Sprints

| Sprint | 목표 | 테스트 | 누적 |
|--------|------|--------|------|
| 35 | 규칙 테스트 & 배포 | 22 | 22 |
| 36 | 배포 인식 평가 | 36 | 58 |
| 37 | 다중 서비스 대응 | 56 | 114 |
| 38 Phase 1 | 실시간 평가 | 23 | 137 |
| 38 Phase 2 | 성능 최적화 | 16 | 153 |

### 진행 중 (Sprint 38)

| Phase | 목표 | 테스트 | 상태 |
|-------|------|--------|------|
| 1 | 실시간 규칙 평가 | 23 | ✅ Complete |
| 2 | 규칙 성능 최적화 | 16 | ✅ Complete |
| 3 | 비용 관리 기능 | 8 | 🔄 In Progress |
| 4 | 대시보드 UI 개선 | 12 | ⏳ Planned |
| 5 | 다중 계정 지원 | 10 | ⏳ Planned |

**목표:** Sprint 38 완료 시 총 **332 tests** 달성

---

## 핵심 설계 결정

### 1. Phase 기반 분해
- **이유**: 각 단계마다 테스트 가능한 완전한 기능
- **이점**: 세션 단절해도 마지막 Phase부터 재개 가능

### 2. 병렬 규칙 평가
- **이유**: 규칙 수 증가 시 성능 저하 방지
- **구현**: asyncio 기반 ParallelEvaluator
- **성능**: 100개 규칙 → <5초

### 3. 규칙 캐싱 (TTL 300s)
- **이유**: Cost Explorer API 호출 최소화 (비용)
- **구현**: 메모리 기반 RuleCache + 스레드 안전
- **효율**: 66-75% 히트율

### 4. 원자적 대응
- **이유**: 부분 실패 방지 (일관성)
- **구현**: ResponseOrchestrator (트랜잭션 패턴)
- **보장**: 모두 성공하거나 모두 롤백

---

## 주요 의존성

### Backend
- `boto3`: AWS SDK
- `asyncio`: 비동기 처리
- `pytest`: 테스트 프레임워크
- `python-json-logger`: 구조화된 로깅

### Frontend
- `next.js@16.2.4`: React 프레임워크
- `react@19.2.4`: UI 라이브러리
- `tailwindcss@4`: CSS 유틸리티
- `swr`: 데이터 페칭

### Deployment
- `aws-cdk` 또는 `aws-sam-cli`: Infrastructure as Code

---

## 성공 지표 (Sprint 38)

| 항목 | 목표 | 현재 |
|------|------|------|
| **총 테스트** | 332 | 153 (진행 중) |
| **코드 라인** | 80,000+ | 76,000+ |
| **캐시 히트율** | >70% | 75% ✅ |
| **평가 시간** | <5초 (100 rules) | 3.2초 ✅ |
| **대응 성공률** | >95% | 97% ✅ |

---

## 시작하기

### 1. 저장소 클론
```bash
git clone <repo>
cd aws-guardian
```

### 2. 환경 설정
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 테스트 실행
```bash
python3 -m pytest tests/ -v
```

### 4. 배포
```bash
sam build
sam deploy --guided
```

---

## 문서

- `SGD/README.md`: Sprint-Guided Development 방법론
- `SKILL.md`: 프로젝트 메타 정보 및 진행률
- `SPRINT_38_PLAN.md`: Sprint 38 상세 계획
- `README.md`: 프로젝트 사용 설명서

---

**Last Updated:** 2026-05-24  
**Maintainer:** jinyounghwa  
**Status:** 🔄 Active Development
