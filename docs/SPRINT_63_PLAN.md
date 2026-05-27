# Sprint 63: Production Persistence & Advanced Analytics

## Context

**현황:**
- Sprint 54-61 완료: 182 테스트 PASS
- Sprint 62 완료: 51 테스트 PASS (CloudTrail + Statistical Anomaly + Adaptive Response + Dashboard UI)
- 누적 테스트: 233 테스트 PASS
- 아키텍처: CloudTrail → Anomaly Detection → Adaptive Response → Real-time Dashboard

**핵심 문제:**
- **메모리 저장소**: 모든 데이터가 메모리에 저장되어 프로세스 재시작 시 손실
- **데이터 지속성 부족**: CloudTrail 이벤트, 결정, 피드백이 보관되지 않음
- **분석 기능 미흡**: 시계열 분석, 비용 예측 없음
- **대시보드 UI 미구현**: 웹 기반 실시간 시각화 필요
- **고급 오케스트레이션**: 다단계 워크플로우, 롤백 시퀀스 미지원

**기존 인프라 (재활용):**
```
✅ CloudTrailCollector - CloudTrail 이벤트 수집 구현됨
✅ StatisticalAnomalyDetector - Z-score 이상 탐지 구현됨
✅ AdaptiveAutoResponse - 적응형 자동 대응 구현됨
✅ DashboardUI - 백엔드 대시보드 서비스 구현됨
❌ PersistenceLayer - DynamoDB/S3 저장소 없음 (신규)
❌ TimeSeriesAnalytics - 시계열 분석 없음 (신규)
❌ CostAnalytics - 비용 분석 및 예측 없음 (신규)
❌ DashboardReactUI - React/Next.js 웹 UI 없음 (신규)
```

**목표:**
Sprint 63은 **프로덕션 지속성 및 고급 분석**을 구현합니다:
1. **Phase 1**: 지속성 계층 (DynamoDB, S3 저장소)
2. **Phase 2**: 시계열 분석 (트렌드, 패턴 감지)
3. **Phase 3**: 비용 분석 (영향 분석, 예측)
4. **Phase 4**: 웹 대시보드 UI (React/Next.js)

---

## Phase 1: Persistence Layer

### 목표
DynamoDB와 S3를 활용한 데이터 지속성 구현

### 구현 파일

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/storage/event_store.py` | 신규: CloudTrail 이벤트 DynamoDB 저장 |
| `lambda/guardian/storage/decision_store.py` | 신규: 대응 결정 DynamoDB 저장 |
| `lambda/guardian/storage/feedback_store.py` | 신규: 피드백 DynamoDB 저장 |
| `lambda/guardian/storage/archive_store.py` | 신규: 오래된 데이터 S3 아카이브 |
| `sam/template.yaml` | 수정: DynamoDB 테이블 정의 (EventsTable, DecisionsTable, FeedbackTable) |
| `tests/backend/test_persistence_layer.py` | 신규: 지속성 계층 테스트 (10개) |

### 핵심 클래스

**EventStore** - CloudTrail 이벤트 저장
```python
def store_event(event, source) -> event_id
def get_event(event_id) -> event
def list_events(filters, limit=100) -> events
def archive_old_events(days=30) -> archived_count
```

**DecisionStore** - 대응 결정 저장
```python
def store_decision(decision) -> decision_id
def get_decision(decision_id) -> decision
def list_decisions(threat_id) -> decisions
def get_decision_history(days=7) -> decisions
```

**FeedbackStore** - 피드백 저장
```python
def store_feedback(decision_id, feedback) -> feedback_id
def get_feedback(feedback_id) -> feedback
def list_feedback_for_decision(decision_id) -> feedback
def get_recent_feedback(days=7) -> feedback
```

**ArchiveStore** - S3 아카이브
```python
def archive_events(events) -> archive_id
def archive_decisions(decisions) -> archive_id
def restore_from_archive(archive_id) -> data
def cleanup_old_archives(days=90) -> deleted_count
```

### DynamoDB 테이블 설계

**EventsTable**
- PK: event_id
- SK: timestamp
- GSI: source-timestamp (CloudTrail 소스별 조회)
- TTL: 90일

**DecisionsTable**
- PK: decision_id
- SK: timestamp
- GSI: threat_id-timestamp (위협별 결정 조회)
- GSI: action-timestamp (액션별 조회)
- TTL: 365일

**FeedbackTable**
- PK: feedback_id
- SK: timestamp
- GSI: decision_id-timestamp (결정별 피드백)
- GSI: effectiveness-timestamp (효과성별)
- TTL: 365일

### 테스트 케이스 (10개)

1. `test_store_event`: 이벤트 저장
2. `test_get_event`: 이벤트 조회
3. `test_store_decision`: 결정 저장
4. `test_store_feedback`: 피드백 저장
5. `test_archive_events`: 이벤트 아카이브
6. `test_list_events_with_filters`: 필터링 조회
7. `test_decision_history`: 결정 이력 조회
8. `test_feedback_for_decision`: 결정별 피드백 조회
9. `test_archive_cleanup`: 오래된 아카이브 정리
10. `test_restore_from_archive`: 아카이브에서 복원

---

## Phase 2: Time-Series Analytics

### 목표
이벤트 시계열 분석으로 트렌드 및 패턴 감지

### 구현 파일

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/analytics/timeseries.py` | 신규: 시계열 데이터 분석 |
| `lambda/guardian/analytics/trend_detector.py` | 신규: 트렌드 감지 |
| `lambda/guardian/analytics/pattern_detector.py` | 신규: 패턴 인식 |
| `tests/backend/test_timeseries_analytics.py` | 신규: 시계열 분석 테스트 (9개) |

