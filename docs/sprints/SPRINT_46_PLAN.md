# Sprint 46 계획: 자동 복구 작업 시스템

**상태:** 📋 계획 중  
**예상 기간:** 1주  
**기준 테스트:** 649 (Sprint 45 완료)  
**목표 테스트:** 700+ (51개 이상 추가)  

---

## 목표 (Objectives)

Sprint 45에서 구축한 **완전한 자동 감시 및 알림 시스템**을 **자동 복구 시스템**으로 확장합니다:

1. **EC2 자동 복구** - 비정상 인스턴스 자동 중지
2. **S3 자동 복구** - 퍼블릭 버킷 자동 차단
3. **IAM 자동 복구** - 비정상 권한 자동 취소
4. **네트워크 격리** - 위협 인스턴스 자동 격리

---

## Phase별 구현 계획

### Phase 1: EC2 자동 복구 (16 tests)

**목표:** 비인가된 EC2 인스턴스 자동 중지

#### 1.1 EC2 Remediation 핸들러

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `lambda/guardian/remediators/ec2_remediator.py` | 신규: EC2 자동 중지 로직 | - |
| `lambda/guardian/handlers/ec2_remediation_handler.py` | 신규: EC2 Lambda 핸들러 | - |
| `tests/backend/test_ec2_remediation.py` | 신규: EC2 복구 검증 | 8 |
| `tests/backend/test_ec2_remediation_safety.py` | 신규: 안전 장치 검증 | 5 |
| `tests/integration/test_ec2_remediation_integration.py` | 신규: 통합 테스트 | 3 |

**구현 내용:**

```python
# lambda/guardian/remediators/ec2_remediator.py

class EC2Remediator:
    """EC2 인스턴스 자동 복구"""
    
    def __init__(self, ec2_client, audit_logger):
        self.ec2 = ec2_client
        self.audit = audit_logger
    
    def remediate_unauthorized_instance(self, instance_id: str, threat: Dict) -> Dict:
        """
        비정상 EC2 인스턴스 중지
        
        안전 장치:
        1. 프로덕션 인스턴스 확인 (tag: environment=production)
        2. 자동 복구 비활성화 태그 확인
        3. 관리자 승인 확인 (옵션)
        4. 복구 전 백업 생성
        5. 복구 후 감사 로그 기록
        """
        pass
    
    def stop_instance(self, instance_id: str) -> bool:
        """인스턴스 중지"""
        pass
    
    def create_snapshot_before_stop(self, instance_id: str) -> str:
        """중지 전 EBS 스냅샷 생성"""
        pass
    
    def verify_safety_conditions(self, instance_id: str) -> bool:
        """안전 조건 검증"""
        pass
```

**테스트 시나리오:**

```python
# Remediation (8 tests)
- test_ec2_remediation_stops_unauthorized_instance
- test_ec2_remediation_creates_snapshot
- test_ec2_remediation_tags_stopped_instance
- test_ec2_remediation_logs_action
- test_ec2_remediation_verifies_instance_stopped
- test_ec2_remediation_handles_already_stopped_instance
- test_ec2_remediation_handles_termination_protection
- test_ec2_remediation_concurrent_instances

# Safety (5 tests)
- test_ec2_remediation_skips_production_tags
- test_ec2_remediation_skips_disabled_instances
- test_ec2_remediation_requires_approval_for_protected
- test_ec2_remediation_rollback_on_error
- test_ec2_remediation_preserve_instance_state

# Integration (3 tests)
- test_threat_detection_to_ec2_stop
- test_ec2_stop_triggers_notification
- test_ec2_stop_with_network_isolation
```

---

### Phase 2: S3 자동 복구 (15 tests)

**목표:** 퍼블릭 버킷 자동 차단

#### 2.1 S3 Remediation 핸들러

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `lambda/guardian/remediators/s3_remediator.py` | 신규: S3 퍼블릭 차단 | - |
| `lambda/guardian/handlers/s3_remediation_handler.py` | 신규: S3 Lambda 핸들러 | - |
| `tests/backend/test_s3_remediation.py` | 신규: S3 복구 검증 | 8 |
| `tests/backend/test_s3_remediation_compliance.py` | 신규: 규정 준수 검증 | 4 |
| `tests/integration/test_s3_remediation_integration.py` | 신규: 통합 테스트 | 3 |

