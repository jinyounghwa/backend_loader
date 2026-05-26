# Sprint 61: Advanced Learning & Real-time Dashboard System

## Context

**지금까지의 진행:**
- Sprint 60 완료: 33 테스트 PASS (PlaybookExecutor, PlaybookOrchestrator, AuditLogger, DashboardMetrics)
- Sprint 59 완료: 30 테스트 PASS (ML Prediction, Response Mapping, Auto-Trigger, Response Feedback)
- Sprint 58 완료: 26 테스트 PASS (ML Pipeline Infrastructure)
- 누적 테스트: 89 테스트 PASS

**현재 시스템 아키텍처:**
```
위협 탐지 → ML 예측 → 플레이북 매핑 → 플레이북 실행 → 피드백 수집
    ↓          ↓            ↓              ↓              ↓
  Anomaly   Predictor   PlaybookMapper  ActionExecutor  FeedbackEngine
  Detector                                    ↓
                                          감사 로그 + 메트릭
```

**핵심 문제:**
- 수집된 피드백이 저장되기만 하고 모델 학습에 활용되지 않음
- 실시간 대시보드가 없어서 현황 파악이 느림 (배치 조회만 가능)
- 외부 위협 정보(CVE, 악성 IP)가 통합되지 않음
- 파이프라인 전체 상태를 모니터링할 방법이 없음

**목표:**
Sprint 61은 **고급 학습 & 실시간 대시보드 시스템**을 구현합니다:
1. **Phase 1**: 모델 재학습 엔진 (피드백 기반 모델 개선)
2. **Phase 2**: WebSocket 실시간 대시보드 (즉시 상태 업데이트)
3. **Phase 3**: 위협 인텔리전스 통합 (CVE, IP 평판)
4. **Phase 4**: 파이프라인 오케스트레이터 (전체 상태 모니터링)

---

## Phase 1: 모델 재학습 엔진 (ModelRetrainer)

### 목표
피드백 데이터를 활용하여 위협 예측 모델을 주기적으로 재학습합니다.

### 구현 파일

| 파일 | 내용 |
|------|------|
| `lambda/guardian/ml/model_retrainer.py` | ModelRetrainer 클래스 (피드백 기반 재학습) |
| `lambda/guardian/ml/feature_engineer.py` | FeatureEngineer 클래스 (특성 공학) |
| `lambda/guardian/storage/feedback_repository.py` | FeedbackRepository (피드백 저장소 확장) |
| `lambda/guardian/handlers/retraining_handler.py` | 재학습 Lambda 핸들러 |
| `tests/backend/test_model_retraining.py` | 재학습 테스트 (8개) |

### 구현 전략

**1.1. FeatureEngineer 클래스**

피드백 데이터에서 특성 추출:

```python
class FeatureEngineer:
    def extract_features(self, feedback_logs):
        """
        피드백 로그 → 특성 벡터 추출
        
        반환: {
            'num_threats_detected': int,
            'false_positive_rate': float,
            'detection_latency_avg': float,
            'action_success_rate': float,
            'threat_types': [str],
            'severity_distribution': {str: float},
            'time_of_day': str,
            'day_of_week': int,
            ...
        }
        """
        
    def engineer_features(self, threat_logs):
        """로그 → 특성 데이터프레임"""
        
    def extract_threat_patterns(self, detections, actions, outcomes):
        """위협 패턴 발견"""
```

**1.2. ModelRetrainer 클래스**

