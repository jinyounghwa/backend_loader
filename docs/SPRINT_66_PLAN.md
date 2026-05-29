# Sprint 66: 사용자 경험 개선 & 고급 기능

**상태**: Planning  
**목표**: 모바일 앱, 실시간 알림, 고급 ML 기능 추가  

---

## 개요

Sprint 66은 AWS Guardian의 **사용자 경험(UX)과 고급 분석 기능**을 강화합니다. 모바일 앱으로 어디서나 감시 가능하게 하고, 실시간 대시보드와 ML 기반 이상 탐지로 더 똑똑한 시스템을 만듭니다.

---

## 단계별 계획

| Phase | 컴포넌트 | 테스트 | 포커스 |
|-------|---------|--------|--------|
| 1 | 실시간 알림 개선 | 15 | WebSocket, 우선순위, 배칭 |
| 2 | 모바일 앱 (iOS/Android) | 12 | 푸시 알림, 간편 제어 |
| 3 | 고급 ML & 이상 탐지 | 18 | Isolation Forest, ARIMA, 추천 |
| 4 | 대시보드 고급화 | 16 | 실시간 차트, 예측, 시뮬레이션 |
| **합계** | **Sprint 66** | **61** | **UX + 고급 기능** |

**누적**: Sprint 65 (122) + Sprint 66 (61) = **183 tests**

---

## Phase 1: 실시간 알림 개선 (15 tests)

### 파일 목록
- `lambda/guardian/notifiers/notification_prioritizer.py` — 알림 우선순위 지정
- `lambda/guardian/notifiers/batch_notifier.py` — 배치 처리
- `lambda/guardian/notifiers/email_reporter.py` — 이메일 요약
- `lambda/guardian/notifiers/slack_notifier.py` — Slack 통합
- `apps/web/src/lib/hooks/useRealtimeNotifications.ts` — WebSocket 훅
- `apps/web/src/components/NotificationCenter.tsx` — 알림 센터 UI
- `tests/backend/test_notification_system.py` — 15개 테스트

### 테스트 케이스
1. `test_notification_priority_classification` — 위협도별 우선순위
2. `test_batch_notifications_by_severity` — 심각도별 배치
3. `test_notification_deduplication` — 중복 제거
4. `test_email_summary_generation` — 이메일 요약
5. `test_slack_webhook_integration` — Slack 연동
6. `test_websocket_real_time_alerts` — 실시간 WebSocket
7. `test_notification_retry_logic` — 재시도 로직
8. `test_notification_history_tracking` — 이력 추적
9. `test_do_not_disturb_schedule` — 방해금지 시간대
10. `test_notification_filter_by_account` — 계정별 필터
11. `test_alert_aggregation` — 알림 통합
12. `test_multi_channel_delivery` — 멀티 채널
13. `test_notification_delivery_confirmation` — 전송 확인
14. `test_rate_limiting` — 레이트 제한
15. `test_notification_analytics` — 분석

### 주요 기능
```
위협 탐지
    ↓
Notification Prioritizer (심각도 분류)
    ├─ CRITICAL → 즉시 (Telegram + Slack)
    ├─ HIGH → 1분 배치 (Telegram + Email)
    ├─ MEDIUM → 5분 배치 (Email)
    └─ LOW → 일일 요약 (Email)
    ↓
Batch Notifier (배치 처리)
    ├─ 중복 제거
    ├─ 레이트 제한
    └─ 채널별 전송
    ↓
WebSocket (실시간 대시보드)
```

---

## Phase 2: 모바일 앱 (12 tests)

### 파일 목록
- `apps/mobile/ios/src/screens/DashboardScreen.swift` — iOS 대시보드
- `apps/mobile/ios/src/screens/SettingsScreen.swift` — iOS 설정
- `apps/mobile/android/src/screens/DashboardScreen.kt` — Android 대시보드
- `apps/mobile/android/src/screens/SettingsScreen.kt` — Android 설정
- `apps/mobile/src/services/api.ts` — 공통 API 클라이언트
- `apps/mobile/src/hooks/useNotifications.ts` — 알림 훅
- `tests/mobile/test_dashboard_screen.swift` — iOS 테스트 (6)
- `tests/mobile/test_dashboard_screen.kt` — Android 테스트 (6)

### 테스트 케이스
**iOS:**
1. `test_dashboard_displays_cost_summary` — 비용 요약 표시
2. `test_threat_alerts_in_list` — 위협 목록
3. `test_push_notification_received` — 푸시 알림
4. `test_manual_refresh` — 새로고침
5. `test_settings_persistence` — 설정 저장
6. `test_offline_mode` — 오프라인 모드