**구현 내용:**

```python
# lambda/guardian/remediators/s3_remediator.py

class S3Remediator:
    """S3 버킷 자동 복구"""
    
    def __init__(self, s3_client, audit_logger):
        self.s3 = s3_client
        self.audit = audit_logger
    
    def remediate_public_bucket(self, bucket_name: str, threat: Dict) -> Dict:
        """
        퍼블릭 버킷 자동 차단
        
        복구 단계:
        1. 현재 ACL/정책 백업
        2. BlockPublicAccess 활성화
        3. 버킷 정책 검증
        4. 애플리케이션 영향 분석
        5. 감사 로그 기록
        """
        pass
    
    def enable_block_public_access(self, bucket_name: str) -> bool:
        """BlockPublicAccess 활성화"""
        pass
    
    def backup_bucket_policy(self, bucket_name: str) -> Dict:
        """버킷 정책 백업"""
        pass
    
    def remove_public_acl(self, bucket_name: str) -> bool:
        """Public ACL 제거"""
        pass
```

**테스트 시나리오:**

```python
# Remediation (8 tests)
- test_s3_remediation_blocks_public_bucket
- test_s3_remediation_removes_public_acl
- test_s3_remediation_updates_bucket_policy
- test_s3_remediation_backs_up_original_policy
- test_s3_remediation_preserves_private_access
- test_s3_remediation_handles_versioning
- test_s3_remediation_handles_mfa_delete
- test_s3_remediation_concurrent_buckets

# Compliance (4 tests)
- test_s3_remediation_maintains_data_access
- test_s3_remediation_logs_policy_changes
- test_s3_remediation_notifies_bucket_owner
- test_s3_remediation_audit_trail

# Integration (3 tests)
- test_threat_detection_to_s3_block
- test_s3_block_preserves_https
- test_s3_block_with_cloudfront
```

---

### Phase 3: IAM 자동 복구 (12 tests)

**목표:** 비정상 IAM 권한 자동 취소

#### 3.1 IAM Remediation 핸들러

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `lambda/guardian/remediators/iam_remediator.py` | 신규: IAM 권한 취소 | - |
| `lambda/guardian/handlers/iam_remediation_handler.py` | 신규: IAM Lambda 핸들러 | - |
| `tests/backend/test_iam_remediation.py` | 신규: IAM 복구 검증 | 6 |
| `tests/backend/test_iam_remediation_risk.py` | 신규: 위험 분석 검증 | 4 |
| `tests/integration/test_iam_remediation_integration.py` | 신규: 통합 테스트 | 2 |

**구현 내용:**

```python
# lambda/guardian/remediators/iam_remediator.py

class IAMRemediator:
    """IAM 권한 자동 복구"""
    
    def __init__(self, iam_client, audit_logger):
        self.iam = iam_client
        self.audit = audit_logger
    
    def remediate_excessive_permissions(self, principal: str, threat: Dict) -> Dict:
        """
        과도한 IAM 권한 취소
        
        복구 단계:
        1. 현재 권한 목록 분석
        2. 위험한 권한 식별 (AdministratorAccess, *:*)
        3. 영향도 분석
        4. 취소할 권한 선택
        5. 권한 제거
        6. 감사 로그 기록
        """
        pass
    
    def detach_dangerous_policies(self, principal: str) -> List[str]:
        """위험한 정책 분리"""
        pass
    
    def rotate_access_keys(self, user_name: str) -> Dict:
        """액세스 키 로테이션"""
        pass
    
    def create_session_token(self, principal: str, duration: int) -> Dict:
        """임시 STS 토큰 생성"""
        pass
```

**테스트 시나리오:**

```python
# Remediation (6 tests)
- test_iam_remediation_detaches_admin_policy
- test_iam_remediation_rotates_access_keys
- test_iam_remediation_creates_temporary_token
- test_iam_remediation_blocks_principal
- test_iam_remediation_preserves_essential_permissions
- test_iam_remediation_handles_service_roles

# Risk Analysis (4 tests)
- test_iam_remediation_analyzes_blast_radius
- test_iam_remediation_identifies_affected_resources
- test_iam_remediation_estimates_impact
- test_iam_remediation_requires_confirmation_for_high_risk

# Integration (2 tests)
- test_threat_detection_to_iam_revoke
- test_iam_revoke_with_session_termination
```