```python
class ModelRetrainer:
    def __init__(self, model_storage, feedback_repo, feature_engineer):
        self.model = model_storage
        self.feedback = feedback_repo
        self.engineer = feature_engineer
    
    def retrain_from_feedback(self, lookback_days=30):
        """
        지난 30일간의 피드백으로 모델 재학습
        
        반환: {
            'model_version': str,
            'training_samples': int,
            'accuracy': float,
            'precision': float,
            'recall': float,
            'f1_score': float,
            'improvements': {
                'threat_type': float,  # 개선율
                ...
            },
            'timestamp': str
        }
        """
        
        # 1. 피드백 수집 (지난 30일)
        feedback_logs = self.feedback.query_recent(days=lookback_days)
        
        # 2. 특성 추출
        X, y = self.engineer.extract_features(feedback_logs)
        
        # 3. 모델 재학습 (증분 학습)
        new_model = self.model.incremental_fit(X, y)
        
        # 4. 검증
        metrics = self._evaluate_model(new_model, X, y)
        
        # 5. 저장 (버전 관리)
        model_version = self.model.save_version(new_model, metrics)
        
        return {
            'model_version': model_version,
            'metrics': metrics,
            'training_samples': len(feedback_logs),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _evaluate_model(self, model, X, y):
        """모델 성능 평가"""
        predictions = model.predict(X)
        
        return {
            'accuracy': accuracy_score(y, predictions),
            'precision': precision_score(y, predictions, average='weighted'),
            'recall': recall_score(y, predictions, average='weighted'),
            'f1_score': f1_score(y, predictions, average='weighted'),
            'confusion_matrix': confusion_matrix(y, predictions).tolist()
        }
    
    def compare_with_previous(self, new_metrics):
        """이전 모델 대비 개선도 계산"""
        prev_metrics = self.model.get_previous_version_metrics()
        
        return {
            'accuracy_improvement': new_metrics['accuracy'] - prev_metrics['accuracy'],
            'precision_improvement': new_metrics['precision'] - prev_metrics['precision'],
            'recall_improvement': new_metrics['recall'] - prev_metrics['recall'],
            'f1_improvement': new_metrics['f1_score'] - prev_metrics['f1_score']
        }
```

**1.3. 재학습 Lambda 핸들러**

EventBridge 트리거 (매주 일요일 00:00 UTC):

```python
def handler(event, context):
    retrainer = ModelRetrainer(...)
    
    # 재학습 실행
    result = retrainer.retrain_from_feedback()
    
    # 개선도 확인
    improvements = retrainer.compare_with_previous(result['metrics'])
    
    # 임계값 초과 시 자동 배포
    if improvements['accuracy_improvement'] > 0.02:
        retrainer.deploy_new_model(result['model_version'])
        notify_deployment(result, improvements)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

### 테스트 케이스 (8개)

| # | 테스트 | 기대 결과 |
|---|--------|---------|
| 1 | `test_extract_features_basic` | 피드백 로그 → 특성 벡터 정상 추출 |
| 2 | `test_extract_features_empty` | 피드백 없음 → 빈 벡터 반환 |
| 3 | `test_retrain_with_feedback` | 피드백으로 모델 재학습 → 메트릭 반환 |
| 4 | `test_retrain_incremental` | 증분 학습 → 메모리 효율성 확인 |
| 5 | `test_model_version_management` | 모델 버전 저장/로드 정상 동작 |
| 6 | `test_compare_metrics_improvement` | 이전 모델 대비 개선도 계산 정확 |
| 7 | `test_retrain_schedule` | EventBridge 매주 실행 → Lambda 트리거 |
| 8 | `test_automatic_deployment` | 개선도 > 2% → 자동 배포 실행 |

---

## Phase 2: WebSocket 실시간 대시보드

### 목표
위협 탐지, 대응, 피드백 결과를 실시간으로 대시보드에 반영합니다.

### 구현 파일

| 파일 | 내용 |
|------|------|
| `lambda/guardian/handlers/websocket_handler.py` | WebSocket 연결 관리 |
| `lambda/guardian/realtime/dashboard_broadcaster.py` | 실시간 브로드캐스트 엔진 |
| `apps/web/src/hooks/useRealtimeDashboard.ts` | React Hook (실시간 업데이트) |
| `apps/web/src/components/Dashboard/RealtimeThreatFeed.tsx` | 실시간 위협 피드 UI |
| `tests/backend/test_websocket_dashboard.py` | WebSocket 테스트 (8개) |
| `tests/frontend/test_realtime_dashboard.tsx` | 프론트엔드 테스트 (3개) |

### 구현 전략

**2.1. DynamoDB 스트림 → WebSocket 연결**

```python
class DashboardBroadcaster:
    def __init__(self, apigateway_client):
        self.apigateway = apigateway_client
        self.active_connections = {}  # connection_id → ws_client
    
    async def on_threat_detected(self, threat):
        """위협 탐지 시 실시간 브로드캐스트"""
        message = {
            'type': 'threat_detected',
            'threat_id': threat.threat_id,
            'severity': threat.severity,
            'rule_id': threat.rule_id,
            'timestamp': threat.timestamp,
            'evidence': threat.evidence,
            'recommended_playbooks': threat.recommended_playbooks
        }
        
        await self.broadcast_to_all(message)
    
    async def on_action_executed(self, action):
        """작업 실행 시 실시간 업데이트"""
        message = {
            'type': 'action_executed',
            'action_id': action.action_id,
            'playbook_id': action.playbook_id,
            'status': action.status,
            'timestamp': action.timestamp,
            'cost': action.cost
        }
        
        await self.broadcast_to_all(message)
    
    async def on_feedback_submitted(self, feedback):
        """피드백 제출 시 메트릭 업데이트"""
        message = {
            'type': 'feedback_submitted',
            'feedback_id': feedback.feedback_id,
            'threat_id': feedback.threat_id,
            'is_correct': feedback.is_correct,
            'model_accuracy': await self._get_current_accuracy()
        }
        
        await self.broadcast_to_all(message)
    
    async def broadcast_to_all(self, message):
        """모든 연결된 클라이언트에 메시지 발송"""
        for connection_id in self.active_connections:
            try:
                await self.apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
            except Exception as e:
                logger.error(f"Failed to send to {connection_id}: {e}")
                await self._remove_connection(connection_id)
