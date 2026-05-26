# Sprint 62: Advanced Auto-Response & Real-time Event Integration

## Context

**현황:**
- Sprint 60 완료: 33 테스트 PASS (Playbook Execution & Actions System)
- Sprint 61 완료: 51 테스트 PASS (Advanced Learning & Real-time Dashboard)
- 누적 테스트: 164 테스트 PASS
- 아키텍처: Threat Detection → ML Prediction → Playbook Mapping → Execution → Real-time Dashboard

**핵심 문제:**
- **실시간 이벤트 수집이 WebSocket 중심**: CloudTrail 스트림으로 변경 필요
- **규칙 기반 이상 탐지 미흡**: 통계적 임계값 생성 필요
- **자동 대응 효율성 낮음**: 의사결정 규칙이 경직되어 있음
- **웹 UI 대시보드 미구현**: 실시간 위협 상황 시각화 필요
- **성능 최적화 미흡**: 대량 이벤트 처리 시 병목

**기존 인프라 (재활용):**
```
✅ PipelineOrchestrator - 6단계 파이프라인 구현됨
✅ DashboardBroadcaster - WebSocket 실시간 통신 구현됨
✅ ThreatIntelligence - CVE/IP 평판 통합 구현됨
✅ ModelRetrainer - ML 모델 재학습 구현됨
❌ CloudTrailCollector - CloudTrail 스트림 수집 없음 (신규)
❌ StatisticalAnomalyDetector - 통계 기반 이상 탐지 없음 (신규)
❌ AdaptiveAutoResponse - 적응형 자동 대응 없음 (신규)
❌ DashboardUI - 웹 UI 대시보드 없음 (신규)
```

**목표:**
Sprint 62는 **고급 자동 대응 및 실시간 이벤트 통합**을 구현합니다:
1. **Phase 1**: CloudTrail 스트림 수집 (실시간 AWS 이벤트)
2. **Phase 2**: 통계 기반 이상 탐지 (동적 임계값, Z-score)
3. **Phase 3**: 적응형 자동 대응 (학습 기반 결정, 비용 최적화)
4. **Phase 4**: 웹 대시보드 UI (React, 실시간 업데이트)

---

## Phase 1: CloudTrail Stream Collector

### 목표
AWS CloudTrail에서 실시간 이벤트를 수집하고 처리

### 구현 파일
- `lambda/guardian/collectors/cloudtrail_collector.py`: CloudTrailCollector 클래스 (~300 lines)
- `tests/backend/test_cloudtrail_collector.py`: 11개 테스트

### 핵심 클래스

```python
class CloudTrailCollector:
    """CloudTrail 스트림에서 AWS 이벤트 수집"""
    
    def start_collection(self, region: str, event_names: List[str]) -> str:
        """
        CloudTrail 수집 시작
        
        Returns: collector_id
        """
    
    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        CloudTrail 이벤트 처리
        
        Returns:
            {
                'event_id': str,
                'event_type': str,
                'source_ips': [str],
                'principals': [str],
                'resources': [str],
                'timestamp': str,
                'error_code': str (optional)
            }
        """
    
    def filter_events(self, event_type: str, filters: Dict) -> List[Dict]:
        """CloudTrail 이벤트 필터링"""
    
    def get_collection_stats(self, collector_id: str) -> Dict:
        """수집 통계 조회"""
```

### 지원 이벤트 타입

| Event Type | 설명 | 우선순위 |
|-----------|------|---------|
| `RunInstances` | EC2 인스턴스 기동 | HIGH |
| `PutObject` | S3 파일 업로드 | MEDIUM |
| `CreateAccessKey` | IAM 액세스 키 생성 | HIGH |
| `ModifySecurityGroup` | SecurityGroup 변경 | MEDIUM |
| `PutBucketPolicy` | S3 버킷 정책 변경 | MEDIUM |
| `CreateUser` | IAM 사용자 생성 | MEDIUM |
| `AttachUserPolicy` | IAM 정책 첨부 | MEDIUM |
| `CreateDBInstance` | RDS 데이터베이스 생성 | MEDIUM |

### 테스트 케이스 (11개)

