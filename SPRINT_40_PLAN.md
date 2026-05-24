# Sprint 40: 자동 리소스 정리 및 비용 절감 자동화

## 현황

**완료된 Sprints:**
- Sprint 32-39: 357 테스트 PASS ✅

**Sprint 40 목표:**
자동 리소스 정리와 비용 절감을 자동으로 실행하는 시스템을 구축합니다.

**4개 Phase로 구성:**
1. **Phase 1**: 자동 정리 엔진 (12 테스트)
2. **Phase 2**: 스냅샷/볼륨 정리 자동화 (10 테스트)
3. **Phase 3**: EC2 생명주기 관리 (12 테스트)
4. **Phase 4**: 자동 대응 결과 추적 (10 테스트)

**총 44 테스트**

---

## Phase 1: 자동 정리 엔진 (12 테스트)

### 1.1 AutoCleanupEngine 클래스
```python
class AutoCleanupEngine:
    def __init__(self, ec2_client, s3_client, dynamodb_table):
        pass
    
    def identify_cleanup_targets(self, account_id: str) -> List[Dict]:
        """
        정리 대상 리소스 식별
        - 미사용 EBS 볼륨 (unattached, 30일 이상)
        - 미사용 스냅샷 (90일 이상)
        - 미할당 탄력적 IP
        - 빈 보안 그룹
        - 중지된 EC2 (30일 이상)
        """
    
    def execute_cleanup(self, resource_id: str, resource_type: str, dry_run: bool = True) -> Dict:
        """
        리소스 정리 실행
        dry_run=True: 미리보기만, False: 실제 삭제
        """
    
    def schedule_cleanup_job(self, account_id: str, schedule: str) -> str:
        """
        정기적 정리 작업 스케줄링
        schedule: 'daily', 'weekly', 'monthly'
        """
    
    def get_cleanup_history(self, account_id: str, days: int = 30) -> List[Dict]:
        """정리 작업 이력 조회"""
```

### 1.2 테스트 그룹
- Cleanup Target Identification (2 테스트)
- Resource Deletion (2 테스트)
- Dry-Run Simulation (2 테스트)
- Cleanup Scheduling (2 테스트)
- History Tracking (2 테스트)
- Error Handling (2 테스트)

---

## Phase 2: 스냅샷/볼륨 정리 (10 테스트)

### 2.1 StorageCleanupManager 클래스
```python
class StorageCleanupManager:
    def delete_unattached_volumes(self, account_id: str, dry_run: bool = True) -> Dict:
        """미연결 볼륨 삭제"""
    
    def delete_old_snapshots(self, account_id: str, days_threshold: int = 90) -> Dict:
        """오래된 스냅샷 삭제"""
    
    def cleanup_orphaned_snapshots(self, account_id: str) -> Dict:
        """소스 볼륨이 없는 고아 스냅샷 삭제"""
    
    def estimate_storage_savings(self, account_id: str) -> Dict:
        """정리로 절감될 스토리지 비용 예상"""
```

### 2.2 테스트 그룹
- Unattached Volume Deletion (2 테스트)
- Old Snapshot Cleanup (2 테스트)
- Orphaned Snapshot Detection (2 테스트)
- Cleanup Validation (2 테스트)
- Savings Estimation (2 테스트)

---

## Phase 3: EC2 생명주기 관리 (12 테스트)

### 3.1 EC2LifecycleManager 클래스
```python
class EC2LifecycleManager:
    def stop_idle_instances(self, account_id: str, cpu_threshold: float = 5) -> Dict:
        """
        유휴 인스턴스 자동 중지
        - CPU 사용률 5% 미만
        - 생산 환경 제외 (태그 확인)
        """
    
    def terminate_stopped_instances(self, account_id: str, days_stopped: int = 30) -> Dict:
        """
        30일 이상 중지된 인스턴스 종료
        """
    
    def tag_idle_instances(self, account_id: str) -> Dict:
        """
        유휴 인스턴스에 태그 추가
        Tag: {'LastIdleDetection': datetime}
        """
    
    def schedule_instance_shutdown(self, instance_id: str, schedule_time: str) -> str:
        """
        특정 시간에 인스턴스 정지 스케줄
        """
```

### 3.2 테스트 그룹
- Idle Instance Detection (2 테스트)
- Automatic Shutdown (2 테스트)
- Termination of Long-Stopped (2 테스트)
- Instance Tagging (2 테스트)
- Schedule Management (2 테스트)
- Safety Checks (2 테스트)