```

**2.2. 프론트엔드 Hook**

```typescript
export function useRealtimeDashboard() {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // WebSocket 연결
    const ws = new WebSocket(`wss://${process.env.NEXT_PUBLIC_API_ENDPOINT}/ws`);
    
    ws.onopen = () => console.log('Dashboard WebSocket connected');
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'threat_detected':
          setThreats(prev => [message, ...prev].slice(0, 50));
          break;
        case 'action_executed':
          setActions(prev => [message, ...prev].slice(0, 50));
          break;
        case 'feedback_submitted':
          setMetrics(prev => ({
            ...prev,
            model_accuracy: message.model_accuracy
          }));
          break;
      }
    };
    
    wsRef.current = ws;
    
    return () => ws.close();
  }, []);

  return { threats, actions, metrics };
}
```

### 테스트 케이스 (11개)

| # | 테스트 | 기대 결과 |
|---|--------|---------|
| 1 | `test_websocket_connect` | 클라이언트 연결 → 정상 등록 |
| 2 | `test_websocket_disconnect` | 클라이언트 해제 → 정상 제거 |
| 3 | `test_broadcast_threat_detected` | 위협 → 모든 클라이언트에 브로드캐스트 |
| 4 | `test_broadcast_action_executed` | 작업 → 모든 클라이언트에 브로드캐스트 |
| 5 | `test_broadcast_feedback_submitted` | 피드백 → 메트릭 업데이트 브로드캐스트 |
| 6 | `test_websocket_failure_resilience` | 일부 클라이언트 실패 → 나머지 계속 작동 |
| 7 | `test_realtime_threat_feed_ui` | 위협 메시지 도착 → UI 즉시 반영 |
| 8 | `test_realtime_action_feed_ui` | 작업 메시지 도착 → UI 즉시 반영 |
| 9 | `test_realtime_metrics_update` | 피드백 → 정확도 수치 즉시 업데이트 |
| 10 | `test_websocket_message_ordering` | 메시지 순서 유지 |
| 11 | `test_realtime_dashboard_performance` | 초당 100개 메시지 처리 → 지연 < 100ms |

---

## Phase 3: 위협 인텔리전스 통합

### 목표
외부 위협 정보(CVE, 악성 IP 평판)를 위협 탐지에 통합하여 정확도를 높입니다.

### 구현 파일

| 파일 | 내용 |
|------|------|
| `lambda/guardian/intelligence/threat_intelligence.py` | ThreatIntelligence 클래스 |
| `lambda/guardian/intelligence/cve_checker.py` | CVE 데이터베이스 조회 |
| `lambda/guardian/intelligence/ip_reputation.py` | IP 평판 조회 (AbuseIPDB, AlienVault) |
| `lambda/guardian/handlers/enrichment_handler.py` | 위협 정보 보강 Lambda |
| `tests/backend/test_threat_intelligence.py` | 위협 인텔리전스 테스트 (7개) |

### 구현 전략

**3.1. ThreatIntelligence 클래스**

```python
class ThreatIntelligence:
    def __init__(self, cve_db, ip_reputation, cache):
        self.cve = cve_db
        self.ip_rep = ip_reputation
        self.cache = cache
    
    async def enrich_threat(self, threat):
        """
        탐지된 위협에 외부 정보 추가
        
        반환: {
            'original_threat': {...},
            'cve_matches': [...],
            'malicious_ips': [...],
            'threat_level_adjusted': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
            'confidence_score': float
        }
        """
        enriched = {
            'original_threat': threat,
            'cve_matches': [],
            'malicious_ips': [],
            'threat_level_adjusted': threat.severity,
            'confidence_score': 1.0
        }
        
        # 1. CVE 확인
        if threat.has_version_info():
            cves = await self.cve.find_matching_cves(threat.software, threat.version)
            enriched['cve_matches'] = cves
            
            if cves:
                enriched['threat_level_adjusted'] = 'CRITICAL'
                enriched['confidence_score'] = min(1.0, 1.0 + 0.2 * len(cves))
        
        # 2. IP 평판 확인
        if threat.has_source_ip():
            ip_rep = await self.ip_rep.check_reputation(threat.source_ip)
            if ip_rep['is_malicious']:
                enriched['malicious_ips'].append(ip_rep)
                enriched['threat_level_adjusted'] = 'CRITICAL'
                enriched['confidence_score'] = min(1.0, enriched['confidence_score'] + 0.3)
        
        return enriched
    
    async def batch_enrich(self, threats):
        """여러 위협 동시 보강 (병렬 처리)"""
        tasks = [self.enrich_threat(t) for t in threats]
        return await asyncio.gather(*tasks)
