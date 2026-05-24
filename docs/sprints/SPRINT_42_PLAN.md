# Sprint 42: Multi-Account Monitoring & Automated Remediation

> AWS Guardian의 멀티 계정 지원 및 자동 대응 시스템 확대

---

## 슬로건

**"여러 계정을 동시에 감시하고, 자동으로 대응한다"**

---

## 현황 분석

### 완료된 기능 (Sprint 40-41)
- ✅ 단일 계정 비용 모니터링
- ✅ EC2, S3, EBS 리소스 감시
- ✅ CloudTrail 이벤트 분석
- ✅ ARIMA 기반 비용 예측
- ✅ 2-sigma 이상 탐지
- ✅ 쿼리 캐싱 및 성능 최적화

### 누적 테스트
- 이전 스프린트: 401 tests
- Sprint 40: 44 tests (리소스 정리)
- Sprint 41: 44 tests (실시간 모니터링)
- **합계: 489 tests PASS**

### Sprint 42의 목표

| 항목 | 내용 |
|------|------|
| **주요 기능** | 멀티 계정 지원 + 자동 대응 |
| **테스트 수** | 44 tests (4 Phase × 11 tests) |
| **누적 테스트** | 533 tests PASS |
| **구현 파일** | 8개 신규 모듈 + 4개 테스트 |
| **배포 대상** | AWS Lambda (멀티 계정) |

---

## 4단계 구현 계획

### Phase 1: Multi-Account Manager (12 tests)

**목표:** 여러 AWS 계정을 하나의 대시보드에서 관리

**구현 파일:**
```
lambda/guardian/managers/multi_account_manager.py
  └─ MultiAccountManager 클래스
     ├─ register_account(account_id, role_arn, account_name)
     ├─ list_all_accounts()
     ├─ get_account_status(account_id)
     ├─ switch_account_context(account_id)
     ├─ aggregate_metrics(metric_type)
     └─ cross_account_query(query, accounts)

lambda/guardian/storage/account_registry.py
  └─ AccountRegistry 클래스
     ├─ add_account(account_config)
     ├─ update_account(account_id, config)
     ├─ remove_account(account_id)
     ├─ get_account(account_id)
     └─ list_accounts_by_status()

tests/backend/test_multi_account_manager.py (12 tests)
```

**기술 스택:**
- STS AssumeRole로 다른 계정 접근
- DynamoDB에 계정 메타데이터 저장
- 크로스 계정 쿼리 최적화

**테스트 그룹:**
- Group 1: 계정 등록 및 관리 (2 tests)
- Group 2: 멀티 계정 쿼리 (3 tests)
- Group 3: 메트릭 집계 (3 tests)
- Group 4: 계정 상태 모니터링 (4 tests)

---

### Phase 2: Automated Remediation Engine (12 tests)

**목표:** 감지된 위협에 자동으로 대응

**구현 파일:**
```
lambda/guardian/handlers/remediation_handler.py
  └─ RemediationHandler 클래스
     ├─ execute_remediation(threat_id, remediation_type)
     ├─ stop_instance(instance_id)
     ├─ revoke_iam_key(access_key_id)
     ├─ block_s3_public_access(bucket_name)
     ├─ disable_default_vpc_access(account_id)
     └─ create_remediation_ticket()

lambda/guardian/validators/remediation_validator.py
  └─ RemediationValidator 클래스
     ├─ validate_remediation(action, resource)
     ├─ check_dry_run(action)
     ├─ verify_iam_permissions()
     └─ generate_rollback_plan()

lambda/guardian/storage/remediation_log.py
  └─ RemediationLog 클래스
     ├─ log_remediation(action, details)
     ├─ get_remediation_history(account_id)
     ├─ log_rollback(original_state)
     └─ calculate_remediation_success_rate()

tests/backend/test_remediation_engine.py (12 tests)
```

**대응 작업:**
- **EC2 위협:** 인스턴스 자동 중지 (스냅샷 생성 후)
- **IAM 위협:** 의심 액세스키 비활성화
- **S3 위협:** 퍼블릭 액세스 자동 차단
- **VPC 위협:** 의심 보안그룹 규칙 제거

**테스트 그룹:**
- Group 1: 자동 대응 트리거 (2 tests)
- Group 2: EC2 대응 (3 tests)
- Group 3: IAM/S3 대응 (4 tests)
- Group 4: 롤백 및 감사 (3 tests)

---

### Phase 3: Compliance & Policy Monitoring (10 tests)

**목표:** AWS 규정 준수 모니터링 및 정책 위반 감지

**구현 파일:**
```
lambda/guardian/monitors/compliance_monitor.py
  └─ ComplianceMonitor 클래스
     ├─ check_encryption_status(resource_type)
     ├─ verify_logging_enabled(account_id)
     ├─ validate_iam_policies()
     ├─ check_mfa_enforcement()
     ├─ scan_public_resources()
     ├─ generate_compliance_report()
     └─ calculate_compliance_score()

lambda/guardian/validators/policy_validator.py
  └─ PolicyValidator 클래스
     ├─ validate_iam_policy(policy)
     ├─ check_least_privilege()
     ├─ detect_overly_permissive_policies()
     └─ suggest_policy_improvements()

tests/backend/test_compliance_monitoring.py (10 tests)
```

