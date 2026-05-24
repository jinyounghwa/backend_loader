# Sprint 43: Real-time CloudTrail & ML Anomaly Detection

> AWS Guardian의 실시간 위협 탐지 및 머신러닝 기반 이상 탐지 고도화

---

## 슬로건

**"실시간으로 탐지하고, AI가 학습해서 더 똑똑하게 대응한다"**

---

## 현황 분석

### 완료된 기능 (Sprint 40-42)
- ✅ 단일/멀티 계정 모니터링
- ✅ EC2, S3, EBS, IAM 감시
- ✅ CloudTrail 배치 분석
- ✅ 통계 기반 이상 탐지 (2-sigma)
- ✅ 자동 대응 (EC2 중지, IAM 키 비활성화)
- ✅ 규정 준수 모니터링
- ✅ 대시보드 및 예측 분석

### 누적 테스트
- 이전 스프린트: 413 tests
- Sprint 40: 44 tests
- Sprint 41: 44 tests
- Sprint 42: 47 tests
- **합계: 460+ tests PASS**

### Sprint 43의 목표

| 항목 | 내용 |
|------|------|
| **주요 기능** | 실시간 위협 탐지 + ML 이상 탐지 |
| **테스트 수** | 44 tests (4 Phase × 11 tests) |
| **누적 테스트** | 500+ tests PASS |
| **구현 파일** | 8개 신규 모듈 + 4개 테스트 |
| **배포 대상** | AWS Lambda (SQS + DynamoDB Streams) |

---

## 4단계 구현 계획

### Phase 1: Real-time CloudTrail Integration (12 tests)

**목표:** CloudTrail 이벤트를 실시간으로 처리

**구현 파일:**
```
lambda/guardian/handlers/cloudtrail_stream_handler.py
  └─ CloudTrailStreamHandler 클래스
     ├─ process_cloudtrail_stream(records)
     ├─ extract_api_calls(event)
     ├─ filter_by_risk_level(calls)
     ├─ correlate_suspicious_events(events)
     └─ trigger_immediate_alert(threat)

lambda/guardian/processors/event_normalizer.py
  └─ EventNormalizer 클래스
     ├─ normalize_cloudtrail_event(event)
     ├─ extract_principal(event)
     ├─ get_api_parameters(event)
     └─ calculate_event_risk_score()

tests/backend/test_cloudtrail_stream.py (12 tests)
```

**기술 스택:**
- SQS로 CloudTrail 이벤트 수신
- DynamoDB Streams로 트리거
- 즉시 위협 탐지 및 대응

**테스트 그룹:**
- Group 1: 실시간 스트림 처리 (3 tests)
- Group 2: 이벤트 정규화 (3 tests)
- Group 3: 위협 상관관계 (3 tests)
- Group 4: 즉시 경고 발송 (3 tests)

---

### Phase 2: ML-Based Anomaly Detection (12 tests)

**목표:** 머신러닝으로 패턴 기반 이상 탐지

**구현 파일:**
```
lambda/guardian/models/isolation_forest_detector.py
  └─ IsolationForestDetector 클래스
     ├─ train_model(historical_data)
     ├─ predict_anomalies(new_data)
     ├─ calculate_anomaly_score(instance)
     ├─ detect_novel_patterns()
     └─ auto_retrain_schedule()

lambda/guardian/models/time_series_forecaster.py
  └─ TimeSeriesForecaster 클래스
     ├─ fit_arima_model(timeseries_data)
     ├─ forecast_with_confidence(steps)
     ├─ detect_seasonality(data)
     └─ get_forecast_accuracy()

tests/backend/test_ml_anomaly_detection.py (12 tests)
```

**기술 스택:**
- scikit-learn (Isolation Forest)
- statsmodels (ARIMA)
- 자동 모델 재학습 (주간)

**테스트 그룹:**
- Group 1: 모델 학습 및 예측 (3 tests)
- Group 2: 이상 점수 계산 (3 tests)
- Group 3: 시간별 계절성 감지 (3 tests)
- Group 4: 모델 재학습 및 성능 검증 (3 tests)

---

### Phase 3: Slack/Teams Integration (10 tests)

**목표:** Slack과 Microsoft Teams 동시 알림

