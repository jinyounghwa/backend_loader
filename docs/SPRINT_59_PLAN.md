# Sprint 59: ML-Based Threat Response Automation

## Context

**Current Status:**
- Sprint 56 완료: 15 tests PASS (Custom Response Playbooks)
- Sprint 57 완료: 14 tests PASS (Real-time Threat Dashboard)
- Sprint 58 완료: 47 tests PASS (ML Threat Correlation)
- 누적 테스트: 76 tests PASS
- 아키텍처: Threat Detection → ML Analysis → Dashboard → **Automated Response** (NEW)

**핵심 문제:**
- **ML 예측 결과가 대시보드에만 표시되고 있음**
- 위협이 감지되면 관리자의 수동 조치 필요
- 반복적인 패턴의 위협에는 자동 대응 불가능
- 응답 시간이 길어서 피해 확대 가능

**기존 인프라 (재활용):**
```
✅ ML Prediction Model - 위협 예측 완료
✅ Playbook Execution - 자동 대응 엔진 완료
✅ Real-time Dashboard - 실시간 업데이트 완료
❌ ML-Playbook Mapping - 예측 ↔ 대응 매핑 없음 (신규 구현 필요)
❌ Auto-Trigger System - ML 기반 자동 트리거 없음 (신규 구현 필요)
❌ Response Metrics - 대응 효율성 추적 없음 (신규 구현 필요)
```

**목표:**
Sprint 59는 **ML 기반 위협 자동 대응 시스템**을 구현합니다:
1. **Phase 1**: ML Prediction → Playbook Mapping (예측 결과에 맞는 대응 규칙)
2. **Phase 2**: Auto-Trigger Workflow (조건 충족 시 자동 실행)
3. **Phase 3**: Response Validation & Metrics (대응 결과 검증 및 효율성 추적)
4. **Phase 4**: Adaptive Response Learning (성공/실패에 따른 학습)

---

## 구현 파일 목록

### Phase 1: ML → Playbook Mapping

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/response_mapper.py` | 신규: ResponseMapper (ML 예측 → Playbook 매핑) |
| `lambda/guardian/handlers/ml_response_handler.py` | 신규: POST /ml/map-response 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/map-response/route.ts` | 신규: 매핑 API 라우트 |
| `tests/backend/test_ml_response_mapping.py` | 신규: Mapping 테스트 (5개) |

### Phase 2: Auto-Trigger Workflow

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/auto_trigger_engine.py` | 신규: AutoTriggerEngine (자동 트리거 엔진) |
| `lambda/guardian/handlers/ml_trigger_handler.py` | 신규: POST /ml/trigger-response 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/trigger/route.ts` | 신규: 트리거 API |
| `tests/backend/test_auto_trigger.py` | 신규: Auto-trigger 테스트 (5개) |

### Phase 3: Response Metrics

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/storage/response_metrics.py` | 신규: ResponseMetricsRepository (메트릭 저장) |
| `lambda/guardian/handlers/metrics_handler.py` | 신규: GET /ml/response-metrics 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/metrics/route.ts` | 신규: 메트릭 조회 API |
| `apps/web/src/components/Dashboard/ResponseMetricsPanel.tsx` | 신규: 메트릭 시각화 UI |
| `tests/backend/test_response_metrics.py` | 신규: Metrics 테스트 (5개) |

### Phase 4: Adaptive Learning

| 파일 | 수정 내용 |
|------|---------|
| `lambda/guardian/ml/response_feedback_engine.py` | 신규: 대응 피드백 처리 |
| `lambda/guardian/handlers/feedback_handler.py` | 신규: POST /ml/response-feedback 엔드포인트 |
| `apps/web/src/app/api/guardian/ml/feedback/route.ts` | 신규: 피드백 API |
| `tests/backend/test_adaptive_learning.py` | 신규: Adaptive learning 테스트 (4개) |

---

## 구현 상세

### Phase 1: ML → Playbook Mapping (180L)

**ResponseMapper 클래스**

ML 예측 결과 → 적절한 Playbook 선택:
```python
class ResponseMapper:
    def __init__(self, playbooks_repo):
        self.playbooks = playbooks_repo
    
    def map_prediction_to_playbook(self, prediction):
        """
        위협 예측 → 최적의 Playbook 매핑
        반환: {
            'threat_type': 'Unknown Region',
            'prediction_confidence': 0.95,
            'recommended_playbooks': [
                {
                    'playbook_id': 'pb-001',
                    'name': 'Block Unknown Region',
                    'severity_threshold': 7,
                    'auto_execute': True,
                    'match_score': 0.98
                }
            ],
            'primary_playbook': 'pb-001'
        }
        """
    
    def map_cluster_to_playbook(self, cluster):
        """유사 위협 클러스터 → 대표 대응 규칙"""
    
    def map_pattern_to_playbook(self, pattern):
        """반복 패턴 → 예방 조치"""
```

**매핑 로직:**
- 위협 타입 기반 매칭 (Unknown Region → 차단)
- 심각도 기반 우선순위 (High → 즉시 차단)
- 클러스터 분석 (유사 위협 그룹 → 공통 대응)
- 패턴 인식 (반복 패턴 → 예방 조치)