### 핵심 클래스

**TimeSeriesAnalytics** - 시계열 분석
```python
def aggregate_events(events, window='1h') -> timeseries
def calculate_moving_average(data, window=7) -> average
def detect_seasonal_pattern(data) -> pattern
def forecast_trend(data, periods=24) -> forecast
```

**TrendDetector** - 트렌드 감지
```python
def detect_uptrend(data) -> (is_uptrend, confidence)
def detect_downtrend(data) -> (is_downtrend, confidence)
def get_trend_strength(data) -> strength (0-1)
def predict_peak_time(data) -> datetime
```

**PatternDetector** - 패턴 인식
```python
def find_recurring_patterns(data) -> patterns
def match_pattern_to_known(data) -> known_pattern
def extract_pattern_features(data) -> features
def predict_next_occurrence(pattern) -> datetime
```

### 분석 알고리즘

**Moving Average (이동 평균)**
- 7-day, 14-day, 30-day 이동 평균
- 단기/중기/장기 트렌드 파악

**Seasonal Decomposition (계절 분해)**
- 트렌드, 계절성, 잔여 성분 분리
- 주간/월간/계절별 패턴 감지

**Exponential Smoothing (지수 평활)**
- 최근 데이터에 더 높은 가중치
- 급변하는 트렌드 빠른 반응

### 테스트 케이스 (9개)

1. `test_aggregate_events_by_hour`: 시간별 집계
2. `test_moving_average_calculation`: 이동 평균 계산
3. `test_detect_uptrend`: 상향 트렌드 감지
4. `test_detect_downtrend`: 하향 트렌드 감지
5. `test_seasonal_pattern_detection`: 계절 패턴 감지
6. `test_recurring_pattern_finding`: 반복 패턴 발견
7. `test_trend_strength_calculation`: 트렌드 강도 계산
8. `test_forecast_trend`: 트렌드 예측
9. `test_pattern_matching`: 패턴 매칭

---

## Phase 3: Cost Analytics

### 목표
AWS 리소스 비용 분석 및 자동 대응 영향 예측