---

## Phase 4: 자동 대응 추적 (10 테스트)

### 4.1 CleanupAuditLogger 클래스
```python
class CleanupAuditLogger:
    def log_cleanup_action(self, account_id: str, action: Dict) -> None:
        """
        정리 작업 기록
        - resource_id, resource_type, action, timestamp
        - status: 'success', 'failed', 'dry_run'
        - savings: 절감 비용
        """
    
    def get_cleanup_summary(self, account_id: str, days: int = 30) -> Dict:
        """
        기간별 정리 작업 요약
        - 정리된 리소스 수
        - 절감 비용
        - 실패한 작업
        """
    
    def rollback_cleanup(self, cleanup_id: str) -> bool:
        """정리 작업 롤백 (이전 스냅샷 복구 등)"""
```

### 4.2 테스트 그룹
- Action Logging (2 테스트)
- Summary Generation (2 테스트)
- Cost Tracking (2 테스트)
- Rollback Capability (2 테스트)
- Report Generation (2 테스트)

---

## 구현 파일

### Phase 1
| 파일 | 설명 |
|------|------|
| `lambda/guardian/engines/auto_cleanup_engine.py` | AutoCleanupEngine 클래스 |
| `tests/backend/test_auto_cleanup_engine.py` | 12개 테스트 |

### Phase 2
| 파일 | 설명 |
|------|------|
| `lambda/guardian/managers/storage_cleanup_manager.py` | StorageCleanupManager 클래스 |
| `tests/backend/test_storage_cleanup.py` | 10개 테스트 |

### Phase 3
| 파일 | 설명 |
|------|------|
| `lambda/guardian/managers/ec2_lifecycle_manager.py` | EC2LifecycleManager 클래스 |
| `tests/backend/test_ec2_lifecycle.py` | 12개 테스트 |

### Phase 4
| 파일 | 설명 |
|------|------|
| `lambda/guardian/loggers/cleanup_audit_logger.py` | CleanupAuditLogger 클래스 |
| `tests/backend/test_cleanup_audit.py` | 10개 테스트 |

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 자동화 엔진 | AWS SDK (EC2, S3, EBS) |
| 스케줄링 | AWS EventBridge |
| 감사 로그 | DynamoDB |
| 비용 추적 | Cost Explorer API |
| 백엔드 | Python Lambda |
| 테스트 | pytest (44개) |

---

## 성공 지표

- [ ] Phase 1: 자동 정리 엔진 작동 100%
- [ ] Phase 2: 스토리지 비용 절감 확인
- [ ] Phase 3: EC2 생명주기 관리 안정성 > 99%
- [ ] Phase 4: 감사 로그 완벽성 100%
- [ ] 모든 44개 테스트 PASS
- [ ] 누적 테스트: 357 + 44 = 401 PASS

---

## 일정

| Phase | 예상 시간 | 상태 |
|-------|---------|------|
| Phase 1 | 2시간 | ❌ 예정 |
| Phase 2 | 1.5시간 | ❌ 예정 |
| Phase 3 | 2시간 | ❌ 예정 |
| Phase 4 | 1.5시간 | ❌ 예정 |
| **총** | **7시간** | **❌ 예정** |

---

## 다음 단계 (Sprint 41+)

**향후 개선:**
- 머신러닝 기반 비용 예측
- 실시간 CloudTrail 통합
- 자동 Reserved Instance 구매 제안
- 크로스리전 최적화
- 웹 대시보드 (자동화 현황, 절감액 추적)

---

## 검증 체크리스트

**Phase 1**
- [ ] AutoCleanupEngine 구현
- [ ] 12개 테스트 PASS

**Phase 2**
- [ ] StorageCleanupManager 구현
- [ ] 10개 테스트 PASS

**Phase 3**
- [ ] EC2LifecycleManager 구현
- [ ] 12개 테스트 PASS

**Phase 4**
- [ ] CleanupAuditLogger 구현
- [ ] 10개 테스트 PASS

**최종**
- [ ] 누적 44개 테스트 PASS
- [ ] 전체 테스트: 401 PASS
- [ ] Git 커밋: "feat: Sprint 40 - Automated Resource Cleanup"

---

**작성자:** Claude Code  
**작성일:** 2026-05-24  
**상태:** 📋 계획 단계