```

**3.2. CVE 체커**

```python
class CVEChecker:
    async def find_matching_cves(self, software, version):
        """
        소프트웨어 → 해당 CVE 목록 조회
        
        반환: [
            {
                'cve_id': 'CVE-2024-12345',
                'severity': 'CRITICAL',
                'cvss_score': 9.8,
                'description': '...',
                'published_date': '2024-01-01'
            }
        ]
        """
        
        # 캐시 확인
        cache_key = f"cve:{software}:{version}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # NVD(National Vulnerability Database) API 조회
        cves = await self._query_nvd(software, version)
        
        # 캐시 저장 (7일)
        await self._set_cache(cache_key, cves, ttl=7*24*3600)
        
        return cves
    
    async def _query_nvd(self, software, version):
        """NVD REST API 호출"""
        # https://services.nvd.nist.gov/rest/json/cves/2.0
```

**3.3. IP 평판 조회**

```python
class IPReputation:
    def __init__(self, abuseipdb_api_key):
        self.api_key = abuseipdb_api_key
    
    async def check_reputation(self, ip_address):
        """
        IP 평판 조회 (AbuseIPDB)
        
        반환: {
            'ip': str,
            'is_malicious': bool,
            'abuse_score': int (0-100),
            'threat_types': [str],
            'last_reported': str
        }
        """
        
        # 캐시 확인 (24시간)
        cache_key = f"ip_rep:{ip_address}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # AbuseIPDB API 호출
        response = await self._query_abuseipdb(ip_address)
        
        # 결과 정규화
        result = {
            'ip': ip_address,
            'is_malicious': response['abuseConfidenceScore'] > 25,
            'abuse_score': response['abuseConfidenceScore'],
            'threat_types': response['usageType'],
            'last_reported': response['lastReportedAt']
        }
        
        # 캐시 저장 (24시간)
        await self._set_cache(cache_key, result, ttl=24*3600)
        
        return result
