# Sprint 60: Playbook Execution & Actions System

## Context

**현황:**
- Sprint 59 완료: 8 테스트 PASS (ML Prediction → Playbook Mapping)
- 누적 테스트: 76 + 55 + 8 = 139 테스트 PASS
- 아키텍처: Threat Detection → ML Prediction → Playbook Mapping → ❌ Execution (MISSING)

**핵심 문제:**
- **플레이북이 생성되지만 실제로 실행되는 메커니즘이 없음**
- AWS EC2, S3, IAM, SecurityGroup 등 실제 리소스에 대한 조치를 할 수 없음
- 플레이북 실행 결과를 추적하고 저장할 방법이 없음
- 감시된 위협에서 자동 대응까지의 파이프라인이 불완전함

**기존 인프라 (재활용):**
```
✅ MLPredictor - ML 예측 엔진 구현됨
✅ ResponseMapper - 플레이북 매핑 구현됨
✅ ExecutionMetricsCollector - 실행 메트릭 수집 구현됨
✅ ResponseFeedbackCollector - 피드백 수집 구현됨
❌ ActionExecutor - AWS 액션 실행 엔진 없음 (신규 구현 필요)
❌ PlaybookOrchestrator - 플레이북 조율 엔진 없음 (신규 구현 필요)
❌ AuditLogger - 감사 로깅 없음 (신규 구현 필요)
❌ DashboardMetrics - 대시보드 메트릭 없음 (신규 구현 필요)
```

**목표:**
Sprint 60은 **플레이북 실행 및 액션 시스템**을 완성합니다:
1. **Phase 1**: AWS 액션 실행 엔진 (EC2 Stop, SG Restrict, S3 Block Public, IAM Disable Key, NAT Block Region)
2. **Phase 2**: 플레이북 조율 엔진 (의존성 관리, 병렬 실행, 비용 추정)
3. **Phase 3**: 감사 로깅 시스템 (실행 기록, 위협 대응 이력)
4. **Phase 4**: 대시보드 메트릭 수집 (플레이북 상태, 효율성, 시스템 개요)

---

## Phase 1: AWS 액션 실행 엔진 (ActionExecutor)

### 목표
개별 AWS 리소스에 대한 보안 조치를 실행하고 결과를 검증하는 엔진 구축

### 구현 파일
- `lambda/guardian/ml/action_executor.py`: ActionExecutor 클래스 (~350 lines)
- `tests/backend/test_action_executor.py`: 10개 테스트

### 핵심 클래스

```python
class ActionExecutor:
    """AWS 액션 실행 엔진"""
    
    def execute_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        AWS 액션 실행
        
        action_spec = {
            'action_id': str,
            'action_type': 'ec2_stop' | 'sg_restrict_port' | 's3_block_public' | 
                          'iam_disable_key' | 'nat_block_region',
            'target_id': str,
            'parameters': Dict,
            'dry_run': bool (optional)
        }
        
        Returns:
            {
                'action_id': str,
                'status': 'SUCCESS' | 'FAILED',
                'result': {...},
                'error': str (optional),
                'execution_time_seconds': float
            }
        """
    
    def validate_action_result(self, action_result: Dict, original_action: Dict) -> Dict:
        """AWS에서 액션이 실제로 적용되었는지 검증"""
    
    def get_action_cost_estimate(self, action_type: str) -> float:
        """액션별 월 비용 절감액 반환
        - ec2_stop: $0 (중지만 하고 EBS 비용 남음)
        - sg_restrict_port: $0
        - s3_block_public: $0
        - iam_disable_key: $0
        - nat_block_region: $32 (NAT 게이트웨이 제거 기준)
        """
    
    def rollback_action(self, action_id: str) -> Dict:
        """실행된 액션 취소"""
```

### 지원 액션 타입