**규정 준수 체크:**
- 암호화 활성화 상태
- 로깅 설정 (CloudTrail, VPC Flow)
- MFA 강제 설정
- 퍼블릭 리소스 감지
- IAM 정책 최소 권한 원칙

**테스트 그룹:**
- Group 1: 암호화 및 로깅 (2 tests)
- Group 2: IAM 정책 검증 (2 tests)
- Group 3: 규정 준수 점수 (3 tests)
- Group 4: 자동 수정 제안 (3 tests)

---

### Phase 4: Advanced Visualization & Insights (10 tests)

**목표:** 실시간 대시보드 및 고급 분석

**구현 파일:**
```
lambda/guardian/analytics/dashboard_generator.py
  └─ DashboardGenerator 클래스
     ├─ generate_health_dashboard()
     ├─ generate_risk_dashboard()
     ├─ generate_cost_dashboard()
     ├─ create_alerts_summary()
     ├─ export_metrics(format)
     └─ generate_executive_summary()

lambda/guardian/analytics/trend_analyzer.py
  └─ TrendAnalyzer 클래스
     ├─ analyze_cost_trends()
     ├─ predict_future_costs()
     ├─ identify_cost_drivers()
     ├─ calculate_month_over_month()
     └─ generate_optimization_insights()

lambda/guardian/storage/metrics_warehouse.py
  └─ MetricsWarehouse 클래스
     ├─ store_metric(metric_name, value)
     ├─ get_timeseries_data(metric_name, days)
     ├─ aggregate_metrics_by_dimension()
     └─ query_metrics(filter_criteria)

tests/backend/test_advanced_analytics.py (10 tests)
```

**대시보드 종류:**
- **Health Dashboard:** 전체 시스템 상태, 활성 경고, 최근 대응
- **Risk Dashboard:** 위협 위험도, 취약점, 규정 준수 현황
- **Cost Dashboard:** 비용 추세, 예측, 절감 기회
- **Insights:** AI 기반 권장사항, 패턴 분석

**테스트 그룹:**
- Group 1: 메트릭 수집 및 저장 (2 tests)
- Group 2: 트렌드 분석 (2 tests)
- Group 3: 대시보드 생성 (3 tests)
- Group 4: 예측 및 통찰 (3 tests)

---

## 아키텍처 다이어그램

```
Sprint 42 System Architecture

┌─────────────────────────────────────────────────────────────┐
│                    AWS Guardian (Sprint 42)                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Multi-Account Manager (Phase 1)               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │ Account  │  │ Account  │  │ Cross-Account    │   │   │
│  │  │ Registry │  │ Context  │  │ Query Optimizer  │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │    Automated Remediation Engine (Phase 2)            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │EC2 Stop  │  │IAM Key   │  │S3 Block Public   │   │   │
│  │  │& Snapshot│  │Revoke    │  │Access            │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │ Remediation Validator + Rollback Plan        │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   Compliance & Policy Monitoring (Phase 3)           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Encryption│  │Logging   │  │IAM Policy        │   │   │
│  │  │Status    │  │Status    │  │Validator         │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │ Compliance Score + Auto-Fix Suggestions      │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Advanced Visualization & Insights (Phase 4)         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Dashboard │  │Trend     │  │Metrics           │   │   │
│  │  │Generator │  │Analyzer  │  │Warehouse         │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │Executive Summary + Cost Forecast             │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 데이터 흐름

```
Multiple AWS Accounts
    │
    ├─ Account A (Role ARN)
    ├─ Account B (Role ARN)
    ├─ Account C (Role ARN)
    └─ Account D (Role ARN)
         │
         ↓
    ┌─────────────────────┐
    │ MultiAccountManager │
    │  (STS AssumeRole)   │
    └─────────────────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    ↓         ↓         ↓          ↓
CloudTrail  CloudWatch  Cost    Config
Events     Metrics    Explorer  Data
    │         │         │        │
    └─────────┼─────────┼────────┘
              ↓
    ┌─────────────────────────────────┐
    │ Detection Engines                │
    │ • Anomaly Detection              │
    │ • Threat Detection               │
    │ • Compliance Validation          │
    └─────────────────────────────────┘
              ↓
    ┌─────────────────────────────────┐
    │ Remediation Decisions            │
    │ • Risk Score Evaluation          │
    │ • Dry-Run Verification          │
    │ • Rollback Planning             │
    └─────────────────────────────────┘
              ↓
    ┌─────────────────────────────────┐
    │ Automated Actions (if approved)  │
    │ • Stop EC2 Instance             │
    │ • Revoke IAM Key               │
    │ • Block S3 Public Access       │
    └─────────────────────────────────┘
              ↓
    ┌─────────────────────────────────┐
    │ Audit & Compliance Logging       │
    │ • Action History                │
    │ • Rollback Records              │
    │ • Compliance Score              │
    └─────────────────────────────────┘
              ↓
    ┌─────────────────────────────────┐
    │ Dashboard & Insights             │
    │ • Health Status                 │
    │ • Risk Dashboard                │
    │ • Cost Trends                   │
    │ • Recommendations               │
    └─────────────────────────────────┘
