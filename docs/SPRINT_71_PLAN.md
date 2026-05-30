# Sprint 71: Multi-Account & Real-time Response Automation

> AWS Guardian v2.3 - 다중 계정 지원, 실시간 위협 대응 자동화, 고급 ML 이상 감지, 모바일 앱

---

## 📋 Overview

| 항목 | 내용 |
|------|------|
| **버전** | AWS Guardian v2.3 |
| **기간** | 2026-05-30 ~ 2026-06-13 (14일) |
| **목표 테스트** | 68 tests (17 per phase) |
| **누적 목표** | 462 + 68 = 530 tests |
| **주요 기능** | 다중 계정, 실시간 대응, 고급 ML, 모바일앱 |

---

## 🎯 Sprint 71 Phases

### Phase 1: 다중 AWS 계정 지원 (17 tests)
**핵심 기능:**
- 교차 계정 역할 가정 (AssumeRole)
- 계정별 독립적인 CloudTrail/IAM/GuardDuty 모니터링
- 계정별 대시보드 및 경고 분리
- 중앙 통제 센터에서 모든 계정 통합 모니터링
- 계정별 비용 집계 및 분석

**구현 파일 (3개):**
1. `lambda/guardian/multi_account/account_manager.py` (400 lines)
   - AccountRegistry: 계정 등록 및 관리
   - RoleAssumer: 교차 계정 역할 가정
   - AccountAggregator: 계정별 데이터 수집

2. `lambda/guardian/multi_account/account_router.py` (300 lines)
   - EventRouter: 이벤트를 올바른 계정 핸들러로 라우팅
   - AccountContext: 계정 컨텍스트 관리

3. `tests/backend/test_multi_account.py` (350 lines)
   - 17 tests: 계정 등록, 역할 가정, 데이터 집계, 라우팅

**기술:**
- AWS STS AssumeRole
- DynamoDB (계정 메타데이터)
- 계정별 Lambda 실행 역할

---

### Phase 2: 실시간 위협 대응 자동화 (17 tests)
**핵심 기능:**
- 위협 탐지 → 자동 대응 (0 수동 개입)
- 심각도별 자동화 정책 (Critical: 격리, High: 차단, Medium: 경고)
- 대응 실행 보고서 생성
- 대응 취소 및 복구 기능
- 대응 감사 로그 (DynamoDB)

**구현 파일 (3개):**
1. `lambda/guardian/responders/threat_responder.py` (400 lines)
   - ThreatResponder: 위협별 자동 대응 결정
   - ResponseExecutor: 실제 대응 실행 (EC2 Stop, SG 수정, IAM 차단)
   - ResponseTracker: 대응 상태 추적

2. `lambda/guardian/responders/response_policy.py` (300 lines)
   - ResponsePolicy: 심각도별 대응 정책 정의
   - PolicyEvaluator: 정책 평가 및 적용

3. `tests/backend/test_threat_responder.py` (350 lines)
   - 17 tests: 자동 대응 실행, 정책 평가, 감사 로그, 복구

**기술:**
- AWS Systems Manager (원격 실행)
- EventBridge 규칙 (자동 트리거)
- DynamoDB 감사 로그
- SNS/SQS (대응 큐)

---

### Phase 3: 고급 머신러닝 이상 감지 (17 tests)
**핵심 기능:**
- 자동 이상 감지 (정상 패턴 학습 후 편차 감지)
- 시계열 분석 (ARIMA, Prophet, Isolation Forest)
- 동작 기반 프로파일 (각 사용자/역할의 정상 행동)
- 컨텍스트 기반 이상 점수 (시간, 요일, 계절성)
- 이상 예측 (다음 24시간 위협 확률)

**구현 파일 (3개):**
1. `lambda/guardian/ml/behavioral_analyzer.py` (400 lines)
   - BehavioralProfiler: 사용자/역할 정상 행동 프로파일
   - AnomalyDetector: 동작 기반 이상 감지
   - ContextScorer: 컨텍스트 기반 점수 (시간, 위치, 디바이스)

2. `lambda/guardian/ml/anomaly_predictor.py` (300 lines)
   - AnomalyPredictor: 이상 발생 예측
   - ThreatProbability: 다음 24시간 위협 확률 계산