1. `test_start_collection`: 수집 시작
2. `test_process_runinstances_event`: EC2 기동 이벤트 처리
3. `test_process_putobject_event`: S3 업로드 이벤트 처리
4. `test_process_createaccesskey_event`: IAM 액세스 키 이벤트 처리
5. `test_filter_events_by_type`: 이벤트 타입 필터링
6. `test_filter_events_by_principal`: 주체(사용자) 필터링
7. `test_get_collection_stats`: 수집 통계 조회
8. `test_event_deduplication`: 중복 이벤트 제거
9. `test_error_handling`: 에러 처리
10. `test_batch_processing`: 배치 처리
11. `test_collection_performance`: 성능 테스트 (1000 events/sec)

---

## Phase 2: Statistical Anomaly Detector

### 목표
통계적 이상 탐지로 동적 임계값 기반의 위협 탐지

### 구현 파일
- `lambda/guardian/detectors/statistical_anomaly.py`: StatisticalAnomalyDetector 클래스 (~280 lines)
- `tests/backend/test_statistical_anomaly.py`: 9개 테스트

### 핵심 클래스

```python
class StatisticalAnomalyDetector:
    """통계 기반 이상 탐지"""
    
    def train_baseline(self, historical_data: List[Dict], window_days: int = 7) -> Dict:
        """
        정상 패턴 학습
        
        Returns:
            {
                'baseline_id': str,
                'metrics': {
                    'mean': float,
                    'std_dev': float,
                    'percentile_95': float,
                    'percentile_99': float
                },
                'trained_at': str
            }
        """
    
    def detect_anomaly(self, event: Dict, baseline: Dict) -> Dict:
        """
        이상 탐지 (Z-score)
        
        Returns:
            {
                'is_anomaly': bool,
                'z_score': float,
                'anomaly_type': str,  # 'volumetric', 'behavioral', 'pattern'
                'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'confidence': float (0-1)
            }
        """
    
    def get_anomaly_insights(self, event: Dict, baseline: Dict) -> Dict:
        """이상에 대한 인사이트 제공"""
    
    def update_baseline(self, new_data: List[Dict]) -> None:
        """기준선 업데이트 (점진적 학습)"""
```

### 이상 탐지 알고리즘

**Z-Score 방식:**
```
Z = (X - μ) / σ

- Z > 3: CRITICAL (매우 이상)
- Z > 2: HIGH (매우 의심)
- Z > 1.5: MEDIUM (의심)
- Z <= 1.5: NORMAL
```

**이상 타입:**
- `volumetric`: 비정상적으로 많은 이벤트 (DDoS, 스캔)
- `behavioral`: 평소와 다른 행동 (야간 API 호출, 다른 리전)
- `pattern`: 예상치 못한 패턴 (특정 사용자의 대량 작업)

### 테스트 케이스 (9개)

1. `test_train_baseline`: 기준선 학습
2. `test_detect_normal_event`: 정상 이벤트 탐지
3. `test_detect_volumetric_anomaly`: 볼륨 이상 탐지
4. `test_detect_behavioral_anomaly`: 행동 이상 탐지
5. `test_detect_pattern_anomaly`: 패턴 이상 탐지
6. `test_get_anomaly_insights`: 이상 인사이트
7. `test_update_baseline_incremental`: 점진적 기준선 업데이트
8. `test_multi_feature_anomaly`: 다중 특성 이상 탐지
9. `test_anomaly_scoring`: 이상 점수 계산

---

## Phase 3: Adaptive Auto-Response

### 목표
학습 기반의 적응형 자동 대응으로 효율성 극대화

### 구현 파일
- `lambda/guardian/response/adaptive_responder.py`: AdaptiveAutoResponse 클래스 (~250 lines)
- `tests/backend/test_adaptive_responder.py`: 8개 테스트

### 핵심 클래스

```python
class AdaptiveAutoResponse:
    """학습 기반 적응형 자동 대응"""
    
    def select_response(self, threat: Dict, feedback_history: List[Dict]) -> Dict:
        """
        위협에 최적의 대응 선택
        
        Returns:
            {
                'response_type': str,
                'playbook_id': str,
                'actions': [...],
                'expected_cost_savings': float,
                'confidence': float,
                'reasoning': str
            }
        """
    
    def estimate_response_effectiveness(self, threat_type: str, response_type: str) -> float:
        """
        대응 효과 추정 (0-1)
        
        기준: 위협 완화율 = (탐지된 위협 - 재발생) / 탐지된 위협
        """
    
    def estimate_cost_impact(self, response_actions: List[Dict]) -> Dict:
        """
        비용 영향도 계산
        
        Returns:
            {
                'immediate_cost': float,
                'monthly_savings': float,
                'cost_benefit_ratio': float
            }
        """
    
    def learn_from_feedback(self, response_id: str, feedback: Dict) -> None:
        """피드백으로부터 학습 (강화학습)"""
    
    def get_response_history(self, threat_type: str, days: int = 30) -> List[Dict]:
        """대응 이력 조회 및 분석"""
```