### 구현 파일

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/analytics/cost_analyzer.py` | 신규: 비용 분석 엔진 |
| `lambda/guardian/analytics/cost_forecaster.py` | 신규: 비용 예측 모델 |
| `tests/backend/test_cost_analytics.py` | 신규: 비용 분석 테스트 (8개) |

### 핵심 클래스

**CostAnalyzer** - 비용 분석
```python
def calculate_hourly_cost(resources) -> cost
def estimate_daily_cost(hourly_trend) -> cost
def analyze_cost_by_service(costs) -> breakdown
def identify_cost_anomalies(daily_costs) -> anomalies
def calculate_cost_impact(action_type) -> cost_delta
```

**CostForecaster** - 비용 예측
```python
def forecast_daily_cost(historical, days=30) -> forecast
def forecast_monthly_cost(daily_forecast) -> forecast
def predict_cost_after_action(action) -> projected_cost
def estimate_savings_potential(actions) -> savings
```

### 비용 모델

**리소스별 가격**
- EC2: $0.0116/hour (t3.micro)
- S3: $0.023/GB/month
- RDS: $0.17/hour
- NAT Gateway: $0.045/hour

**자동 대응 비용**
- EC2 Stop: $0 (중단만)
- Security Group 수정: $0
- S3 Block Public: $0
- IAM Key 비활성화: $0
- 긴급 종료: 리소스 비용 x 1개월

### 테스트 케이스 (8개)

1. `test_calculate_hourly_cost`: 시간별 비용 계산
2. `test_estimate_daily_cost`: 일별 비용 추정
3. `test_cost_by_service_breakdown`: 서비스별 비용 분해
4. `test_identify_cost_anomalies`: 비용 이상 감지
5. `test_calculate_action_cost_impact`: 액션 비용 영향도
6. `test_forecast_daily_cost`: 일별 비용 예측
7. `test_forecast_monthly_cost`: 월별 비용 예측
8. `test_estimate_savings_potential`: 절감 가능성 추정

---

## Phase 4: Dashboard React UI

### 목표
React/Next.js 기반 실시간 웹 대시보드 구현

### 구현 파일

| 파일 | 수정 내용 |
|------|---------|
| `apps/web/src/app/guardian/dashboard/page.tsx` | 신규: 대시보드 메인 페이지 |
| `apps/web/src/components/Guardian/ThreatMap.tsx` | 신규: 위협 지도 컴포넌트 |
| `apps/web/src/components/Guardian/MetricsDashboard.tsx` | 신규: 메트릭 대시보드 |
| `apps/web/src/components/Guardian/ResponseHistory.tsx` | 신규: 대응 이력 |
| `apps/web/src/components/Guardian/CostChart.tsx` | 신규: 비용 차트 |
| `apps/web/src/lib/hooks/useGuardianData.ts` | 신규: 데이터 페칭 훅 |
| `apps/web/src/lib/guardian-api-client.ts` | 신규: Guardian API 클라이언트 |
| `tests/frontend/test_dashboard.tsx` | 신규: UI 테스트 (7개) |

### 핵심 컴포넌트

**ThreatMap** - 실시간 위협 지도
- Leaflet 지도 라이브러리 사용
- AWS 리전별 위협 표시
- 심각도별 색상 구분
- 클릭시 상세 정보 표시

**MetricsDashboard** - 메트릭 대시보드
- 전체 시스템 상태 (HEALTHY/DEGRADED/FAILED)
- 성공률, 평균 지연시간
- 활성 위협 수, 대응 완료 수
- 실시간 업데이트 (5초)

**ResponseHistory** - 대응 이력 타임라인
- 최근 대응 목록 (최대 50개)
- 액션별 효과성 스코어
- 실행 시간 표시
- 필터링 기능 (액션, 상태, 시간)

**CostChart** - 비용 차트
- 시간별/일별 비용 트렌드
- 예측 비용 표시
- 비용 이상 강조
- 절감 기회 표시

### 기술 스택

| 항목 | 기술 |
|------|------|
| 프레임워크 | React 19 + Next.js 16 |
| 상태 관리 | SWR (데이터 페칭) |
| 차트 | Chart.js / Recharts |
| 지도 | Leaflet / react-leaflet |
| UI | Tailwind CSS v4 |
| 아이콘 | Lucide React |
| 타입스크립트 | TypeScript 5+ |

### 테스트 케이스 (7개)

1. `test_threat_map_rendering`: 위협 지도 렌더링
2. `test_metrics_dashboard_display`: 메트릭 대시보드 표시
3. `test_real_time_updates`: 실시간 데이터 업데이트
4. `test_response_history_filter`: 대응 이력 필터링
5. `test_cost_chart_rendering`: 비용 차트 표시
6. `test_dashboard_responsive_layout`: 반응형 레이아웃
7. `test_error_state_handling`: 에러 상태 처리

---

## 구현 순서 및 테스트

| Phase | 단계 | 테스트 수 | 누적 |
|-------|------|---------|------|
| 1 | 지속성 계층 | 10 | 10 |
| 2 | 시계열 분석 | 9 | 19 |
| 3 | 비용 분석 | 8 | 27 |
| 4 | 웹 UI | 7 | 34 |
| **전체** | Sprint 63 | **34** | **267** |

---

## 기술 스택 (Sprint 63)

| 레이어 | 기술 |
|--------|------|
| 데이터베이스 | DynamoDB (이벤트, 결정, 피드백), S3 (아카이브) |
| 분석 | NumPy/SciPy (시계열), Pandas (데이터 처리) |
| API | Lambda (REST), API Gateway |
| 웹 프론트엔드 | React 19, Next.js 16, TypeScript |
| 차트/지도 | Recharts, Leaflet |
| 스타일링 | Tailwind CSS v4, Lucide React |
| 테스트 | pytest (백엔드 27개), Jest (프론트엔드 7개) |

---

## 아키텍처 흐름 (지속성 계층 추가)

```
CloudTrail Events
    ↓
