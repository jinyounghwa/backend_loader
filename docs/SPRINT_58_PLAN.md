# Sprint 58: Machine Learning Threat Correlation

## Context

**Current Status:**
- Sprint 56 완료: 15 tests PASS (Custom Response Playbooks)
- Sprint 57 완료: 14 tests PASS (Real-time Threat Dashboard)
- 누적 테스트: 912 tests PASS
- 아키텍처: Threat Detection → Playbook Matching → Real-time Broadcasting

**핵심 문제:**
- **규칙 기반 감지는 알려진 위협만 탐지 가능**
- 새로운 공격 패턴이나 복합 위협은 놓칠 수 있음
- 위협들 간의 연관성이 분석되지 않음
- 단순 임계값 기반으로는 미묘한 이상을 감지할 수 없음

**기존 인프라 (재활용):**
```
✅ Threat Detection Engine - 위협 감지 완료
✅ Playbook Execution - 자동 대응 완료
✅ Real-time Dashboard - 실시간 업데이트 완료
❌ Threat Prediction Model - 미래 위협 예측 없음 (신규 구현 필요)
❌ Anomaly Clustering Engine - 유사 위협 그룹핑 없음 (신규 구현 필요)
❌ Threat Trend Analyzer - 시간대 추세 분석 없음 (신규 구현 필요)
❌ Pattern Recognition Service - 공격 패턴 학습 없음 (신규 구현 필요)
```

**목표:**
Sprint 58은 **기계학습 기반 위협 상관관계 시스템**을 구현합니다:
1. **Phase 1**: Threat Prediction Model (미래 위협 예측)
2. **Phase 2**: Anomaly Clustering Engine (유사 위협 자동 그룹핑)
3. **Phase 3**: Threat Trend Analyzer (시간대 추세 분석)
4. **Phase 4**: Pattern Recognition Service (반복 공격 패턴 학습)

---

## 구현 파일 목록

### Phase 1: Threat Prediction Model

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/threat_prediction_model.py` | 신규: ThreatPredictionModel (시계열 ARIMA + 통계) |
| `lambda/guardian/handlers/ml_prediction_handler.py` | 신규: POST /predict-threats 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/predict/route.ts` | 신규: 예측 API 라우트 |
| `apps/web/src/components/Dashboard/ThreatPredictionPanel.tsx` | 신규: 예측 시각화 UI |
| `tests/backend/test_threat_prediction.py` | 신규: Prediction 테스트 (4개) |

### Phase 2: Anomaly Clustering Engine

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/anomaly_clustering_engine.py` | 신규: K-Means clustering (유사도 기반) |
| `lambda/guardian/handlers/ml_clustering_handler.py` | 신규: POST /cluster-threats 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/cluster/route.ts` | 신규: 클러스터링 API |
| `apps/web/src/components/Dashboard/AnomalyClusterPanel.tsx` | 신규: 클러스터 그룹 시각화 |
| `tests/backend/test_anomaly_clustering.py` | 신규: Clustering 테스트 (2개) |

### Phase 3: Threat Trend Analyzer

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/threat_trend_analyzer.py` | 신규: 시간대별 추세 분석 |
| `lambda/guardian/handlers/ml_trend_handler.py` | 신규: GET /threat-trends 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/trends/route.ts` | 신규: 추세 조회 API |
| `apps/web/src/components/Dashboard/ThreatTrendChart.tsx` | 신규: 추세 라인 차트 |
| `tests/backend/test_threat_trends.py` | 신규: Trend 테스트 (2개) |

### Phase 4: Pattern Recognition Service

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/pattern_recognition_service.py` | 신규: 반복 패턴 학습 (Subsequence matching) |
| `lambda/guardian/handlers/ml_pattern_handler.py` | 신규: POST /identify-patterns 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/patterns/route.ts` | 신규: 패턴 조회 API |
| `apps/web/src/components/Dashboard/PatternRecognitionPanel.tsx` | 신규: 패턴 매칭 결과 |
| `tests/integration/test_ml_correlation_integration.py` | 신규: 통합 테스트 (7개) |

---

## 구현 상세

### Phase 1: Threat Prediction Model (220L)

