---
module: analytics-ml
path: 06-Analytics-ML
keywords: analytics, ml, cost-forecast, anomaly-detection, arima, ensemble
---

# Analytics & ML — 분석 및 머신러닝

#module-analytics #arch-serverless

## 목적

비용 예측, 이상 탐지, 패턴 인식을 통해 Guardian의 탐지 정확도를 높이고 사전 대응을 가능하게 합니다.

## 주요 디렉토리

```
lambda/guardian/
├── analytics/          # 비용 분석, 대시보드, 예측
├── ml/                 # ML 모델, 훈련, 추론
├── detectors/          # 이상 탐지 엔진
├── forecasters/        # 비용 예측 모델
└── intelligence/       # 위협 인텔리전스
```

## Analytics 모듈

| 파일 | 기능 |
|------|------|
| `analytics_engine.py` | 통합 분석 엔진 |
| `arima_forecaster.py` | ARIMA 시계열 비용 예측 |
| `cost_analyzer.py` | 비용 구조 분석 |
| `cost_forecaster.py` | 다기간 비용 예측 |
| `trend_analyzer.py` | 비용/보안 트렌드 분석 |
| `seasonality_detector.py` | 계절성 패턴 감지 |
| `pattern_recognizer.py` | 비정상 패턴 인식 |
| `recommendation_engine.py` | 비용 최적화 추천 |
| `optimization_suggester.py` | 리소스 최적화 제안 |
| `dashboard_generator.py` | 분석 대시보드 생성 |

## ML 모듈

| 파일 | 기능 |
|------|------|
| `ml/` | ML 모델 정의 및 훈련 |
| `detectors/anomaly_detection_engine.py` | 앙상블 이상 탐지 |
| `detectors/anomaly_detector.py` | 단순 이상 탐지 |
| `detectors/statistical_anomaly.py` | 통계적 이상 탐지 |
| `detectors/attack_chain_detector.py` | 공격 체인 탐지 |
| `predictors/` | 예측 모델 |

## ARIMA 비용 예측

```python
# arima_forecaster.py 개념적 흐름
class ARIMAForecaster:
    def fit(self, historical_costs: List[float]):
        # 과거 7-30일 비용 데이터로 모델 훈련
        self.model = ARIMA(historical_costs, order=(p, d, q))
        self.model.fit()

    def forecast(self, days: int = 7) -> List[float]:
        # 향후 N일 비용 예측
        return self.model.forecast(steps=days)
```

> [!tip] ARIMA 사용 시점
> 비용이 예측 가능한 패턴(주중/주말 차이, 월말 스파이크)을 따를 때 효과적입니다.
> 갑작스러운 공격으로 인한 비용 폭발은 이상 탐지(anomaly_detection_engine)로 잡습니다.

## 앙상블 이상 탐지

```python
# anomaly_detection_engine.py 개념
class AnomalyDetectionEngine:
    detectors = [
        StatisticalAnomalyDetector(),   # Z-score, IQR
        MLAnomalyDetector(),            # Isolation Forest
        RuleBasedDetector(),            # 규칙 기반
    ]

    def detect(self, data) -> AnomalyResult:
        results = [d.detect(data) for d in self.detectors]
        # 다수결 또는 가중 평균으로 최종 결정
        return self._ensemble(results)
```

> [!important] 앙상블의 장점
> 단일 알고리즘은 특정 패턴에만 강합니다.
> 여러 탐지기를 결합하면 오탐(false positive)을 줄이고 미탐(false negative)을 최소화합니다.

## 비용 최적화 추천

```
수집: Cost Explorer API → 서비스별 비용 내역
분석: optimization_suggester.py
  - EC2: 사용률 낮은 인스턴스 → 다운사이즈 또는 Reserved 구매 추천
  - S3: 접근 빈도 낮은 객체 → Intelligent Tiering 전환
  - Lambda: 메모리/타임아웃 최적화
결과: recommendation_engine.py → 우선순위 추천 목록
```

## 계절성 탐지

```python
# seasonality_detector.py
def detect_patterns(costs: List[float]) -> dict:
    return {
        "weekly": detect_weekly_pattern(costs),    # 주간 패턴
        "monthly": detect_monthly_pattern(costs),  # 월간 패턴
        "spike_days": find_spike_days(costs),      # 스파이크 일자
    }
```

## Related Notes

- [[Handlers & Engines]]
- [[Multi-Account]]
- [[CostChecker]]
- [[시스템 아키텍처]]