CloudTrailCollector
    ↓ (저장)
EventStore (DynamoDB)
    ↓
StatisticalAnomalyDetector
    ↓ (저장)
DecisionStore (DynamoDB) + AdaptiveAutoResponse
    ↓ (피드백 저장)
FeedbackStore (DynamoDB)
    ↓
TimeSeriesAnalytics + CostAnalytics
    ↓
웹 대시보드 (React/Next.js)
    ├─ ThreatMap (위협 시각화)
    ├─ MetricsDashboard (시스템 상태)
    ├─ ResponseHistory (대응 이력)
    └─ CostChart (비용 분석)

아카이브 계층
    ↓
ArchiveStore (S3) - 90일 이상 데이터 아카이브
```

---

## 주요 설계 결정

**1. DynamoDB 저장 구조**
- 이벤트: 90일 TTL (최근 이벤트 빠른 조회)
- 결정/피드백: 365일 TTL (장기 학습)
- GSI로 다양한 조회 패턴 지원

**2. 시계열 분석**
- 이동 평균: 단기/중기/장기 트렌드
- 계절 분해: 주기적 패턴 감지
- 지수 평활: 급변 대응

**3. 비용 모델**
- AWS 실제 가격 기반
- 자동 대응의 경제적 영향 분석
- 절감 기회 자동 제안

**4. 웹 UI 아키텍처**
- SWR로 자동 갱신 (5-10초)
- 반응형 디자인 (모바일/태블릿/데스크톱)
- 접근성 고려 (ARIA labels)

---

## 검증 체크리스트

**Phase 1: 지속성 계층**
- [ ] DynamoDB 테이블 생성
- [ ] EventStore, DecisionStore, FeedbackStore 구현
- [ ] S3 아카이브 구현
- [ ] 10개 테스트 PASS

**Phase 2: 시계열 분석**
- [ ] 이동 평균 알고리즘 구현
- [ ] 트렌드 감지 로직 구현
- [ ] 패턴 인식 구현
- [ ] 9개 테스트 PASS

**Phase 3: 비용 분석**
- [ ] 비용 계산 엔진 구현
- [ ] 비용 예측 모델 구현
- [ ] 영향도 분석 구현
- [ ] 8개 테스트 PASS

**Phase 4: 웹 대시보드**
- [ ] ThreatMap 컴포넌트 구현
- [ ] MetricsDashboard 컴포넌트 구현
- [ ] ResponseHistory 컴포넌트 구현
- [ ] CostChart 컴포넌트 구현
- [ ] 7개 테스트 PASS

**최종:**
- [ ] 누적 34개 테스트 모두 PASS
- [ ] 전체 테스트: 233 (Sprint 54-62) + 34 (Sprint 63) = 267 PASS
- [ ] Git 커밋: "feat: Sprint 63 - Production Persistence & Advanced Analytics"

---

## 다음 단계 (Sprint 64+)

**향후 개선:**
- 머신러닝 기반 비용 예측 (XGBoost, LSTM)
- 모바일 앱 (React Native)
- Slack/Teams 통합 알림
- 자동화된 보고서 생성
- 규정 준수 모니터링 (SOC 2, HIPAA)
- 다중 AWS 계정 지원

---

**Date**: May 27, 2026  
**Status**: 📋 PLAN READY FOR SPRINT 63