**ThreatPredictionModel 클래스**

시계열 데이터를 통해 미래 위협을 예측:
```python
class ThreatPredictionModel:
    def __init__(self, historical_threats_table):
        self.threats = historical_threats_table
        self.arima = ARIMA(order=(1,1,1))
    
    def predict_threats(self, account_id, days_ahead=7, confidence=0.95):
        """
        지난 30일 위협 데이터 → ARIMA 모델 학습 → 향후 N일 예측
        반환: {
            'predictions': [
                {'date': '2026-06-02', 'expected_threats': 2.3, 'confidence': 0.95},
                {'date': '2026-06-03', 'expected_threats': 1.8, 'confidence': 0.92},
                ...
            ],
            'trend': 'increasing' | 'stable' | 'decreasing',
            'anomaly_score': 0.75,
            'model_accuracy': 0.87
        }
        """
    
    def train_model(self, account_id, lookback_days=30):
        """지난 N일 위협 데이터로 모델 재학습"""
    
    def get_prediction_confidence(self, account_id):
        """현재 모델 신뢰도 (0-1)"""
```

**테스트 (4개)**
- test_predict_threats: 기본 예측 (ARIMA)
- test_train_model: 모델 재학습
- test_predict_with_seasonality: 계절성 포함 예측
- test_prediction_confidence_score: 신뢰도 계산

### Phase 2: Anomaly Clustering Engine (190L)

**AnomalyClusteringEngine 클래스**

유사한 위협들을 자동으로 그룹화:
```python
class AnomalyClusteringEngine:
    def __init__(self, threat_feature_extractor):
        self.extractor = threat_feature_extractor
        self.kmeans = KMeans(n_clusters=5, random_state=42)
    
    def cluster_threats(self, threats, n_clusters=5):
        """
        위협 목록 → 특성 추출 → K-Means clustering
        반환: {
            'clusters': [
                {
                    'id': 'C001',
                    'threats': [threat_id1, threat_id2, ...],
                    'centroid': [f1, f2, f3],
                    'cohesion': 0.92,
                    'representative_threat': threat_id
                },
                ...
            ],
            'silhouette_score': 0.78
        }
        """
    
    def get_similar_threats(self, threat_id, similarity_threshold=0.7):
        """특정 위협과 유사한 다른 위협들 반환"""
    
    def update_cluster_centroids(self):
        """클러스터 중심점 업데이트"""
```

**테스트 (2개)**
- test_cluster_threats: K-Means clustering
- test_get_similar_threats: 유사 위협 검색

### Phase 3: Threat Trend Analyzer (185L)

**ThreatTrendAnalyzer 클래스**

위협의 시간대별 추세 분석:
```python
class ThreatTrendAnalyzer:
    def __init__(self, threats_table):
        self.threats = threats_table
    
    def analyze_trends(self, account_id, time_range='24h'):
        """
        시간대별 위협 분포 분석
        반환: {
            'hourly_breakdown': [
                {'hour': 0, 'threats': 5, 'avg_severity': 6.2},
                {'hour': 1, 'threats': 3, 'avg_severity': 5.8},
                ...
            ],
            'peak_hours': [15, 16, 17],
            'safe_hours': [2, 3, 4],
            'weekly_pattern': {...},
            'anomaly_hours': [12]  # 비정상 활동 시간
        }
        """
    
    def get_threat_velocity(self, account_id):
        """위협 발생 속도 (위협/시간)"""
    
    def get_threat_density(self, account_id, time_window='1h'):
        """시간 윈도우 내 위협 밀도"""
```

**테스트 (2개)**
- test_analyze_trends: 시간대별 추세 분석
- test_get_threat_velocity: 위협 속도 계산

### Phase 4: Pattern Recognition Service (210L)

**PatternRecognitionService 클래스**

