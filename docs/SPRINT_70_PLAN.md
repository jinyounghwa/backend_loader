# Sprint 70: Advanced Threat Detection & Enterprise Features

> AWS Guardian v2.2 - CloudTrail 통합, IAM 이상 감지, GuardDuty 연계, 웹 대시보드

---

## 📋 Overview

| 항목 | 내용 |
|------|------|
| **버전** | AWS Guardian v2.2 |
| **기간** | 2026-05-30 ~ 2026-06-13 (14일) |
| **목표 테스트** | 68 tests (17 per phase) |
| **누적 목표** | 384 + 68 = 452 tests |
| **주요 기능** | CloudTrail, IAM 감시, GuardDuty, 웹 대시보드 |

---

## 🎯 Sprint 70 Phases

### Phase 1: CloudTrail 실시간 로그 분석 (17 tests)
**핵심 기능:**
- CloudTrail 이벤트 스트림 캡처 (EventBridge + Lambda)
- API 호출 이상 감지 (비정상 활동 패턴)
- 권한 변경 추적 (IAM 정책 수정)
- 리소스 삭제 감시 (EC2, S3, RDS)
- 이상 이벤트 → Telegram + Discord 알림

**구현 파일 (3개):**
1. `lambda/guardian/integrations/cloudtrail_analyzer.py` (400 lines)
   - CloudTrailEventParser: 이벤트 파싱 및 정규화
   - AnomalousActivityDetector: API 호출 패턴 이상 감지
   - PermissionChangeTracker: IAM 정책 변경 추적
   - ResourceDeleteMonitor: 리소스 삭제 감시

2. `lambda/guardian/pipelines/cloudtrail_pipeline.py` (300 lines)
   - CloudTrailPipeline: 엔드-투-엔드 처리 (EventBridge → Lambda → 분석)
   - EventNormalizer: 다양한 이벤트 형식 정규화

3. `tests/backend/test_cloudtrail_analysis.py` (350 lines)
   - 17 tests: 이벤트 파싱, 이상 감지, 권한 추적, 삭제 감시, 성능

**기술:**
- EventBridge + CloudTrail Events
- Pattern matching + Statistical anomaly detection
- DynamoDB 이벤트 저장

---

### Phase 2: IAM 이상 감지 및 권한 분석 (17 tests)
**핵심 기능:**
- IAM 정책 변경 감시 (과도한 권한 부여)
- 사용되지 않는 IAM 역할 탐지
- Cross-account 권한 분석
- Privilege escalation 감지
- 최소 권한 원칙 위반 탐지

**구현 파일 (3개):**
1. `lambda/guardian/analyzers/iam_analyzer.py` (400 lines)
   - IAMPolicyAnalyzer: 정책 분석 및 위험도 평가
   - PrivilegeEscalationDetector: 권한 상승 패턴 감지
   - UnusedRoleDetector: 미사용 역할 식별
   - CrossAccountAnalyzer: 교차 계정 권한 분석

2. `lambda/guardian/validators/iam_validator.py` (300 lines)
   - MinimumPrivilegeValidator: 최소 권한 검증
   - PolicyRiskScorer: 정책 위험도 점수 계산 (0-100)

3. `tests/backend/test_iam_analysis.py` (350 lines)
   - 17 tests: 정책 분석, 권한 상승, 미사용 역할, 교차 계정, 성능

**기술:**
- IAM Policy simulator (boto3)
- Graph-based permission analysis
- Machine learning 위험도 점수

---

### Phase 3: GuardDuty 통합 및 위협 연계 (17 tests)
**핵심 기능:**
- GuardDuty 발견 결과 수집
- 위협 심각도 분류 (CRITICAL/HIGH/MEDIUM/LOW)
- 기존 CloudTrail/IAM 감지와 연계
- 위협 캠페인 감지 (다중 신호 상관)
- 자동 대응 (격리, 차단, 알림)