```

### 테스트 케이스 (7개)

| # | 테스트 | 기대 결과 |
|---|--------|---------|
| 1 | `test_enrich_threat_with_cve` | 위협 + CVE 데이터 → 보강됨 |
| 2 | `test_enrich_threat_with_ip_rep` | 위협 + IP 평판 → 보강됨 |
| 3 | `test_cve_cache` | CVE 조회 → 캐시 저장/재사용 |
| 4 | `test_ip_reputation_cache` | IP 조회 → 캐시 저장/재사용 |
| 5 | `test_batch_enrich_parallel` | 여러 위협 동시 보강 → 병렬 처리 |
| 6 | `test_threat_level_upgrade_cve` | CVE 매칭 → 위협도 CRITICAL로 상향 |
| 7 | `test_threat_level_upgrade_malicious_ip` | 악성 IP 매칭 → 위협도 CRITICAL로 상향 |

---

## Phase 4: 파이프라인 오케스트레이터

### 목표
위협 탐지부터 피드백 수집까지 전체 파이프라인의 상태를 모니터링하고 최적화합니다.

### 구현 파일

| 파일 | 내용 |
|------|------|
| `lambda/guardian/orchestration/pipeline_orchestrator.py` | PipelineOrchestrator 클래스 |
| `lambda/guardian/orchestration/pipeline_metrics.py` | 파이프라인 메트릭 수집 |
| `lambda/guardian/handlers/health_check_handler.py` | 파이프라인 상태 체크 Lambda |
| `apps/web/src/components/Dashboard/PipelineHealthPanel.tsx` | 파이프라인 상태 UI |
| `tests/backend/test_pipeline_orchestration.py` | 파이프라인 테스트 (7개) |
| `tests/frontend/test_pipeline_health_panel.tsx` | UI 테스트 (2개) |

### 구현 전략

**4.1. PipelineOrchestrator**

```python
class PipelineOrchestrator:
    def __init__(self, anomaly_detector, predictor, playbook_mapper, 
                 action_executor, feedback_engine, retrainer):
        self.stages = {
            'anomaly_detection': anomaly_detector,
            'prediction': predictor,
            'playbook_mapping': playbook_mapper,
            'action_execution': action_executor,
            'feedback_collection': feedback_engine,
            'model_retraining': retrainer
        }
        self.metrics = PipelineMetrics()
    
    async def orchestrate(self, account_id):
        """
        전체 파이프라인 실행 (각 단계 모니터링)
        
        반환: {
            'pipeline_id': str,
            'status': 'HEALTHY' | 'DEGRADED' | 'FAILED',
            'stages': {
                'anomaly_detection': {...},
                'prediction': {...},
                'playbook_mapping': {...},
                'action_execution': {...},
                'feedback_collection': {...},
                'model_retraining': {...}
            },
            'end_to_end_latency_ms': float,
            'errors': [str]
        }
        """
        
        pipeline_id = str(uuid.uuid4())
        stage_results = {}
        errors = []
        
        # 1. 이상 탐지
        start = time.time()
        try:
            threats = await self.stages['anomaly_detection'].detect(account_id)
            stage_results['anomaly_detection'] = {
                'status': 'SUCCESS',
                'threats_detected': len(threats),
                'latency_ms': (time.time() - start) * 1000
            }
        except Exception as e:
            errors.append(f"Anomaly detection failed: {e}")
            stage_results['anomaly_detection'] = {'status': 'FAILED', 'error': str(e)}
        
        # 2. ML 예측
        if threats:
            start = time.time()
            try:
                predictions = await self.stages['prediction'].predict_batch(threats)
                stage_results['prediction'] = {
                    'status': 'SUCCESS',
                    'predictions_made': len(predictions),
                    'latency_ms': (time.time() - start) * 1000
                }
            except Exception as e:
                errors.append(f"Prediction failed: {e}")
                stage_results['prediction'] = {'status': 'FAILED', 'error': str(e)}
        
        # 3-6단계 계속...
        
        # 파이프라인 상태 결정
        status = self._determine_pipeline_status(stage_results, errors)
        
        # 메트릭 저장
        await self.metrics.record_pipeline_execution({
            'pipeline_id': pipeline_id,
            'status': status,
            'stage_results': stage_results,
            'errors': errors
        })
        
        return {
            'pipeline_id': pipeline_id,
            'status': status,
            'stages': stage_results,
            'errors': errors
        }
    
    def _determine_pipeline_status(self, stage_results, errors):
        """파이프라인 상태 결정"""
        failed_stages = sum(1 for r in stage_results.values() if r['status'] == 'FAILED')
        
        if failed_stages == 0:
            return 'HEALTHY'
        elif failed_stages <= 2:
            return 'DEGRADED'
        else:
            return 'FAILED'
```

**4.2. 파이프라인 메트릭**

```python
class PipelineMetrics:
    def __init__(self, dynamodb_table):
        self.table = dynamodb_table
    
    async def get_pipeline_health(self, lookback_minutes=60):
        """
        최근 1시간 파이프라인 상태 통계
        
        반환: {
            'total_executions': int,
            'successful_executions': int,
            'failed_executions': int,
            'success_rate': float,
            'avg_e2e_latency_ms': float,
            'stage_success_rates': {
                'anomaly_detection': float,
                'prediction': float,
                ...
            },
            'error_summary': {
                'error_type': int,
                ...
            }
        }
        """
        
        # 최근 기록 조회
        executions = await self.table.query_recent(lookback_minutes=lookback_minutes)
        
        total = len(executions)
        successful = sum(1 for e in executions if e['status'] == 'HEALTHY')
        
        return {
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': total - successful,
            'success_rate': successful / total if total > 0 else 0,
            'avg_e2e_latency_ms': self._calculate_avg_latency(executions),
            'stage_success_rates': self._calculate_stage_success_rates(executions),
            'error_summary': self._summarize_errors(executions)
        }