**구현 파일:**
```
lambda/guardian/responders/slack_responder.py
  └─ SlackResponder 클래스
     ├─ send_alert(alert, channel)
     ├─ create_alert_block(threat)
     ├─ add_buttons(message, actions)
     └─ handle_interactive_action()

lambda/guardian/responders/teams_responder.py
  └─ TeamsResponder 클래스
     ├─ send_alert(alert)
     ├─ create_adaptive_card(threat)
     ├─ add_action_buttons(card)
     └─ handle_card_action()

lambda/guardian/responders/notification_orchestrator.py
  └─ NotificationOrchestrator 클래스
     ├─ send_to_all_channels(alert)
     ├─ throttle_notifications()
     └─ track_notification_delivery()

tests/backend/test_slack_teams_integration.py (10 tests)
```

**기술 스택:**
- Slack Bot API
- Microsoft Teams Webhooks
- 알림 중복 제거 및 스로틀링

**테스트 그룹:**
- Group 1: Slack 메시지 포맷 (3 tests)
- Group 2: Teams 적응형 카드 (3 tests)
- Group 3: 인터랙티브 버튼/액션 (2 tests)
- Group 4: 다중 채널 배포 (2 tests)

---

### Phase 4: Cost Optimization Recommendations (10 tests)

**목표:** ROI 기반 비용 최적화 추천

**구현 파일:**
```
lambda/guardian/optimizers/cost_optimizer_engine.py
  └─ CostOptimizerEngine 클래스
     ├─ analyze_resource_utilization()
     ├─ calculate_roi_for_optimization()
     ├─ generate_rightsizing_recommendations()
     ├─ estimate_annual_savings()
     └─ track_optimization_impact()

lambda/guardian/calculators/roi_calculator.py
  └─ ROICalculator 클래스
     ├─ calculate_implementation_cost()
     ├─ calculate_annual_savings()
     ├─ calculate_payback_period()
     └─ prioritize_by_roi()

tests/backend/test_cost_optimization.py (10 tests)
```

**기술 스택:**
- CloudWatch 메트릭 분석
- Reserved Instance 계산
- Spot Instance 최적화

**테스트 그룹:**
- Group 1: 리소스 사용률 분석 (3 tests)
- Group 2: ROI 계산 (3 tests)
- Group 3: 최적화 권장사항 (2 tests)
- Group 4: 비용 절감 추적 (2 tests)

---

## 아키텍처 다이어그램

```
Sprint 43 System Architecture

┌─────────────────────────────────────────────────────────────┐
│                    AWS Guardian (Sprint 43)                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Real-time CloudTrail Processing (Phase 1)          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │CloudTrail│  │SQS/Streams│  │Event Normalizer  │   │   │
│  │  │Events   │→ │  Queue    │→ │& Risk Scoring    │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │                      ↓                                 │   │
│  │         Immediate Threat Detection & Alert            │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ML-Based Anomaly Detection (Phase 2)               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Isolation │  │Time Series│  │Pattern Learning  │   │   │
│  │  │Forest    │  │ARIMA      │  │& Auto-Retrain    │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  • Novel Attack Detection                             │   │
│  │  • Seasonality-Aware Forecasting                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Multi-Channel Notification (Phase 3)                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Telegram │  │Slack Bot │  │Teams Webhooks    │   │   │
│  │  │Alerts   │  │Messages  │  │Adaptive Cards    │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  • Notification Deduplication                         │   │
│  │  • Interactive Actions & Buttons                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Cost Optimization Engine (Phase 4)                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Resource  │  │ROI        │  │Savings Impact    │   │   │
│  │  │Analyzer  │  │Calculator │  │Tracker           │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  • Right-Sizing Recommendations                       │   │
│  │  • Reserved Instance Optimization                     │   │
│  │  • Spot Instance Analysis                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 데이터 흐름

```
CloudTrail Events (Real-time)
    ↓
SQS → DynamoDB Streams
    ↓
┌─────────────────────┐
│ Event Normalizer    │
│ • Extract API call  │
│ • Score risk level  │
│ • Correlate events  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Anomaly Detection   │
│ • 2-sigma (fast)    │
│ • Isolation Forest  │
│ • ARIMA forecast    │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Decision Engine     │
│ • Risk assessment   │
│ • Confidence check  │
│ • Priority ranking  │
└─────────────────────┘
    ↓
┌─────────────────────────────┐
│ Multi-Channel Notification  │
│ • Telegram Bot              │
│ • Slack (with buttons)      │
│ • Teams (adaptive card)     │
│ • Notification dedup        │
└─────────────────────────────┘
    ↓