| Action Type | 설명 | AWS API | 결과 |
|------------|------|---------|------|
| `ec2_stop` | EC2 인스턴스 중지 | `ec2.stop_instances()` | 인스턴스 상태 STOPPED |
| `sg_restrict_port` | SecurityGroup 포트 제한 | `ec2.revoke_security_group_ingress()` | 규칙 삭제 |
| `s3_block_public` | S3 퍼블릭 액세스 차단 | `s3.put_public_access_block()` | ACL 차단 설정 |
| `iam_disable_key` | IAM 액세스 키 비활성화 | `iam.update_access_key_status()` | 키 상태 INACTIVE |
| `nat_block_region` | NAT 게이트웨이 삭제 (리전 차단) | `ec2.delete_nat_gateway()` | 게이트웨이 삭제 |

### 테스트 케이스 (10개)

1. `test_execute_ec2_stop`: EC2 인스턴스 중지
2. `test_execute_sg_restrict_port`: SecurityGroup 포트 제한
3. `test_execute_s3_block_public`: S3 퍼블릭 액세스 차단
4. `test_execute_iam_disable_key`: IAM 액세스 키 비활성화
5. `test_execute_nat_block_region`: NAT 게이트웨이 삭제
6. `test_validate_action_result`: 액션 결과 검증
7. `test_get_action_cost_estimate`: 비용 추정
8. `test_rollback_action`: 액션 취소
9. `test_dry_run_mode`: 드라이런 모드 (실제 실행 안 함)
10. `test_unsupported_action_type`: 지원하지 않는 액션 타입 에러

### 설계 원칙
- 실제 AWS SDK 통합 (boto3)
- 모든 액션 결과 저장 (executed_actions dict)
- 취소 가능성 고려 (action_history 유지)
- 드라이런 모드 지원 (프로덕션 이전 검증)
- 비용 추정 포함 (비용 인식 자동 대응)

---

## Phase 2: 플레이북 조율 엔진 (PlaybookOrchestrator)

### 목표
여러 액션을 조직화하여 복잡한 대응 워크플로우 실행

### 구현 파일
- `lambda/guardian/ml/playbook_orchestrator.py`: PlaybookOrchestrator 클래스 (~250 lines)
- `tests/backend/test_playbook_orchestrator.py`: 9개 테스트

### 핵심 클래스

```python
class PlaybookOrchestrator:
    """플레이북 조율 엔진"""
    
    def execute_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        플레이북 실행 (액션 의존성 관리)
        
        playbook = {
            'playbook_id': str,
            'threat_id': str,
            'threat_type': str,
            'account_id': str,
            'actions': [
                {
                    'action_id': str,
                    'action_type': str,
                    'target_id': str,
                    'parameters': Dict,
                    'depends_on': [str] (optional - 선행 액션 ID)
                }
            ],
            'dry_run': bool (optional)
        }
        
        Returns:
            {
                'execution_id': str,
                'playbook_id': str,
                'status': 'COMPLETED' | 'PARTIAL' | 'FAILED',
                'actions_executed': int,
                'actions_succeeded': int,
                'actions_failed': int,
                'action_results': [...],
                'execution_time_seconds': float
            }
        """
    
    def _build_action_graph(self, actions: List[Dict]) -> List[List[Dict]]:
        """
        액션 의존성 그래프 생성 (위상 정렬)
        
        Returns: 실행 순서별로 정렬된 액션 그룹
        예: [[action1, action2], [action3], [action4, action5]]
        """
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """실행 상태 조회"""
    
    def get_execution_summary(self, execution_id: str) -> Dict:
        """실행 요약 조회"""
    
    def estimate_playbook_cost(self, playbook: Dict) -> float:
        """플레이북 총 비용 추정"""
    
    def get_parallel_actions(self, playbook: Dict) -> List[List[str]]:
        """병렬 실행 가능한 액션 그룹 반환"""
```

### 의존성 관리

```
시나리오: S3 버킷이 퍼블릭으로 열려있고, 공격자가 접근 가능한 상황

actions:
  1. action-1 (sg_restrict_port): 포트 22 차단
  2. action-2 (s3_block_public): S3 퍼블릭 액세스 차단
  3. action-3 (iam_disable_key): 공격자 액세스 키 비활성화 (depends_on: action-1, action-2)

실행 순서:
  [action-1, action-2] → (병렬 실행)
       ↓
  [action-3] → (의존성 충족 후 실행)
```