**Android:**
7. `test_material_design_compliance` — Material Design
8. `test_notification_badge` — 알림 배지
9. `test_dark_mode_support` — 다크모드
10. `test_tablet_layout` — 태블릿 레이아웃
11. `test_permission_handling` — 권한 처리
12. `test_app_shortcuts` — 앱 단축키

### 아키텍처
```
AWS Guardian Backend
    ↓
REST API + WebSocket
    ↓
┌─────────────────────┐
│  iOS App (Swift)    │
│  - SwiftUI UI       │
│  - URLSession API   │
│  - UserNotifications│
└─────────────────────┘
┌─────────────────────┐
│ Android App (Kotlin)│
│  - Jetpack Compose  │
│  - Retrofit API     │
│  - Firebase Cloud   │
└─────────────────────┘
```

---

## Phase 3: 고급 ML & 이상 탐지 (18 tests)

### 파일 목록
- `lambda/guardian/ml/isolation_forest.py` — Isolation Forest 엔진
- `lambda/guardian/ml/arima_forecaster.py` — ARIMA 시계열
- `lambda/guardian/ml/anomaly_detector_v2.py` — 개선된 이상 탐지
- `lambda/guardian/ml/recommendation_engine.py` — 추천 엔진
- `lambda/guardian/ml/pattern_learner.py` — 패턴 학습
- `tests/backend/test_ml_anomaly_detection.py` — 18개 테스트

### 테스트 케이스
1. `test_isolation_forest_initialization` — 초기화
2. `test_isolation_forest_anomaly_detection` — 이상 탐지
3. `test_forest_model_persistence` — 모델 저장/로드
4. `test_arima_forecast_generation` — ARIMA 예측
5. `test_seasonal_pattern_detection` — 계절 패턴
6. `test_forecast_confidence_interval` — 신뢰도 구간
7. `test_anomaly_detector_v2_accuracy` — 정확도
8. `test_anomaly_threshold_adaptation` — 임계값 학습
9. `test_multivariate_anomaly_detection` — 다변량 탐지
10. `test_recommendation_cost_optimization` — 비용 최적화 추천
11. `test_recommendation_security_hardening` — 보안 강화 추천
12. `test_recommendation_ranking` — 추천 순위 지정
13. `test_pattern_learner_baseline` — 기준선 학습
14. `test_pattern_learner_drift_detection` — 드리프트 탐지
15. `test_daily_pattern_extraction` — 일일 패턴
16. `test_weekly_pattern_extraction` — 주간 패턴
17. `test_ml_model_retraining` — 모델 재학습
18. `test_ml_performance_metrics` — 성능 메트릭

### 알고리즘

#### Isolation Forest (비정상 탐지)
```
특징:
- 트리 기반 이상 탐지
- 저차원 특징에서 이상 발견
- O(n log n) 복잡도

적용 대상:
- EC2 CPU 사용률
- 네트워크 대역폭
- API 응답 시간
```

#### ARIMA (시계열 예측)
```
특징:
- 자동 회귀 통합 이동평균
- 계절 패턴 지원
- 신뢰도 구간 제공

적용 대상:
- 일일 비용 예측
- 트래픽 예측
- 리소스 사용 예측
```

#### 추천 엔진
```
입력:
- 현재 비용 / 위협
- 과거 데이터
- 사용자 선호도

출력:
- 비용 절감 추천
- 보안 강화 추천
- 성능 개선 추천

예시:
"RI 구매로 월 $150 절감 가능"
"S3 Intelligent-Tiering 활성화 권장"
"CloudFront 캐싱으로 대역폭 30% 감소"
```

---

## Phase 4: 대시보드 고급화 (16 tests)

### 파일 목록
- `apps/web/src/components/AdvancedCharts.tsx` — 고급 차트
- `apps/web/src/components/AnomalyExplainer.tsx` — 이상 설명
- `apps/web/src/components/ForecastingDashboard.tsx` — 예측 대시보드
- `apps/web/src/components/RecommendationPanel.tsx` — 추천 패널
- `apps/web/src/components/SimulationEngine.tsx` — 시뮬레이션
- `apps/web/src/lib/hooks/useForecast.ts` — 예측 훅
- `tests/frontend/test_advanced_dashboard.tsx` — 16개 테스트