### 의사결정 프레임워크

```
위협 탐지
    ↓
현재 상황 평가
  - 위협 심각도
  - 영향 범위
  - 필요 리소스
    ↓
후보 대응 생성
  - 적극적 대응 (EC2 중지, 차단)
  - 모니터링 강화
  - 격리
    ↓
효과도 추정
  - 히스토리 기반 성공률
  - 피드백 학습 결과
    ↓
비용-효과 분석
  - 대응 비용 vs 절감액
  - ROI 계산
    ↓
최적 대응 선택
  - 효과도 높음 + 비용 효율적
```

### 테스트 케이스 (8개)

1. `test_select_response_critical_threat`: CRITICAL 위협 대응 선택
2. `test_select_response_low_threat`: LOW 위협 대응 선택
3. `test_estimate_effectiveness`: 대응 효과 추정
4. `test_estimate_cost_impact`: 비용 영향도 계산
5. `test_learn_from_feedback`: 피드백 학습
6. `test_get_response_history`: 대응 이력 조회
7. `test_adaptive_learning_improves`: 적응 학습으로 효율 향상
8. `test_cost_benefit_optimization`: 비용-효과 최적화

---

## Phase 4: Dashboard Web UI

### 목표
React 기반 실시간 대시보드로 위협 현황 시각화

### 구현 파일 (Next.js + React)
- `apps/web/src/app/dashboard/page.tsx`: 메인 대시보드
- `apps/web/src/components/ThreatMap.tsx`: 위협 지도 (지리적 분포)
- `apps/web/src/components/RealTimeMetrics.tsx`: 실시간 메트릭
- `apps/web/src/components/ResponseHistory.tsx`: 대응 이력
- `apps/web/src/hooks/useThreatSocket.ts`: WebSocket 훅
- `tests/frontend/dashboard.test.tsx`: 7개 테스트

### 주요 컴포넌트

**1. Dashboard Page**
```typescript
- Real-time threat counter
- System health status (HEALTHY/DEGRADED/FAILED)
- Active threats list with severity badges
- Response action queue
- Cost savings indicator
```

**2. Threat Map**
```typescript
- Geolocation-based threat visualization
- Threat clustering by region
- Interactive tooltip with threat details
- Heatmap of threat density
```

**3. Real-time Metrics**
```typescript
- Threat detection rate (threats/hour)
- Response success rate (%)
- Average response time (seconds)
- Cost savings ($/hour, $/day, $/month)
- System uptime
```

**4. Response History**
```typescript
- Timeline of recent responses
- Playbook execution status
- Action details and results
- Cost impact per response
```

### 테스트 케이스 (7개)

1. `test_dashboard_renders`: 대시보드 렌더링
2. `test_threat_counter_updates`: 위협 카운터 실시간 업데이트
3. `test_threat_map_display`: 위협 지도 표시
4. `test_metrics_real_time`: 메트릭 실시간 업데이트
5. `test_response_history_display`: 대응 이력 표시
6. `test_websocket_connection`: WebSocket 연결
7. `test_dashboard_responsiveness`: 반응형 디자인

---

## 전체 파이프라인 흐름 (Sprint 62)

```
CloudTrail Events [Phase 1] ← NEW
    ↓
Real-time Processing
    ├─ Event Parsing & Filtering
    ├─ Deduplication
    └─ Enrichment
    ↓
Statistical Anomaly Detection [Phase 2] ← NEW
    ├─ Z-Score Calculation
    ├─ Volumetric Analysis
    ├─ Behavioral Analysis
    └─ Severity Assignment
    ↓
Existing Pipeline (Sprint 60-61)
    ├─ ML Prediction
    ├─ Playbook Mapping
    └─ Threat Intelligence Enrichment
    ↓
Adaptive Auto-Response [Phase 3] ← NEW
    ├─ Response Selection (learning-based)
    ├─ Cost-Benefit Analysis
    ├─ Effectiveness Estimation
    └─ Feedback Learning
    ↓
Playbook Execution (Sprint 60)
    ├─ Dependency Orchestration
    ├─ Action Execution
    └─ Audit Logging
    ↓
Real-time Dashboard UI [Phase 4] ← NEW
    ├─ Threat Map
    ├─ Metrics Display
    ├─ Response History
    └─ Cost Dashboard
```