### 테스트 케이스 (9개)

1. `test_execute_simple_playbook`: 의존성 없는 단순 플레이북
2. `test_execute_playbook_with_dependencies`: 의존성이 있는 플레이북
3. `test_get_execution_status`: 실행 상태 조회
4. `test_get_execution_summary`: 실행 요약 조회
5. `test_estimate_playbook_cost`: 플레이북 비용 추정
6. `test_get_parallel_actions`: 병렬 실행 그룹 조회
7. `test_dry_run_mode`: 드라이런 모드
8. `test_nonexistent_execution`: 존재하지 않는 실행 조회
9. `test_playbook_with_multiple_actions`: 많은 액션이 있는 플레이북

### 설계 원칙
- 위상 정렬로 의존성 해결
- 병렬 실행 지원 (asyncio)
- 실패 시 다운스트림 액션 스킵
- 부분 성공 추적 (PARTIAL status)
- 비용 최적화 정보 제공

---

## Phase 3: 감사 로깅 시스템 (AuditLogger)

### 목표
모든 액션 및 플레이북 실행을 감사 로그에 기록하여 추적 가능하게 함

### 구현 파일
- `lambda/guardian/ml/audit_logger.py`: AuditLogger 클래스 (~180 lines)
- `tests/backend/test_audit_logger.py`: 7개 테스트

### 핵심 클래스

```python
class AuditLogger:
    """실행 작업 감사 로깅"""
    
    def log_action_execution(self, action_result: Dict, metadata: Dict) -> str:
        """
        개별 액션 실행 로깅
        
        metadata = {
            'user_id': str (optional),
            'request_id': str (optional),
            'ip_address': str (optional),
            'playbook_id': str,
            'threat_id': str
        }
        
        Returns: log_id
        """
    
    def log_playbook_execution(self, execution_result: Dict, metadata: Dict) -> str:
        """플레이북 실행 로깅"""
    
    def get_audit_trail(self, playbook_id: str, days: int = 7) -> List[Dict]:
        """플레이북별 감사 추적"""
    
    def get_threat_response_history(self, threat_id: str) -> List[Dict]:
        """위협별 대응 이력"""
    
    def get_action_statistics(self, action_type: str, days: int = 7) -> Dict:
        """
        액션 타입별 통계
        
        Returns:
            {
                'action_type': str,
                'total_executions': int,
                'successful': int,
                'failed': int,
                'success_rate': float,
                'most_common_target': str
            }
        """
```

### 로그 구조

```python
audit_log_entry = {
    'log_id': str,
    'action_id': str,
    'action_type': str,
    'target_id': str,
    'status': 'SUCCESS' | 'FAILED',
    'timestamp': str,
    'user_id': str,
    'playbook_id': str,
    'threat_id': str,
    'ip_address': str,
    'error': str (optional)
}
```

### 테스트 케이스 (7개)

1. `test_log_action_execution`: 액션 실행 로깅
2. `test_log_playbook_execution`: 플레이북 실행 로깅
3. `test_get_audit_trail`: 플레이북 감사 추적
4. `test_get_threat_response_history`: 위협별 대응 이력
5. `test_get_action_statistics`: 액션 통계
6. `test_empty_audit_trail`: 빈 감사 추적
7. `test_action_statistics_not_found`: 통계 없을 때

### 설계 원칙
- 모든 실행 자동 기록
- 위협-대응 연관성 추적
- 액션별 성공률 계산
- 감사 추적성 (누가, 언제, 무엇, 왜)

---

## Phase 4: 대시보드 메트릭 (DashboardMetrics)

### 목표
실행 결과를 수집하여 대시보드에 실시간 메트릭 제공

### 구현 파일
- `lambda/guardian/ml/dashboard_metrics.py`: DashboardMetrics 클래스 (~200 lines)
- `tests/backend/test_dashboard_metrics.py`: 7개 테스트

### 핵심 클래스