**테스트 (5개)**
- test_prediction_to_playbook_mapping
- test_cluster_based_mapping
- test_pattern_based_mapping
- test_confidence_score_filtering
- test_multi_playbook_recommendation

### Phase 2: Auto-Trigger Workflow (200L)

**AutoTriggerEngine 클래스**

조건 충족 시 자동으로 Playbook 실행:
```python
class AutoTriggerEngine:
    def __init__(self, playbook_executor, response_mapper):
        self.executor = playbook_executor
        self.mapper = response_mapper
    
    def should_auto_execute(self, prediction, playbook):
        """
        자동 실행 여부 판단
        조건:
        1. 예측 신뢰도 > threshold (기본 0.9)
        2. Playbook auto_execute = True
        3. 심각도 >= 7
        4. 최근 유사 위협 패턴 감지
        """
    
    def execute_auto_response(self, threat, playbook):
        """
        자동 대응 실행
        반환: {
            'execution_id': 'exec-123',
            'status': 'success' | 'partial' | 'failed',
            'actions_executed': 5,
            'resources_affected': 3,
            'execution_time_ms': 245,
            'rollback_available': True
        }
        """
    
    def create_execution_context(self, threat):
        """자동 대응 실행 컨텍스트 생성"""
```

**실행 조건:**
- Confidence >= 90% (예측 확실성)
- Severity >= 7 (위협 심각도)
- Auto-execute enabled (Playbook 설정)
- No manual override (수동 금지 설정)

**테스트 (5개)**
- test_auto_execute_decision
- test_confidence_threshold_filtering
- test_severity_based_auto_trigger
- test_pattern_based_auto_trigger
- test_rollback_capability

### Phase 3: Response Metrics (200L)

**ResponseMetricsRepository 클래스**

대응 효율성 추적:
```python
class ResponseMetricsRepository:
    def record_response(self, response_data):
        """
        대응 결과 기록
        저장: {
            'response_id': 'resp-123',
            'threat_id': 'threat-456',
            'playbook_id': 'pb-001',
            'predicted_threat_type': 'Unknown Region',
            'actual_threat_type': 'Unknown Region',  # 예측 정확성 확인
            'auto_executed': True,
            'success': True,
            'time_to_response_ms': 245,
            'resources_affected': 3,
            'cost_saved': '$500',
            'timestamp': '2026-05-26T...'
        }
        """
    
    def get_response_metrics(self, account_id, time_range='24h'):
        """
        대응 메트릭 조회
        반환: {
            'total_responses': 42,
            'auto_executed': 35,
            'manual_executed': 7,
            'success_rate': 0.95,
            'average_response_time_ms': 312,
            'prevented_incidents': 8,
            'estimated_cost_saved': '$3,500',
            'playbook_effectiveness': {
                'pb-001': { 'success_rate': 0.98, 'usage_count': 15 },
                'pb-002': { 'success_rate': 0.85, 'usage_count': 8 }
            }
        }
        """
    
    def get_ml_accuracy(self, account_id):
        """ML 예측 정확성 측정"""
```

**메트릭 지표:**
- Success rate (성공률)
- Response time (대응 시간)
- Cost savings (절감액)
- Threat accuracy (예측 정확도)
- Playbook effectiveness (Playbook 효율성)

**테스트 (5개)**
- test_response_recording
- test_success_rate_calculation
- test_average_response_time
- test_ml_prediction_accuracy
- test_playbook_effectiveness_ranking

### Phase 4: Adaptive Learning (180L)

**ResponseFeedbackEngine 클래스**

대응 결과에서 학습:
```python
class ResponseFeedbackEngine:
    def process_feedback(self, response_id, feedback):
        """
        대응 피드백 처리
        입력: {
            'response_id': 'resp-123',
            'success': True | False,
            'notes': '상세 피드백',
            'improvements': ['더 빨리 차단', '더 정확한 판단']
        }
        """
    
    def update_ml_model(self, feedback_data):
        """피드백 기반 ML 모델 업데이트"""
    
    def adjust_playbook_priority(self, playbook_id, feedback):
        """피드백 기반 Playbook 우선순위 조정"""
    
    def learn_response_patterns(self, success_cases):
        """성공 사례에서 패턴 학습"""
```

**학습 방식:**
- 성공/실패 사례 수집
- 특정 위협 유형별 최적 Playbook 식별
- 응답 시간 최적화
- 오탐(false positive) 감소

**테스트 (4개)**
- test_feedback_processing
- test_model_update_from_feedback
- test_playbook_priority_adjustment
- test_learning_effectiveness

---

## 구현 전략

### 데이터 구조

**Playbook Mapping**
```python
{
    'threat_type': 'Unknown Region',
    'playbooks': [
        {
            'playbook_id': 'pb-001',
            'name': 'Block Unknown Region EC2',
            'type': 'ec2_stop',
            'severity_threshold': 7,
            'confidence_threshold': 0.85,
            'auto_execute': True,
            'match_score': 0.98,  # 위협과의 유사도
            'expected_resolution_time': 300
        }
    ]
}
```