### 테스트 케이스
1. `test_cost_trend_chart_rendering` — 비용 추세 차트
2. `test_forecast_visualization` — 예측 시각화
3. `test_anomaly_explanation_panel` — 이상 설명
4. `test_what_if_simulation` — What-If 시뮬레이션
5. `test_recommendation_acceptance` — 추천 수용
6. `test_cost_breakdown_by_service` — 서비스별 비용
7. `test_cost_breakdown_by_account` — 계정별 비용
8. `test_threat_timeline` — 위협 타임라인
9. `test_remediation_impact_chart` — 대응 영향도
10. `test_export_pdf_report` — PDF 내보내기
11. `test_custom_date_range` — 커스텀 기간
12. `test_interactive_filtering` — 대화형 필터
13. `test_real_time_update_websocket` — 실시간 업데이트
14. `test_performance_metrics_panel` — 성능 메트릭
15. `test_compliance_score_calculation` — 규정 준수 점수
16. `test_dashboard_responsive_design` — 반응형 디자인

### 주요 UI 컴포넌트
```
┌─────────────────────────────────────────┐
│        AWS Guardian Dashboard            │
├─────────────────────────────────────────┤
│                                         │
│  [Cost Forecast] [Threats] [Actions]   │
│                                         │
│  ┌─────────────┬──────────────┐         │
│  │Cost Trend   │Anomaly Info  │         │
│  │(Line Chart) │(Explanation) │         │
│  ├─────────────┼──────────────┤         │
│  │Forecast     │Recommend     │         │
│  │(Area Chart) │(Suggestions) │         │
│  ├─────────────┼──────────────┤         │
│  │What-If      │Simulation    │         │
│  │(Sliders)    │(Results)     │         │
│  └─────────────┴──────────────┘         │
│                                         │
│  [Export PDF] [Share] [Settings]       │
└─────────────────────────────────────────┘
```

---

## 구현 전략

### Week 1: Phase 1 (실시간 알림)
- Notification Prioritizer, Batch Notifier 구현
- WebSocket 실시간 업데이트
- 15개 테스트 작성

### Week 2: Phase 2 (모바일 앱)
- iOS SwiftUI 앱 (Dashboard, Settings)
- Android Jetpack Compose 앱
- 12개 테스트 작성

### Week 3: Phase 3 (고급 ML)
- Isolation Forest 엔진
- ARIMA 시계열 예측
- 추천 엔진
- 18개 테스트 작성

### Week 4: Phase 4 (고급 대시보드)
- 고급 차트 및 시각화
- What-If 시뮬레이션
- PDF 리포트 내보내기
- 16개 테스트 작성

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| **Backend** | Python 3.12, FastAPI, asyncio |
| **ML** | scikit-learn, statsmodels, pandas |
| **Frontend** | Next.js, React 19, TailwindCSS |
| **Mobile** | Swift (iOS), Kotlin (Android) |
| **실시간** | WebSocket, Server-Sent Events |
| **차트** | Recharts, Plotly |
| **알림** | Telegram, Slack, Email, Push |

---

## 성공 지표

| 지표 | 목표 | 방법 |
|------|------|------|
| 모든 테스트 PASS | 61 | pytest, iOS tests, Android tests |
| 모바일 앱 출시 | iOS + Android | App Store + Play Store |
| ML 정확도 | > 92% | Precision, Recall, F1 Score |
| 대시보드 성능 | < 200ms | Lighthouse, Web Vitals |
| 사용자 만족도 | > 4.5/5 | 스토어 리뷰 |

---

## 의존성

- Sprint 65 완료 (실제 AWS API)
- boto3, botocore, scikit-learn, statsmodels
- React Native (모바일 공통 코드)
- Firebase (푸시 알림)

---

## 위험 관리

| 위험 | 대응 |
|------|------|
| 모바일 앱 승인 지연 | 테스트플라이트/베타 먼저 출시 |
| ML 모델 정확도 낮음 | Hybrid 접근 (규칙 + ML) |
| WebSocket 안정성 | 폴백 메커니즘 (polling) |
| 대시보드 성능 | 데이터 캐싱, 집계 |

---

## 다음 단계 (Sprint 67)

1. **인프라 코드화**: Terraform, CloudFormation
2. **CI/CD 파이프라인**: GitHub Actions, CodePipeline
3. **멀티 리전**: 전 세계 배포
4. **고급 보안**: 엔드투엔드 암호화, RBAC

---

## 결론

Sprint 66은 AWS Guardian을 **프로덕션급 SaaS 플랫폼**으로 진화시킵니다. 모바일 앱으로 언제 어디서나 감시 가능하고, 고급 ML로 더 똑똑하게 자동화하며, 아름다운 대시보드로 한눈에 이해할 수 있도록 만듭니다.

---

**목표**: 누적 183 테스트, 프로덕션 SaaS 레벨의 완성도 달성