---

### Phase 4: 네트워크 격리 (8 tests)

**목표:** 위협 인스턴스 자동 네트워크 격리

#### 4.1 Network Isolation 핸들러

| 파일 | 목적 | 테스트 수 |
|------|------|---------|
| `lambda/guardian/remediators/network_remediator.py` | 신규: 네트워크 격리 | - |
| `lambda/guardian/handlers/network_remediation_handler.py` | 신규: 네트워크 Lambda 핸들러 | - |
| `tests/backend/test_network_remediation.py` | 신규: 네트워크 검증 | 5 |
| `tests/integration/test_network_remediation_integration.py` | 신규: 통합 테스트 | 3 |

**구현 내용:**

```python
# lambda/guardian/remediators/network_remediator.py

class NetworkRemediator:
    """네트워크 격리"""
    
    def __init__(self, ec2_client, audit_logger):
        self.ec2 = ec2_client
        self.audit = audit_logger
    
    def isolate_instance(self, instance_id: str, threat: Dict) -> Dict:
        """
        위협 인스턴스 격리
        
        격리 방법:
        1. 격리 보안 그룹 생성
        2. ENI에서 모든 SG 제거
        3. 격리 SG만 적용
        4. VPC Flow Logs 활성화
        5. 감사 로그 기록
        """
        pass
    
    def create_isolation_security_group(self, vpc_id: str) -> str:
        """격리용 보안 그룹 생성"""
        pass
    
    def detach_all_security_groups(self, instance_id: str) -> List[str]:
        """모든 보안 그룹 제거"""
        pass
    
    def enable_vpc_flow_logs(self, instance_id: str) -> bool:
        """VPC Flow Logs 활성화"""
        pass
```

**테스트 시나리오:**

```python
# Remediation (5 tests)
- test_network_remediation_isolates_instance
- test_network_remediation_creates_isolation_sg
- test_network_remediation_removes_existing_sgs
- test_network_remediation_enables_flow_logs
- test_network_remediation_logs_isolation

# Integration (3 tests)
- test_threat_detection_to_network_isolation
- test_network_isolation_preserves_ebs
- test_network_isolation_allows_aws_services
```

---

## 구현 일정

| Phase | 항목 | 예상 일수 | 테스트 수 |
|-------|------|---------|---------|
| 1 | EC2 자동 복구 | 2일 | 16 |
| 2 | S3 자동 복구 | 2일 | 15 |
| 3 | IAM 자동 복구 | 1.5일 | 12 |
| 4 | 네트워크 격리 | 0.5일 | 8 |
| **합계** | **모든 Phase** | **6일** | **51** |

---

## 성공 기준

| 기준 | 목표 | 검증 방법 |
|------|------|---------|
| 테스트 커버리지 | 80%+ | codecov.io |
| 복구 성공률 | 99%+ | 통합 테스트 |
| 안전 장치 | 100% | Phase별 안전 테스트 |
| 롤백 가능성 | 100% | 백업 & 복구 테스트 |
| 감사 로그 | 100% | 모든 작업 기록 검증 |
| 복구 시간 | < 1초 | 성능 테스트 |

---

## 안전 설계 원칙

### 1. 다층 안전 장치

```
위협 탐지
    ↓
분석 & 컨펌 (임계값, 조건)
    ↓
안전 검사 (프로덕션, 태그, 보호)
    ↓
실행 전 백업 (정책, 스냅샷, 설정)
    ↓
자동 복구 실행
    ↓
검증 & 로깅
    ↓
롤백 대기 (관리자 검토 기간)
```

### 2. 복구 금지 조건

- 프로덕션 환경 (environment=production)
- 자동 복구 비활성화 태그 설정
- 관리자 승인 필수 인스턴스
- 중요 서비스 실행 중
- 최근 배포 (< 1시간)

### 3. 롤백 메커니즘

- 모든 복구 전 상태 백업
- 1시간 내 자동 롤백 옵션
- 관리자 수동 롤백 지원
- 변경 이력 완전 기록