3. `tests/backend/test_behavioral_ml.py` (350 lines)
   - 17 tests: 프로파일링, 이상 감지, 컨텍스트, 예측

**기술:**
- Isolation Forest (비정상 탐지)
- ARIMA/Prophet (시계열)
- Clustering (그룹 프로파일)
- 확률 모델 (위협 예측)

---

### Phase 4: 모바일 앱 (iOS/Android) (17 tests)
**핵심 기능:**
- iOS/Android 네이티브 앱
- 실시간 위협 알림 (푸시 알림)
- 빠른 조치 (1-탭 격리, EC2 중지)
- 대시보드 모바일 버전 (그래프, 테이블)
- 오프라인 모드 (마지막 상태 캐시)

**구현 파일 (4개):**
1. `mobile/lib/screens/dashboard_screen.dart` (400 lines)
   - DashboardScreen: 모바일 대시보드 메인
   - ThreatCard: 위협 카드 (탭해서 상세 보기)
   - QuickActionButton: 빠른 조치 버튼

2. `mobile/lib/services/api_service.dart` (300 lines)
   - MobileApiService: 모바일 API 클라이언트
   - PushNotificationHandler: 푸시 알림 처리

3. `mobile/lib/models/threat.dart` (200 lines)
   - ThreatModel: 위협 데이터 모델
   - ResponseModel: 대응 결과 모델

4. `tests/mobile/test_dashboard_screen.dart` (350 lines)
   - 17 tests: 렌더링, 탭 처리, API 호출, 푸시 알림, 오프라인 모드

**기술:**
- Flutter (iOS/Android 동시 지원)
- Firebase Messaging (푸시 알림)
- Local Storage (오프라인 캐시)
- BLoC 패턴 (상태 관리)

---

## 📊 Test Breakdown

| Phase | 기능 | 테스트 |
|-------|------|--------|
| 1️⃣ | 다중 계정 지원 | 17 |
| 2️⃣ | 실시간 대응 자동화 | 17 |
| 3️⃣ | 고급 ML 이상 감지 | 17 |
| 4️⃣ | 모바일 앱 | 17 |
| **합계** | **Sprint 71** | **68** |

**누적:**
```
Sprint 69:    62 tests ✅
Sprint 70:    78 tests ✅
Sprint 71:    68 tests (목표)
━━━━━━━━━━━━━━━━━━━━━━
누적 목표:   530 tests
현재:       462 tests
남은 작업:    68 tests
```

---

## 🛠️ 구현 전략

### 다중 계정 지원
- STS AssumeRole로 각 계정의 리소스 접근
- 계정별 Lambda 실행 역할 자동 생성
- DynamoDB에 계정 메타데이터 저장
- 중앙 대시보드에서 모든 계정 통합 모니터링

### 실시간 대응 자동화
- CloudTrail 이벤트 → 대응 결정 (0.5초 내)
- Systems Manager로 EC2 명령 원격 실행
- DynamoDB에 모든 대응 기록
- SNS로 관리자에게 대응 결과 통보

### 고급 ML 이상 감지
- 매일 사용자/역할의 정상 행동 프로파일 업데이트
- 이상 점수 = (동작 이상도 + 컨텍스트 이상도) / 2
- 시간/요일/계절성을 고려한 기준선 조정
- 다음 24시간 위협 확률 예측

### 모바일 앱
- Flutter로 iOS/Android 동시 개발
- Firebase Messaging으로 푸시 알림
- 1-탭 빠른 조치 (격리, 중지, 차단)
- 오프라인 모드: 마지막 상태 캐시 사용

---

## 📁 Directory Structure