**구현 파일 (3개):**
1. `lambda/guardian/integrations/guardduty_connector.py` (400 lines)
   - GuardDutyEventCollector: GuardDuty 발견 수집
   - ThreatSeverityClassifier: 심각도 분류
   - ThreatCorrelationEngine: 다중 신호 상관분석

2. `lambda/guardian/responders/guardduty_responder.py` (300 lines)
   - GuardDutyAutoResponder: 자동 대응 (격리, 알림)
   - ResponseOrchestrator: 대응 조율

3. `tests/backend/test_guardduty_integration.py` (350 lines)
   - 17 tests: 이벤트 수집, 심각도 분류, 상관분석, 자동 대응, 성능

**기술:**
- GuardDuty findings API
- Multi-signal correlation
- Automatic response orchestration

---

### Phase 4: 웹 대시보드 (Next.js + React) (17 tests)
**핵심 기능:**
- 실시간 위협 모니터링 대시보드
- CloudTrail 이벤트 로그 조회
- IAM 권한 분석 시각화
- GuardDuty 위협 현황
- 비용 트렌드 실시간 그래프
- 자동 대응 히스토리

**구현 파일 (4개):**
1. `frontend/pages/dashboard.tsx` (400 lines)
   - DashboardPage: 메인 대시보드 레이아웃
   - ThreatCard: 위협 현황 카드
   - CostChart: 비용 그래프
   - EventTimeline: CloudTrail 이벤트 타임라인

2. `frontend/components/ThreatTable.tsx` (300 lines)
   - 실시간 위협 테이블 (필터링, 정렬)

3. `frontend/api/dashboard.ts` (200 lines)
   - API endpoints (대시보드 데이터 조회)

4. `tests/frontend/test_dashboard.tsx` (350 lines)
   - 17 tests: 렌더링, 실시간 업데이트, 필터링, API 통합

**기술:**
- Next.js 14 (App Router)
- React 18 + TypeScript
- WebSocket 실시간 업데이트
- Recharts 데이터 시각화
- TanStack Table (데이터 테이블)

---

## 📊 Test Breakdown

| Phase | 기능 | 테스트 |
|-------|------|--------|
| 1️⃣ | CloudTrail 분석 | 17 |
| 2️⃣ | IAM 이상 감지 | 17 |
| 3️⃣ | GuardDuty 통합 | 17 |
| 4️⃣ | 웹 대시보드 | 17 |
| **합계** | **Sprint 70** | **68** |

**누적:**
```
Sprint 69:    62 tests ✅
Sprint 70:    68 tests (목표)
━━━━━━━━━━━━━━━━━━━━
누적 목표:   452 tests
현재:       384 tests
남은 작업:    68 tests
```

---

## 🛠️ 구현 전략

### CloudTrail 분석
- EventBridge → CloudTrail Events → Lambda 파이프라인
- 이벤트별 이상 점수 계산 (0-100)
- 임계값(70+) 초과 시 즉시 알림

### IAM 분석
- IAM Policy Simulator로 권한 검증
- 정책 위험도: AdministratorAccess(100) > PowerUser(80) > ...
- 최소 권한 원칙 위반 자동 감지

### GuardDuty 연계
- GuardDuty findings를 CloudTrail/IAM 이벤트와 상관분석
- 동시다발 위협 → 캠페인으로 분류
- 심각도 기반 자동 대응 (격리/차단)

### 웹 대시보드
- Lambda → API Gateway → Next.js API
- WebSocket으로 실시간 업데이트 (Sub/Pub 패턴)
- DynamoDB의 저장된 데이터 조회 + 실시간 스트리밍

---

## 📁 Directory Structure