---

## 모니터링 메트릭

```python
# CloudWatch 메트릭
RemediationAttempts
├── EC2Stop
├── S3BlockPublicAccess
├── IAMRevokePermissions
└── NetworkIsolation

RemediationSuccess
├── Successful
├── Failed
└── RolledBack

RemediationDuration (ms)
├── EC2 (median: 500ms)
├── S3 (median: 300ms)
├── IAM (median: 400ms)
└── Network (median: 200ms)

RemediationRollbacks
├── Auto (24시간 내)
├── Manual
└── Failed
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 복구 엔진 | Python (boto3) |
| 안전 검사 | 정책 엔진, 조건부 실행 |
| 백업 & 롤백 | AWS Config, Custom Storage |
| 감사 로깅 | CloudTrail, DynamoDB |
| 모니터링 | CloudWatch, Custom Metrics |
| 알림 | SNS, Slack, Email |
| 테스트 | pytest, moto (AWS mocking) |

---

## 신규 파일 목록

### Lambda 함수

```
lambda/guardian/remediators/
├── ec2_remediator.py        (EC2 중지)
├── s3_remediator.py         (S3 차단)
├── iam_remediator.py        (IAM 취소)
└── network_remediator.py    (네트워크 격리)

lambda/guardian/handlers/
├── ec2_remediation_handler.py
├── s3_remediation_handler.py
├── iam_remediation_handler.py
└── network_remediation_handler.py
```

### 테스트

```
tests/backend/
├── test_ec2_remediation.py
├── test_ec2_remediation_safety.py
├── test_s3_remediation.py
├── test_s3_remediation_compliance.py
├── test_iam_remediation.py
├── test_iam_remediation_risk.py
└── test_network_remediation.py

tests/integration/
├── test_ec2_remediation_integration.py
├── test_s3_remediation_integration.py
├── test_iam_remediation_integration.py
└── test_network_remediation_integration.py
```

---

## 다음 단계 (Sprint 47+)

### Sprint 47: Advanced Analytics
- 인시던트 상관관계 분석
- 위협 패턴 인식
- 머신러닝 기반 이상 탐지

### Sprint 48: Multi-Account Management
- 다중 AWS 계정 지원
- 중앙 집중식 대시보드
- 계정별 정책 설정

---

## 검증 체크리스트

**Phase 1: EC2 자동 복구**
- [ ] EC2Remediator 클래스 구현
- [ ] 8개 복구 테스트 PASS
- [ ] 5개 안전 테스트 PASS
- [ ] 3개 통합 테스트 PASS
- [ ] 총 16개 테스트 PASS

**Phase 2: S3 자동 복구**
- [ ] S3Remediator 클래스 구현
- [ ] 8개 복구 테스트 PASS
- [ ] 4개 규정준수 테스트 PASS
- [ ] 3개 통합 테스트 PASS
- [ ] 총 15개 테스트 PASS

**Phase 3: IAM 자동 복구**
- [ ] IAMRemediator 클래스 구현
- [ ] 6개 복구 테스트 PASS
- [ ] 4개 위험 분석 테스트 PASS
- [ ] 2개 통합 테스트 PASS
- [ ] 총 12개 테스트 PASS

**Phase 4: 네트워크 격리**
- [ ] NetworkRemediator 클래스 구현
- [ ] 5개 복구 테스트 PASS
- [ ] 3개 통합 테스트 PASS
- [ ] 총 8개 테스트 PASS

**최종:**
- [ ] 누적 51개 테스트 모두 PASS
- [ ] 전체 테스트: 649 (Sprint 45) + 51 (Sprint 46) = 700 PASS
- [ ] Git 커밋: "feat: Sprint 46 - 자동 복구 작업 시스템"

---

## 리소스 및 참고 자료

### AWS 문서
- [EC2 Stop Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html)
- [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-overview.html)
- [IAM Policy Simulator](https://policysim.aws.amazon.com/)
- [VPC Security Groups](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)

### 라이브러리
- boto3 (AWS SDK)
- moto (AWS mocking for tests)
- pytest (testing framework)

---

**계획 작성:** 2026-05-25  
**예상 시작:** 2026-05-25  
**예상 완료:** 2026-05-31