```
aws-guardian/
├── lambda/guardian/
│   ├── multi_account/
│   │   ├── account_manager.py      (새로 생성)
│   │   └── account_router.py       (새로 생성)
│   ├── responders/
│   │   ├── threat_responder.py     (새로 생성)
│   │   └── response_policy.py      (새로 생성)
│   └── ml/
│       ├── behavioral_analyzer.py  (새로 생성)
│       └── anomaly_predictor.py    (새로 생성)
├── mobile/
│   ├── lib/
│   │   ├── screens/
│   │   │   └── dashboard_screen.dart (새로 생성)
│   │   ├── services/
│   │   │   └── api_service.dart    (새로 생성)
│   │   └── models/
│   │       └── threat.dart         (새로 생성)
│   └── test/
│       └── dashboard_screen_test.dart (새로 생성)
├── tests/
│   ├── backend/
│   │   ├── test_multi_account.py   (새로 생성)
│   │   ├── test_threat_responder.py (새로 생성)
│   │   └── test_behavioral_ml.py   (새로 생성)
│   └── mobile/
│       └── test_dashboard_screen.dart (새로 생성)
└── docs/
    └── SPRINT_71_PROGRESS.md       (추적용)
```

---

## ✅ Success Criteria

| 기준 | 목표 |
|------|------|
| 다중 계정 지원 | 3개 계정 동시 모니터링 |
| 자동 대응 시간 | <1초 (탐지 → 대응) |
| ML 이상 감지 정확도 | 90% (거짓 양성 <5%) |
| 모바일 앱 응답시간 | <500ms |
| 전체 테스트 통과 | 68/68 (100%) |
| 누적 테스트 | 530 tests |

---

## 📅 Estimated Timeline

| Phase | 소요 시간 | 예상 완료 |
|-------|----------|---------|
| 1. 다중 계정 | 3-4일 | 2026-06-02 |
| 2. 실시간 대응 | 3-4일 | 2026-06-06 |
| 3. 고급 ML | 3-4일 | 2026-06-10 |
| 4. 모바일 앱 | 3-4일 | 2026-06-13 |
| **총 소요 시간** | **~14일** | **2026-06-13** |

---

## 🚀 Post-Sprint Activities

### Sprint 71 완료 후
1. 모든 68 tests PASS 확인
2. 누적 530 tests 달성 확인
3. 모바일 앱 iOS/Android 빌드 검증
4. 다중 계정 통합 테스트
5. 성능 벤치마크 (응답시간, 메모리)
6. 보안 감사 (다중 계정 권한, API 인증)

### Sprint 72+ 로드맵
- **Phase 1:** 머신러닝 비용 최적화
- **Phase 2:** 규제 준수 (HIPAA, SOC2)
- **Phase 3:** 글로벌 다중 리전 지원
- **Phase 4:** AI 기반 자동 인시던트 대응

---

## 💡 Technical Highlights

### 다중 계정 아키텍처
```python
# 계정별 역할 가정
assume_role_arn = f"arn:aws:iam::{account_id}:role/GuardianCrossAccountRole"
role_session = assume_role(assume_role_arn)

# 각 계정에서 리소스 조회
resources = get_ec2_instances(role_session)  # 해당 계정의 EC2만 조회
```

### 실시간 대응 정책
```yaml
threat_response_policy:
  CRITICAL:
    action: ISOLATE  # EC2 Stop + SG 수정
    delay: 0s        # 즉시 실행
    notify: CRITICAL # 긴급 알림
  
  HIGH:
    action: BLOCK    # 네트워크 차단
    delay: 5s        # 5초 후 실행 (취소 가능)
    notify: HIGH
  
  MEDIUM:
    action: ALERT    # 알림만
    delay: 30s
    notify: MEDIUM
```

### 동작 기반 이상 감지
```python
# 사용자 정상 행동 프로파일
profile = {
    'typical_api_calls': ['GetUser', 'ListRoles'],
    'typical_time': '9-5 UTC',
    'typical_location': 'US-EAST-1',
    'baseline_failure_rate': 0.02  # 2%
}

# 현재 행동과 비교
current_anomaly_score = compare_behavior(current_action, profile)
# score = 0 (정상) ~ 100 (매우 비정상)
```

---

## 📝 Notes

- **다중 계정**: 계정당 별도의 Lambda 실행 역할 필요 (보안)
- **실시간 대응**: EventBridge로 자동화, DynamoDB로 감사 추적
- **ML 이상**: 초기 1주일은 학습 기간 (정상 패턴 수집)
- **모바일**: Flutter로 iOS/Android 동시 지원 (코드 공유 80%)

---

**Sprint 71 준비 완료** ✅

다음 단계: Phase 1 (다중 계정 지원) 구현 시작