```

---

## 구현 순서 및 테스트

| Phase | 단계 | 테스트 수 | 누적 |
|-------|------|---------|------|
| 1 | Multi-Account Manager | 12 | 12 |
| 2 | Automated Remediation | 12 | 24 |
| 3 | Compliance Monitoring | 10 | 34 |
| 4 | Advanced Analytics | 10 | 44 |
| **전체** | Sprint 42 | **44** | **533** |

---

## 주요 설계 결정

### 1. STS AssumeRole 기반 멀티 계정 접근
- **선택:** 각 계정에 IAM Role 생성 → Guardian이 AssumeRole로 접근
- **장점:** 중앙 집중식 관리, 감사 로깅 용이, 권한 격리
- **구현:** boto3 sts_client.assume_role() + STS credentials 캐싱

### 2. 자동 대응 Dry-Run 및 승인 프로세스
- **선택:** 모든 대응 작업을 dry-run으로 먼저 검증 → 승인 후 실행
- **장점:** 실수 방지, 감사 추적 용이, 수동 개입 가능
- **구현:** RemediationValidator + 스냅샷 생성 후 중지

### 3. 규정 준수 점수 계산
- **선택:** 암호화, 로깅, MFA, 공개 액세스 등의 가중치 합산
- **장점:** 한 눈에 전체 준수 수준 파악 가능
- **구현:** 0-100 점수 + 자동 수정 제안

### 4. 메트릭 웨어하우스 아키텍처
- **선택:** CloudWatch → DynamoDB → 분석 엔진 → 대시보드
- **장점:** 시간 범위 쿼리, 집계, 예측 가능
- **구현:** 시간별 집계 + 월별 요약

---

## 성공 지표

| 지표 | 목표 |
|------|------|
| 멀티 계정 관리 | 10개 계정 동시 모니터링 |
| 자동 대응 성공률 | >98% |
| 규정 준수 검사 | 모든 주요 규정 커버 |
| 대시보드 갱신 속도 | <5초 |
| 쿼리 응답 시간 | <1초 (캐시 포함) |

---

## 다음 단계 (Sprint 43+)

**향후 개선:**
1. ML 기반 이상 탐지 (isolation forest)
2. 머신러닝 모델 자동 재학습
3. CloudTrail 스트림 (실시간 처리)
4. 자동 티켓 생성 (Jira/ServiceNow)
5. 슬랙/팀즈 통합 알림
6. 비용 최적화 ROI 계산
7. 예약 대응 (스케줄 기반)
8. 멀티 클라우드 지원 (GCP, Azure)

---

## 기술 스택 (Sprint 42)

| 레이어 | 기술 |
|--------|------|
| 언어 | Python 3.12 |
| 런타임 | AWS Lambda |
| 다중 계정 | STS AssumeRole + IAM Role |
| 메트릭 | CloudWatch API |
| 저장소 | DynamoDB + S3 |
| 규정 | AWS Config API |
| 감사 | CloudTrail + DynamoDB |
| 테스트 | pytest (44 tests) |

---

## 체크리스트

**Phase 1: Multi-Account Manager**
- [ ] MultiAccountManager 클래스 구현
- [ ] AccountRegistry 저장소 구현
- [ ] STS AssumeRole 통합
- [ ] 크로스 계정 쿼리 최적화
- [ ] 12개 테스트 PASS

**Phase 2: Automated Remediation**
- [ ] RemediationHandler 클래스 구현
- [ ] RemediationValidator 구현
- [ ] EC2, IAM, S3 대응 작업
- [ ] Dry-Run 및 롤백 지원
- [ ] 12개 테스트 PASS

**Phase 3: Compliance Monitoring**
- [ ] ComplianceMonitor 구현
- [ ] PolicyValidator 구현
- [ ] 암호화/로깅/MFA 검사
- [ ] 규정 준수 점수 계산
- [ ] 10개 테스트 PASS

**Phase 4: Advanced Analytics**
- [ ] DashboardGenerator 구현
- [ ] TrendAnalyzer 구현
- [ ] MetricsWarehouse 구현
- [ ] 대시보드 및 통찰 생성
- [ ] 10개 테스트 PASS

**최종:**
- [ ] 누적 44개 테스트 모두 PASS
- [ ] 전체 테스트: 533 PASS (489 + 44)
- [ ] Git 커밋: "feat: Sprint 42 - Multi-Account Monitoring & Automated Remediation"

---

**Sprint 42 계획 완료** ✅