**Auto-Trigger Decision**
```python
{
    'threat_id': 'threat-123',
    'prediction_confidence': 0.95,
    'threat_severity': 8,
    'should_auto_trigger': True,
    'trigger_reason': 'high_confidence + high_severity',
    'selected_playbook': 'pb-001',
    'estimated_execution_time': 245,
    'can_rollback': True
}
```

**Response Metrics**
```python
{
    'response_id': 'resp-123',
    'success': True,
    'response_time_ms': 245,
    'playbook_id': 'pb-001',
    'resources_affected': 3,
    'threat_resolved': True,
    'cost_saved': '$500',
    'ml_prediction_correct': True
}
```

### 성능 목표

- **자동 대응 비율**: 80% 이상 (수동 개입 최소화)
- **응답 시간**: 평균 < 300ms (초기 감지 → 대응 완료)
- **성공률**: 95% 이상 (대응 실패 < 5%)
- **예측 정확도**: 90% 이상 (예측과 실제 일치)
- **비용 절감**: 월별 > $5,000

---

## 구현 순서 및 테스트

| Phase | 단계 | 테스트 수 | 누적 |
|-------|------|---------|------|
| 1 | ML → Playbook Mapping | 5 | 5 |
| 2 | Auto-Trigger Workflow | 5 | 10 |
| 3 | Response Metrics | 5 | 15 |
| 4 | Adaptive Learning | 4 | 19 |
| **전체** | Sprint 59 | **19** | **19** |

---

## 기술 스택 (Sprint 59)

| 레이어 | 기술 |
|--------|------|
| 데이터베이스 | DynamoDB (ResponseMetricsTable, MappingCacheTable) |
| 응답 매퍼 | Python (ResponseMapper, decision trees) |
| 자동 트리거 | Python (AutoTriggerEngine, conditional logic) |
| 메트릭 수집 | DynamoDB Streams → Lambda |
| 대시보드 | React (ResponseMetricsPanel) |
| 백엔드 | Python Lambda, boto3 |
| 인프라 | AWS SAM (template.yaml) |
| 테스트 | pytest (백엔드 19개) |

---

## 아키텍처 흐름 (ML 예측 → 자동 대응)

```
ML Prediction Result
    ↓
ResponseMapper: prediction → recommended_playbooks[]
    ↓
AutoTriggerEngine: should_auto_execute(confidence, severity, pattern)?
    ↓
YES → Execute Playbook
    ├─ Create execution context
    ├─ Run remediation actions
    └─ Record metrics
         ↓
    NO → User Review Required
         └─ Dashboard alert for manual action

Response Feedback → ResponseFeedbackEngine
    ├─ Update ML model
    ├─ Adjust playbook priority
    └─ Learn patterns
```

---

## 주요 설계 결정

**1. 자동 대응 임계값**
- Confidence >= 90% (높은 확실성)
- Severity >= 7 (위협 심각도)
- Pattern detected (반복 패턴)
- Auto-execute enabled (Playbook 설정)

**2. 롤백 전략**
- 모든 자동 대응은 롤백 가능
- 실패 시 자동 롤백
- 사용자는 수동 롤백 가능

**3. 메트릭 수집**
- 모든 대응 결과 기록
- 성공/실패 추적
- ML 예측 정확도 검증
- Playbook 효율성 측정

**4. 학습 반영**
- 월별 모델 재학습
- 성공 사례 우선순위 상향
- 실패 사례 분석 및 개선

---

## 검증 체크리스트

**Phase 1: ML → Playbook Mapping**
- [ ] ResponseMapper 클래스 구현
- [ ] POST /ml/map-response 엔드포인트
- [ ] 5개 테스트 PASS

**Phase 2: Auto-Trigger Workflow**
- [ ] AutoTriggerEngine 구현
- [ ] POST /ml/trigger-response 엔드포인트
- [ ] 롤백 기능 구현
- [ ] 5개 테스트 PASS

**Phase 3: Response Metrics**
- [ ] ResponseMetricsRepository 구현
- [ ] GET /ml/response-metrics 엔드포인트
- [ ] ResponseMetricsPanel UI 구현
- [ ] 5개 테스트 PASS

**Phase 4: Adaptive Learning**
- [ ] ResponseFeedbackEngine 구현
- [ ] POST /ml/response-feedback 엔드포인트
- [ ] 모델 업데이트 로직
- [ ] 4개 테스트 PASS

**최종:**
- [ ] 누적 19개 테스트 모두 PASS
- [ ] 전체 테스트: 76 (Sprint 56-58) + 19 (Sprint 59) = 95 PASS
- [ ] Git 커밋: "feat: Sprint 59 - ML-Based Threat Response Automation"

---

## 다음 단계 (Sprint 60+)

**향후 개선:**
- 사용자 피드백 기반 모델 개선
- 실시간 CloudTrail 통합
- 고급 패턴 인식 (AI-based anomaly)
- 멀티 테넌트 대응 전략
- 규칙 템플릿 라이브러리

---

**Sprint 59 목표:** ML 예측 결과를 활용한 완전 자동화된 위협 대응 시스템 구현