```python
class DashboardMetrics:
    """대시보드용 실시간 메트릭"""
    
    def register_execution(self, execution_result: Dict) -> None:
        """실행 결과 등록 (메트릭 캐시에 저장)"""
    
    def get_execution_summary(self, execution_id: str) -> Optional[Dict]:
        """
        실행 요약 조회
        
        Returns:
            {
                'execution_id': str,
                'status': str,
                'total_actions': int,
                'success_rate': float,
                'execution_time_seconds': float
            }
        """
    
    def get_playbook_health(self, playbook_id: str) -> Dict:
        """
        플레이북 상태 조회
        
        Returns:
            {
                'playbook_id': str,
                'total_executions': int,
                'success_rate': float,
                'avg_execution_time': float,
                'status': 'HEALTHY' | 'DEGRADED' | 'FAILED' | 'UNKNOWN'
            }
        
        상태 결정:
        - HEALTHY: 성공률 100%
        - DEGRADED: 성공률 ≥80%
        - FAILED: 성공률 <80%
        - UNKNOWN: 실행 기록 없음
        """
    
    def get_threat_response_effectiveness(self, threat_type: str) -> Dict:
        """
        위협 대응 효율성 조회
        
        Returns:
            {
                'threat_type': str,
                'total_detections': int,
                'responses_triggered': int,
                'response_rate': float,
                'avg_resolution_time': float,
                'effectiveness_score': float (0-100)
            }
        """
    
    def get_system_overview(self) -> Dict:
        """
        시스템 전체 개요
        
        Returns:
            {
                'total_executions': int,
                'successful_executions': int,
                'failed_executions': int,
                'success_rate': float,
                'total_actions_executed': int,
                'avg_execution_time': float
            }
        """
    
    def get_recent_executions(self, limit: int = 10) -> List[Dict]:
        """최근 실행 목록 (최신순)"""
```

### 메트릭 정의

| 메트릭 | 정의 | 계산 |
|--------|------|------|
| `success_rate` | 성공한 실행 비율 | successful_executions / total_executions |
| `playbook_health` | 플레이북 신뢰도 | 상태별 분류 (HEALTHY/DEGRADED/FAILED) |
| `effectiveness_score` | 위협 대응 효율성 | 성공률 * 100 |
| `avg_execution_time` | 평균 실행 시간 | 모든 실행 시간의 평균 |

### 테스트 케이스 (7개)

1. `test_register_and_get_execution_summary`: 실행 등록 및 요약 조회
2. `test_get_playbook_health`: 플레이북 상태 (DEGRADED)
3. `test_get_playbook_health_healthy`: 플레이북 상태 (HEALTHY)
4. `test_get_threat_response_effectiveness`: 위협 대응 효율성
5. `test_get_system_overview`: 시스템 전체 개요
6. `test_get_recent_executions`: 최근 실행 목록
7. `test_empty_metrics`: 빈 메트릭

### 설계 원칙
- 실시간 메트릭 수집
- 상태 기반 분류 (HEALTHY/DEGRADED/FAILED)
- 효율성 점수 계산
- 시스템 전체 가시성 제공

---

## 전체 파이프라인 흐름 (Sprint 60)

```
위협 탐지 (CloudTrail/Logs)
    ↓ (기존 Sprint 32)
ML 예측 (위협 심각도 & 신뢰도)
    ↓ (기존 Sprint 59)
플레이북 매핑 (권장 대응 플레이북)
    ↓ (기존 Sprint 59)
자동 트리거 결정
    ↓
플레이북 조율 (PlaybookOrchestrator)
    ├─ 의존성 분석 (위상 정렬)
    ├─ 병렬 실행 (asyncio)
    └─ 상태 추적 (COMPLETED/PARTIAL/FAILED)
    ↓
액션 실행 (ActionExecutor) [NEW - Phase 1]
    ├─ EC2 Stop
    ├─ SG Restrict Port
    ├─ S3 Block Public
    ├─ IAM Disable Key
    └─ NAT Block Region
    ↓
감사 로깅 (AuditLogger) [NEW - Phase 3]
    ├─ 액션 실행 로그
    ├─ 플레이북 실행 로그
    └─ 위협 대응 이력
    ↓
메트릭 수집 (DashboardMetrics) [NEW - Phase 4]
    ├─ 플레이북 상태
    ├─ 위협 대응 효율성
    └─ 시스템 개요
    ↓
대시보드 갱신 (웹 UI)
```