┌─────────────────────┐
│ Remediation Engine  │
│ • Auto-action       │
│ • Manual approval   │
│ • Impact tracking   │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Cost Optimization   │
│ • ROI calculation   │
│ • Savings tracking  │
│ • Recommendations   │
└─────────────────────┘
```

---

## 구현 순서 및 테스트

| Phase | 단계 | 테스트 수 | 누적 |
|-------|------|---------|------|
| 1 | Real-time CloudTrail | 12 | 12 |
| 2 | ML Anomaly Detection | 12 | 24 |
| 3 | Slack/Teams Integration | 10 | 34 |
| 4 | Cost Optimization | 10 | 44 |
| **전체** | Sprint 43 | **44** | **500+** |

---

## 주요 설계 결정

### 1. 실시간 CloudTrail 처리 (SQS + Streams)
- **선택:** SQS 큐 + DynamoDB Streams 트리거
- **장점:** 이벤트 손실 없음, 순서 보장, 확장성 우수
- **구현:** Lambda → SQS → Lambda 파이프라인

### 2. Isolation Forest 기반 ML 탐지
- **선택:** scikit-learn Isolation Forest (비감독학습)
- **장점:** 라벨링 불필요, 이상 점수 계산 가능, 빠른 학습
- **구현:** 주간 자동 재학습, 성능 메트릭 추적

### 3. Slack & Teams 이중화
- **선택:** 두 플랫폼 동시 지원
- **장점:** 팀 선호도에 맞춤, 피드백 수집 용이
- **구현:** 공통 데이터 모델 → 플랫폼별 변환

### 4. ROI 기반 최적화 우선순위
- **선택:** 비용 절감을 절감 금액이 아닌 ROI로 평가
- **장점:** 구현 난도와 효과를 동시에 고려
- **구현:** (연간 절감액 - 구현비용) / 구현비용

---

## 성공 지표

| 지표 | 목표 |
|------|------|
| 실시간 처리 지연 | <1초 |
| ML 모델 정확도 | >90% |
| 이상 탐지 오탐 | <5% |
| Slack/Teams 메시지 성공률 | >99% |
| 비용 최적화 ROI | >200% |

---

## 다음 단계 (Sprint 44+)

**향후 개선:**
1. 자동 티켓 생성 (Jira/ServiceNow)
2. 커스텀 대응 워크플로우 (사용자 정의)
3. 다중 클라우드 지원 (GCP, Azure)
4. 머신러닝 모델 엣지 배포
5. GraphQL API 제공
6. 웹 UI 대시보드 개선
7. 보험 통합 (위험도 기반 보험료)
8. SOAR 플랫폼 통합

---

## 기술 스택 (Sprint 43)

| 레이어 | 기술 |
|--------|------|
| 언어 | Python 3.12 |
| 런타임 | AWS Lambda |
| 실시간 처리 | SQS + DynamoDB Streams |
| ML 프레임워크 | scikit-learn, statsmodels |
| 메시징 | Slack API, Teams Webhooks |
| 저장소 | DynamoDB + S3 |
| 테스트 | pytest (44 tests) |

---

## 체크리스트

**Phase 1: Real-time CloudTrail**
- [ ] CloudTrailStreamHandler 구현
- [ ] EventNormalizer 구현
- [ ] SQS 이벤트 처리
- [ ] 12개 테스트 PASS

**Phase 2: ML Anomaly Detection**
- [ ] IsolationForestDetector 구현
- [ ] TimeSeriesForecaster 구현
- [ ] 자동 재학습 스케줄
- [ ] 12개 테스트 PASS

**Phase 3: Slack/Teams Integration**
- [ ] SlackResponder 구현
- [ ] TeamsResponder 구현
- [ ] NotificationOrchestrator 구현
- [ ] 10개 테스트 PASS

**Phase 4: Cost Optimization**
- [ ] CostOptimizerEngine 구현
- [ ] ROICalculator 구현
- [ ] 최적화 권장사항 생성
- [ ] 10개 테스트 PASS

**최종:**
- [ ] 누적 44개 테스트 모두 PASS
- [ ] 전체 테스트: 500+ PASS
- [ ] Git 커밋: "feat: Sprint 43 - Real-time CloudTrail & ML Anomaly Detection"

---

**Sprint 43 계획 완료** ✅