반복되는 공격 패턴 자동 학습:
```python
class PatternRecognitionService:
    def __init__(self, threats_table):
        self.threats = threats_table
        self.patterns = {}
    
    def identify_patterns(self, account_id, min_support=0.3):
        """
        위협 시퀀스 패턴 감지 (Apriori 알고리즘)
        반환: {
            'patterns': [
                {
                    'id': 'P001',
                    'sequence': ['Unknown Region', 'Unauthorized SSH', 'Data Exfil'],
                    'support': 0.45,  # 패턴 발생 확률
                    'confidence': 0.92,  # 이전 단계 후 다음 단계 확률
                    'lift': 2.1,  # 독립적 대비 발생 확률
                    'occurrences': 23
                },
                ...
            ],
            'total_patterns': 12
        }
        """
    
    def match_pattern(self, threat_sequence):
        """현재 위협 시퀀스가 기존 패턴과 매칭되는지 확인"""
    
    def get_pattern_stats(self, pattern_id):
        """패턴 통계 (발생 횟수, 최근 발생시간, 평균 심각도)"""
```

**테스트 (7개 - 통합)**
- test_identify_patterns: Apriori 패턴 추출
- test_threat_sequence_matching: 시퀀스 패턴 매칭
- test_pattern_confidence_calculation: 신뢰도 계산
- test_anomaly_prediction_integration: 예측 + 클러스터링 통합
- test_trend_based_alert_escalation: 추세 기반 알림 에스컬레이션
- test_pattern_recommendation: 패턴 기반 예방 조치 추천
- test_ml_dashboard_metrics: ML 메트릭 대시보드 수집

---

## 구현 전략

### 데이터 구조

**Threat Feature Vector (각 위협)**
```
[
    severity (0-10),           # 위협 심각도
    account_risk_score (0-1),  # 계정 위험도
    event_frequency,           # 이벤트 빈도
    resource_impact_count,     # 영향받은 리소스 수
    response_time_seconds,     # 평균 대응 시간
    remediation_success_rate   # 대응 성공률
]
```

**Pattern Structure**
```python
{
    'id': 'P001',
    'sequence': ['threat_type_1', 'threat_type_2', ...],
    'support': 0.45,       # 발생 확률
    'confidence': 0.92,    # 다음 단계 확률
    'lift': 2.1,           # 연관성 강도
    'avg_duration_minutes': 45,
    'first_seen': '2026-05-10',
    'last_seen': '2026-05-25',
    'occurrences': 23,
    'remediation_rate': 0.87
}
```

### ML 알고리즘 선택

| Phase | 알고리즘 | 이유 |
|-------|---------|------|
| 1 | ARIMA | 시계열 예측, 계절성 처리, 구현 간단 |
| 2 | K-Means | 클러스터링 기준, 확장성, 실시간 처리 |
| 3 | 통계 (평균/분산) | 빠른 계산, 실시간 추세 분석 |
| 4 | Apriori | 시퀀스 패턴 마이닝, 확률 계산 정확 |

### 성능 목표

- **예측 정확도**: 85% 이상 (지난 30일 데이터 기준)
- **클러스터링 실루엣 점수**: 0.7 이상
- **패턴 신뢰도**: 90% 이상 (20회 이상 발생)
- **응답 시간**: 모든 API < 500ms

---

## 구현 순서 및 테스트

| Phase | 단계 | 테스트 수 | 누적 |
|-------|------|---------|------|
| 1 | Threat Prediction | 4 | 4 |
| 2 | Anomaly Clustering | 2 | 6 |
| 3 | Threat Trends | 2 | 8 |
| 4 | Pattern Recognition | 7 | 15 |
| **전체** | Sprint 58 Phase 1 | **15** | **941** |

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 데이터베이스 | DynamoDB (ThreatsTable, PatternsTable) |
| ML 프레임워크 | scikit-learn (ARIMA, K-Means) |
| 시계열 분석 | statsmodels (ARIMA) |
| 실시간 처리 | DynamoDB Streams + Lambda |
| 백엔드 | Python Lambda, boto3 |
| 프론트엔드 | Next.js, React, TailwindCSS, Recharts |
| 테스트 | pytest (8개), Jest (통합) |

---

## 다음 단계 (Sprint 59+)

**향후 개선:**
- 딥러닝 모델 (LSTM, GRU) - 더 복잡한 패턴
- 강화학습 (Q-Learning) - 동적 임계값 최적화
- 자동 피처 엔지니어링 - 새로운 특성 자동 발견
- 실시간 모델 재학습 - 온라인 학습