```

### 테스트 케이스 (9개)

| # | 테스트 | 기대 결과 |
|---|--------|---------|
| 1 | `test_pipeline_orchestration_full_path` | 모든 단계 정상 실행 → HEALTHY |
| 2 | `test_pipeline_one_stage_failure` | 1개 단계 실패 → DEGRADED |
| 3 | `test_pipeline_multiple_failures` | 3개 이상 단계 실패 → FAILED |
| 4 | `test_pipeline_latency_tracking` | 각 단계 지연 시간 기록 |
| 5 | `test_pipeline_error_logging` | 에러 메시지 정상 저장 |
| 6 | `test_pipeline_health_calculation` | 성공률 계산 정확 |
| 7 | `test_pipeline_stage_success_rates` | 각 단계별 성공률 계산 |
| 8 | `test_pipeline_health_panel_display` | 대시보드 패널에 정상 표시 |
| 9 | `test_pipeline_anomaly_detection` | 성공률 급락 감지 → 알림 발송 |

---

## 구현 순서 및 테스트

| Phase | 단계 | 백엔드 | 프론트 | 합계 |
|-------|------|--------|--------|------|
| 1 | 모델 재학습 | 8 | - | 8 |
| 2 | 실시간 대시보드 | 8 | 3 | 11 |
| 3 | 위협 인텔리전스 | 7 | - | 7 |
| 4 | 파이프라인 오케스트레이터 | 7 | 2 | 9 |
| **합계** | **Sprint 61** | **30** | **5** | **35** |

**누적 테스트:**
- Sprint 60: 33 테스트 PASS
- Sprint 59: 30 테스트 PASS
- Sprint 58: 26 테스트 PASS
- Sprint 61: 35 테스트 PASS (예정)
- **총합: 124 테스트**

---

## 기술 스택 (Sprint 61)

| 레이어 | 기술 |
|--------|------|
| 머신러닝 | scikit-learn (증분 학습, 특성 공학) |
| 실시간 통신 | WebSocket (API Gateway + Lambda) |
| 외부 API | NVD REST (CVE), AbuseIPDB (IP 평판) |
| 캐싱 | Redis / ElastiCache (CVE, IP 평판 캐시) |
| 메트릭 수집 | CloudWatch + DynamoDB |
| 백엔드 | Python Lambda |
| 프론트엔드 | React 19 + Next.js 16 + WebSocket |
| UI | Tailwind CSS v4 + Lucide React |
| 테스트 | pytest (백엔드), Jest (프론트엔드) |

---

## 아키텍처 흐름

```
위협 탐지 (매 1시간)
    ↓
[PipelineOrchestrator 시작]
    ├─ Stage 1: 이상 탐지 (AnomalyDetector)
    │   ├─ EC2 / S3 / 비용 체크
    │   └─ 위협 목록 반환
    │
    ├─ Stage 2: ML 예측 (Predictor)
    │   ├─ 각 위협 심각도 예측
    │   └─ 예측 신뢰도 반환
    │
    ├─ Stage 3: 플레이북 매핑 (PlaybookMapper)
    │   ├─ 위협 유형별 최적 플레이북 선택
    │   └─ 플레이북 목록 반환
    │
    ├─ Stage 4: 작업 실행 (ActionExecutor) → [실시간 업데이트]
    │   ├─ 플레이북의 각 작업 실행
    │   └─ 결과 기록
    │
    ├─ Stage 5: 피드백 수집 (FeedbackEngine)
    │   ├─ 사용자 입력 / 자동 평가
    │   └─ 피드백 저장
    │
    └─ Stage 6: 모델 재학습 (ModelRetrainer) [매주 실행]
        ├─ 피드백 데이터 수집 (지난 30일)
        ├─ 특성 공학 (FeatureEngineer)
        ├─ 모델 재학습 (증분 학습)
        └─ 자동 배포 (개선도 > 2%)

[동시 진행]
위협 보강 (ThreatIntelligence)
    ├─ CVE 조회 (CVEChecker)
    ├─ IP 평판 조회 (IPReputation)
    └─ 위협도 상향 (CRITICAL)