```
aws-guardian/
├── lambda/guardian/
│   ├── integrations/
│   │   ├── cloudtrail_analyzer.py      (새로 생성)
│   │   └── guardduty_connector.py      (새로 생성)
│   ├── pipelines/
│   │   └── cloudtrail_pipeline.py      (새로 생성)
│   ├── analyzers/
│   │   └── iam_analyzer.py             (새로 생성)
│   ├── validators/
│   │   └── iam_validator.py            (새로 생성)
│   └── responders/
│       └── guardduty_responder.py      (새로 생성)
├── frontend/
│   ├── pages/
│   │   └── dashboard.tsx               (새로 생성)
│   ├── components/
│   │   └── ThreatTable.tsx             (새로 생성)
│   └── api/
│       └── dashboard.ts                (새로 생성)
├── tests/
│   ├── backend/
│   │   ├── test_cloudtrail_analysis.py (새로 생성)
│   │   ├── test_iam_analysis.py        (새로 생성)
│   │   └── test_guardduty_integration.py (새로 생성)
│   └── frontend/
│       └── test_dashboard.tsx          (새로 생성)
└── docs/
    └── SPRINT_70_PROGRESS.md           (추적용)
```

---

## ✅ Success Criteria

| 기준 | 목표 |
|------|------|
| CloudTrail 이상 감지 | 90% 정확도 |
| IAM 위험도 점수 | 0-100 range, consistency |
| GuardDuty 상관분석 | 2+ 신호 캠페인 감지 |
| 웹 대시보드 응답시간 | <500ms |
| 전체 테스트 통과 | 68/68 (100%) |
| 누적 테스트 | 452 tests |

---

## 📅 Estimated Timeline

| Phase | 소요 시간 | 예상 완료 |
|-------|----------|---------|
| 1. CloudTrail | 3-4일 | 2026-06-02 |
| 2. IAM 분석 | 3-4일 | 2026-06-06 |
| 3. GuardDuty | 3-4일 | 2026-06-10 |
| 4. 웹 대시보드 | 3-4일 | 2026-06-13 |
| **총 소요 시간** | **~14일** | **2026-06-13** |

---

## 🚀 Post-Sprint Activities

### Sprint 70 완료 후
1. 모든 68 tests PASS 확인
2. 누적 452 tests 달성 확인
3. 웹 대시보드 UI/UX 검증
4. 성능 벤치마크 (응답시간, 메모리)
5. 보안 감사 (IAM 정책, API 인증)

### Sprint 71+ 로드맵
- **Phase 1:** 다중 AWS 계정 지원
- **Phase 2:** 실시간 위협 대응 자동화
- **Phase 3:** 고급 머신러닝 이상 감지
- **Phase 4:** 모바일 앱 (iOS/Android)

---

## 💡 Technical Highlights

### CloudTrail 분석
```python
# 이상 점수 계산 예시
anomaly_score = (
    event_frequency_score * 0.4 +      # 빈도 (40%)
    permission_risk_score * 0.3 +      # 권한 위험 (30%)
    resource_sensitivity_score * 0.3   # 리소스 민감도 (30%)
)
# 70+: 알림, 80+: Critical, 90+: 자동 대응
```

### IAM 권한 분석
```python
# 최소 권한 검증
allowed_actions = IAM_POLICY_SIMULATOR.simulate(role, action)
required_actions = EXTRACT_FROM_LOGS(role)
excess_actions = allowed_actions - required_actions
risk_score = (excess_actions / allowed_actions) * 100
```

### GuardDuty 상관분석
```python
# 다중 신호 캠페인 감지
signals = [
    cloudtrail_anomaly,    # +30점
    iam_privilege_escalation,  # +30점
    guardduty_finding      # +40점
]
campaign_confidence = sum(signals) / 100  # 0-1.0
```

---

## 📝 Notes

- **CloudTrail**: 모든 API 호출 기록, 거의 실시간 (1-5분 지연)
- **IAM**: 정책은 복잡하므로 Simulator 사용 (실제 검증)
- **GuardDuty**: 별도 ML 기반 위협 탐지, 우리 분석과 보완
- **웹 대시보드**: 기존 Lambda/DynamoDB와 통합, 실시간 업데이트

---

**Sprint 70 준비 완료** ✅

다음 단계: Phase 1 (CloudTrail 분석) 구현 시작