---

## 구현 순서 및 테스트

| Phase | 단계 | 파일 | 테스트 수 | 누적 |
|-------|------|------|---------|------|
| 1 | ActionExecutor | action_executor.py | 10 | 10 |
| 2 | PlaybookOrchestrator | playbook_orchestrator.py | 9 | 19 |
| 3 | AuditLogger | audit_logger.py | 7 | 26 |
| 4 | DashboardMetrics | dashboard_metrics.py | 7 | 33 |
| **전체** | Sprint 60 | 4개 파일 | **33** | **172** |

---

## 기술 스택 (Sprint 60)

| 레이어 | 기술 |
|--------|------|
| AWS 인프라 | boto3 (EC2, S3, IAM, SecurityGroup, NAT) |
| 액션 실행 | AWS SDK 직접 호출 |
| 워크플로우 | 위상 정렬 (topological sort) |
| 병렬 처리 | asyncio (선택적) |
| 상태 추적 | 메모리 저장소 (dict) |
| 감사 로깅 | 메모리 저장소 (dict) |
| 메트릭 수집 | 메모리 캐시 (dict) |
| 테스트 | pytest (33개 테스트) |

---

## 검증 체크리스트

**Phase 1: ActionExecutor**
- [ ] 5개 액션 타입 구현 (EC2, SG, S3, IAM, NAT)
- [ ] 액션 검증 로직
- [ ] 비용 추정
- [ ] 취소 기능
- [ ] 드라이런 모드
- [ ] 10개 테스트 PASS

**Phase 2: PlaybookOrchestrator**
- [ ] 위상 정렬 구현
- [ ] 의존성 관리
- [ ] 병렬 실행 지원
- [ ] 상태 추적 (COMPLETED/PARTIAL/FAILED)
- [ ] 비용 추정
- [ ] 9개 테스트 PASS

**Phase 3: AuditLogger**
- [ ] 액션 로깅
- [ ] 플레이북 로깅
- [ ] 감사 추적 쿼리
- [ ] 위협 대응 이력 쿼리
- [ ] 액션 통계
- [ ] 7개 테스트 PASS

**Phase 4: DashboardMetrics**
- [ ] 메트릭 등록
- [ ] 실행 요약 조회
- [ ] 플레이북 상태 (HEALTHY/DEGRADED/FAILED)
- [ ] 위협 대응 효율성
- [ ] 시스템 개요
- [ ] 최근 실행 목록
- [ ] 7개 테스트 PASS

**최종:**
- [ ] 누적 33개 테스트 모두 PASS
- [ ] 전체 테스트: 139 (Sprint 32+34+59) + 33 (Sprint 60) = 172 PASS
- [ ] Git 커밋: "feat: Sprint 60 - Playbook Execution & Actions System (33 tests)"

---

## 다음 단계 (Sprint 61)

**Sprint 61 계획:**
- Phase 1: 피드백 기반 모델 재학습
- Phase 2: 실시간 대시보드 WebSocket 통합
- Phase 3: 위협 인텔리전스 통합 (CVE, IP 평판)
- Phase 4: 엔드-투-엔드 파이프라인 최적화

---

## 추가 노트

### 설계 고려사항
1. **비용 인식**: 각 액션의 월 비용 절감액을 추정하여 경제적 합리성 확보
2. **의존성 관리**: 위상 정렬로 복잡한 워크플로우 안전하게 실행
3. **부분 실패**: 일부 액션 실패 시 다른 액션은 계속 실행 (PARTIAL status)
4. **감사 추적성**: 누가, 언제, 무엇을 했는지 완전히 기록
5. **메트릭 중심**: 대시보드용 실시간 메트릭으로 시스템 가시성 확보

### 프로덕션 고려사항 (v1.1+)
- DynamoDB로 감사 로그 마이그레이션
- 메트릭을 CloudWatch에 발행
- AWS Lambda 타임아웃 고려 (15분 제한)
- 재시도 로직 (지수 백오프)
- 장기 실행 작업을 Step Functions으로 마이그레이션