[실시간 대시보드]
WebSocket 브로드캐스트
    ├─ 위협 탐지 → 즉시 전송
    ├─ 작업 실행 → 즉시 전송
    ├─ 피드백 → 정확도 수치 업데이트
    └─ 파이프라인 상태 → 실시간 표시

[모니터링]
파이프라인 상태 체크 (매 시간)
    ├─ 각 단계 성공률 계산
    ├─ 엔드-투-엔드 지연 시간 측정
    ├─ 에러 요약 생성
    └─ 대시보드에 실시간 표시
```

---

## 주요 설계 결정

### 1. 모델 재학습 전략
- **증분 학습**: 메모리 효율성 (새 데이터만 학습)
- **자동 배포**: 개선도 > 2% 시 자동 배포
- **주간 스케줄**: 일요일 00:00 UTC (트래픽 낮은 시간)

### 2. 실시간 대시보드 아키텍처
- **WebSocket**: 즉시성 (지연 < 100ms)
- **브로드캐스트**: 모든 클라이언트에 동시 전송
- **자동 재연결**: 네트워크 끊김 시 자동 복구

### 3. 위협 인텔리전스 캐싱
- **CVE**: 7일 캐시 (변화 낮음)
- **IP 평판**: 24시간 캐시 (변화 높음)
- **Redis/ElastiCache**: 빠른 조회 (API 비용 절감)

### 4. 파이프라인 모니터링
- **3단계 상태 모델**: HEALTHY / DEGRADED / FAILED
- **자동 알림**: 상태 악화 시 즉시 알림
- **성공률 추적**: 각 단계별로 별도 모니터링

---

## 검증 체크리스트

### Phase 1: 모델 재학습
- [ ] FeatureEngineer 클래스 구현
- [ ] ModelRetrainer 클래스 구현
- [ ] 재학습 Lambda 핸들러 구현
- [ ] EventBridge 스케줄 설정 (매주 일요일)
- [ ] 8개 테스트 모두 PASS

### Phase 2: WebSocket 실시간 대시보드
- [ ] DashboardBroadcaster 클래스 구현
- [ ] WebSocket Lambda 핸들러 구현
- [ ] useRealtimeDashboard Hook 구현
- [ ] RealtimeThreatFeed UI 컴포넌트 구현
- [ ] 11개 테스트 모두 PASS

### Phase 3: 위협 인텔리전스
- [ ] ThreatIntelligence 클래스 구현
- [ ] CVEChecker 클래스 구현
- [ ] IPReputation 클래스 구현
- [ ] 캐싱 로직 구현
- [ ] 7개 테스트 모두 PASS

### Phase 4: 파이프라인 오케스트레이터
- [ ] PipelineOrchestrator 클래스 구현
- [ ] PipelineMetrics 클래스 구현
- [ ] HealthCheck Lambda 핸들러 구현
- [ ] PipelineHealthPanel UI 컴포넌트 구현
- [ ] 9개 테스트 모두 PASS

### 최종 검증
- [ ] 35개 테스트 모두 PASS
- [ ] 전체 누적: 124 테스트 (Sprint 58-61)
- [ ] Git 커밋: "feat: Sprint 61 - Advanced Learning & Real-time Dashboard"
- [ ] 문서 업데이트

---

## 성능 목표

| 메트릭 | 목표 |
|--------|------|
| 모델 재학습 시간 | < 5분 (30일 피드백 처리) |
| WebSocket 지연 | < 100ms |
| 위협 보강 시간 | < 500ms (CVE + IP 평판) |
| 파이프라인 엔드-투-엔드 | < 2분 (모든 단계) |
| API 캐시 히트율 | > 80% (CVE, IP) |

---

## 다음 단계 (Sprint 62+)

### Sprint 62: 자동 대응 고도화
- 더 많은 작업 타입 지원 (CloudTrail 기반)
- 비용 최적화 자동화 (Reserved Instance 추천)
- 보험 통합 (자동 대응 비용 청구)

### Sprint 63: 멀티 계정 확장
- 여러 AWS 계정 동시 감시
- 계정별 대시보드 분리
- 교차 계정 위협 상관관계 분석

### Sprint 64: 고급 분석
- 이상 탐지 → 루트 원인 분석
- 예측 모델 설명성 개선 (SHAP, LIME)
- 자동화 ROI 분석