---

## 구현 순서 및 테스트

| Phase | 단계 | 파일 | 테스트 수 | 누적 |
|-------|------|------|---------|------|
| 1 | CloudTrailCollector | cloudtrail_collector.py | 11 | 11 |
| 2 | StatisticalAnomalyDetector | statistical_anomaly.py | 9 | 20 |
| 3 | AdaptiveAutoResponse | adaptive_responder.py | 8 | 28 |
| 4 | Dashboard Web UI | ThreatMap, Metrics 등 | 7 | 35 |
| **전체** | Sprint 62 | 4개 파일 + UI | **35** | **199** |

---

## 기술 스택 (Sprint 62)

| 레이어 | 기술 |
|--------|------|
| 이벤트 수집 | AWS CloudTrail API, S3 Events |
| 스트림 처리 | AWS Lambda, SQS (async) |
| 이상 탐지 | NumPy, SciPy (statistical analysis) |
| 의사결정 | 강화학습 (reward-based) |
| 백엔드 | Python Lambda (계속) |
| 웹 프론트엔드 | Next.js 16.2.4, React 19.2.4, TailwindCSS |
| 실시간 통신 | WebSocket (기존) |
| 지도 시각화 | Mapbox GL / Leaflet |
| 차트 | Chart.js / Recharts |
| 테스트 | pytest (백엔드 35개), Jest (프론트엔드 7개) |

---

## 검증 체크리스트

**Phase 1: CloudTrailCollector**
- [ ] CloudTrail 스트림 수집
- [ ] 8개 이벤트 타입 지원
- [ ] 이벤트 필터링 및 정제
- [ ] 중복 제거
- [ ] 배치 처리 (1000 events/sec)
- [ ] 11개 테스트 PASS

**Phase 2: StatisticalAnomalyDetector**
- [ ] Z-score 계산
- [ ] 3가지 이상 탐지 (volumetric, behavioral, pattern)
- [ ] 동적 임계값
- [ ] 점진적 학습
- [ ] 다중 특성 분석
- [ ] 9개 테스트 PASS

**Phase 3: AdaptiveAutoResponse**
- [ ] 학습 기반 대응 선택
- [ ] 효과도 추정
- [ ] 비용 영향도 계산
- [ ] 강화학습 (피드백)
- [ ] 비용-효과 최적화
- [ ] 8개 테스트 PASS

**Phase 4: Dashboard Web UI**
- [ ] 위협 지도 (Geo visualization)
- [ ] 실시간 메트릭
- [ ] 대응 이력 타임라인
- [ ] WebSocket 통합
- [ ] 반응형 디자인
- [ ] 7개 테스트 PASS

**최종:**
- [ ] 누적 35개 테스트 모두 PASS
- [ ] 전체 테스트: 164 (Sprint 54-61) + 35 (Sprint 62) = 199 PASS
- [ ] Git 커밋: "feat: Sprint 62 - Advanced Auto-Response & Real-time Event Integration (35 tests)"

---

## 다음 단계 (Sprint 63)

**Sprint 63 계획:**
- Phase 1: 자동 대응 피드백 루프 고도화
- Phase 2: SIEM 통합 (Splunk, ELK Stack)
- Phase 3: Slack/PagerDuty 알림 연동
- Phase 4: 성능 최적화 및 스케일링 (대량 이벤트 처리)

---

## 추가 노트

### 설계 고려사항
1. **실시간성**: CloudTrail → Lambda → Processing 지연 < 1초
2. **정확성**: 통계 모델의 거짓 양성(False Positive) 최소화
3. **비용 인식**: 자동 대응의 비용-효과 분석
4. **적응성**: 피드백을 통한 지속적 개선
5. **가시성**: 실시간 대시보드로 완전한 상황 인식

### 프로덕션 고려사항 (v1.2+)
- CloudTrail 로그를 S3에 저장 후 배치 처리
- EventBridge로 CloudTrail 이벤트 자동 라우팅
- DynamoDB에 통계 모델 저장 (버전 관리)
- Lambda 타임아웃 고려 (15분 제한)
- 대시보드용 메트릭을 CloudWatch에 발행

---

**Sprint 62 시작**: May 27, 2026
**목표**: 고급 자동 대응 및 실시간 이벤트 통합 완성
**테스트 목표**: 35/35 PASS
