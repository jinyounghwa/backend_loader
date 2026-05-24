# Sprint 44: 자동화된 티켓팅 & SOAR 플랫폼 통합 - PLAN

> AWS Guardian의 이상 탐지 → 자동 티켓팅 → 자동 대응 워크플로우 구현

**Status:** 📋 PLANNING

---

## 🎯 Sprint Overview

| 항목 | 목표 |
|------|------|
| **목표** | Automated Ticketing (Jira/ServiceNow) + SOAR Integration + Custom Workflows |
| **예상 테스트** | 48 tests (12 + 12 + 12 + 12) |
| **예상 누적** | 554+ tests (Sprint 43: 506 + Sprint 44: 48) |
| **구현 모듈** | 12개 신규 (ticket handlers, workflow engines, SOAR connectors, orchestrators) |
| **배포 대상** | AWS Lambda (SNS + EventBridge for workflow triggers) |
| **지연시간** | CloudTrail 이상 → 티켓 생성까지 < 2초 |

---

## 📊 Phase-by-Phase Plan

### Phase 1: Automated Ticketing System ✏️
**목표: 12 tests PASS**

이상 탐지 → 자동 티켓 생성 (Jira, ServiceNow, Linear 지원)

**구현 파일:**
- `lambda/guardian/handlers/ticketing_handler.py` (250 lines)
  - TicketingHandler: SNS 이벤트 → 티켓 자동 생성
    - create_ticket(): 위협 → 티켓 매핑
    - enrich_ticket_with_evidence(): 근거 추가 (CloudTrail 로그)
    - add_assignee_by_rule(): 규칙 기반 담당자 할당
    - track_ticket_lifecycle(): 티켓 상태 추적

- `lambda/guardian/services/jira_service.py` (200 lines)
  - JiraTicketService: Jira 티켓 관리
    - create_issue(): 보안 이슈 생성
    - update_issue_status(): 상태 업데이트
    - add_comment_with_evidence(): 댓글에 증거 추가
    - link_related_issues(): 관련 이슈 연결

- `lambda/guardian/services/servicenow_service.py` (200 lines)
  - ServiceNowTicketService: ServiceNow 인시던트 관리
    - create_incident(): 보안 인시던트 생성
    - attach_evidence_to_incident(): 증거 첨부
    - escalate_incident(): 심각도 기반 에스컬레이션
    - update_incident_status(): 상태 업데이트

**테스트 분포:**
- Group 1: Jira 티켓 생성 (3 tests) ✅
- Group 2: ServiceNow 인시던트 생성 (3 tests) ✅
- Group 3: 증거 수집 및 첨부 (3 tests) ✅
- Group 4: 담당자 할당 및 에스컬레이션 (3 tests) ✅

---

### Phase 2: Custom Remediation Workflows ✏️
**목표: 12 tests PASS**

사용자 정의 자동 대응 워크플로우 구성 및 실행

**구현 파일:**
- `lambda/guardian/workflows/workflow_engine.py` (280 lines)
  - WorkflowEngine: 워크플로우 정의 및 실행
    - create_workflow(): 조건 → 액션 체인 정의
    - execute_workflow(): 위협 패턴 → 워크플로우 실행
    - validate_workflow_steps(): 단계별 유효성 검증
    - track_workflow_execution(): 실행 상태 및 결과 추적

- `lambda/guardian/actions/remediation_actions.py` (300 lines)
  - RemediationActions: 자동 대응 액션 라이브러리
    - stop_ec2_instance(): EC2 인스턴스 중지
    - revoke_iam_permissions(): 의심 IAM 권한 회수
    - isolate_security_group(): 보안 그룹 격리
    - delete_public_s3_access(): S3 퍼블릭 접근 차단
    - backup_and_snapshot(): 인스턴스 스냅샷 생성

- `lambda/guardian/workflows/workflow_repository.py` (200 lines)
  - WorkflowRepository: 워크플로우 저장소
    - save_workflow(): 커스텀 워크플로우 저장
    - get_workflow(): 규칙 ID별 워크플로우 조회
    - list_workflows_by_threat_type(): 위협 타입별 워크플로우
    - update_workflow(): 워크플로우 수정

**테스트 분포:**
- Group 1: 워크플로우 정의 및 검증 (3 tests) ✅
- Group 2: EC2/IAM/S3 자동 대응 (3 tests) ✅
- Group 3: 조건 평가 및 액션 체인 실행 (3 tests) ✅
- Group 4: 워크플로우 상태 추적 (3 tests) ✅

---

### Phase 3: SOAR Platform Integration ✏️
**목표: 12 tests PASS**

Splunk Phantom / Swimlane 등 SOAR 플랫폼 통합

**구현 파일:**
- `lambda/guardian/integrations/soar_connector.py` (250 lines)
  - SOARConnector: SOAR 플랫폼 통합
    - send_incident_to_soar(): AWS Guardian → SOAR 인시던트
    - receive_playbook_result(): SOAR 플레이북 결과 수신
    - sync_status_with_soar(): 양방향 상태 동기화
    - get_available_playbooks(): 사용 가능한 플레이북 조회

- `lambda/guardian/integrations/splunk_phantom_connector.py` (220 lines)
  - SplunkPhantomConnector: Splunk Phantom 특화
    - create_phantom_container(): 컨테이너 생성 (케이스)
    - run_phantom_playbook(): 자동 플레이북 실행
    - track_playbook_status(): 플레이북 진행 상태 추적
    - get_phantom_case_summary(): 플레이북 결과 요약

- `lambda/guardian/integrations/swimlane_connector.py` (200 lines)
  - SwimlaneConnector: Swimlane 특화
    - create_swimlane_record(): 레코드 생성
    - attach_evidence_to_record(): 증거 첨부
    - trigger_swimlane_workflow(): 워크플로우 트리거
    - update_record_status(): 레코드 상태 업데이트

**테스트 분포:**
- Group 1: SOAR 인시던트 생성 (3 tests) ✅
- Group 2: Splunk Phantom 플레이북 실행 (3 tests) ✅
- Group 3: Swimlane 워크플로우 트리거 (3 tests) ✅
- Group 4: 양방향 상태 동기화 (3 tests) ✅

---

### Phase 4: Workflow Orchestration & Automation ✏️
**목표: 12 tests PASS**

전체 아키텍처 조율 (이상 탐지 → 티켓 → 플레이북 → 대응)

**구현 파일:**
- `lambda/guardian/orchestrators/incident_orchestrator.py` (280 lines)
  - IncidentOrchestrator: 전체 인시던트 파이프라인 조율
    - orchestrate_incident_response(): 위협 → 티켓 → SOAR 플레이북 → 대응
    - coordinate_parallel_workflows(): 병렬 워크플로우 조율
    - track_incident_to_resolution(): 인시던트 → 해결까지 추적
    - generate_incident_report(): 대응 보고서 생성

- `lambda/guardian/handlers/orchestration_handler.py` (200 lines)
  - OrchestrationHandler: EventBridge 이벤트 처리
    - handle_threat_event(): 위협 이벤트 → 전체 파이프라인 시작
    - handle_workflow_status_change(): 워크플로우 상태 변경 이벤트
    - handle_playbook_completion(): SOAR 플레이북 완료 이벤트

- `lambda/guardian/models/incident_model.py` (150 lines)
  - IncidentModel: 인시던트 데이터 모델
    - threat_event: 원본 위협
    - ticket_id: 생성된 티켓
    - workflow_id: 실행된 워크플로우
    - playbook_id: 실행된 SOAR 플레이북
    - status: detection → ticket_created → workflow_executed → resolved

**테스트 분포:**
- Group 1: 인시던트 파이프라인 조율 (3 tests) ✅
- Group 2: 병렬 워크플로우 실행 (3 tests) ✅
- Group 3: 이벤트 기반 상태 전이 (3 tests) ✅
- Group 4: 대응 보고서 생성 (3 tests) ✅

---

## 📈 Expected Results

| Phase | 테스트 | 기대 결과 |
|-------|--------|---------|
| Phase 1 | 12 | Jira/ServiceNow 자동 티켓팅 ✅ |
| Phase 2 | 12 | EC2/IAM/S3 자동 대응 ✅ |
| Phase 3 | 12 | SOAR 플레이북 실행 ✅ |
| Phase 4 | 12 | E2E 인시던트 오케스트레이션 ✅ |
| **전체** | **48** | **554+ cumulative** |

---

## 🏗️ Architecture Integration

```
CloudTrail Event (Real-time)
    ↓
IsolationForestDetector (Sprint 43)
    ↓
NotificationOrchestrator (Sprint 43)
    ├─ SlackResponder
    ├─ TeamsResponder
    └─ IncidentOrchestrator (Sprint 44)
        │
        ├─ TicketingHandler
        │   ├─ JiraTicketService
        │   └─ ServiceNowTicketService
        │
        ├─ WorkflowEngine
        │   └─ RemediationActions
        │       ├─ EC2 Stop
        │       ├─ IAM Revoke
        │       ├─ S3 Block
        │       └─ Snapshot
        │
        └─ SOARConnector
            ├─ SplunkPhantomConnector
            └─ SwimlaneConnector

Track: ticket_id → workflow_id → playbook_id → incident resolution
```

---

## 🔑 Key Features

### Automated Ticketing
- **Jira 통합**: 보안 이슈 자동 생성
- **ServiceNow 통합**: 인시던트 자동 생성
- **근거 첨부**: CloudTrail 로그 자동 포함
- **담당자 할당**: 규칙 기반 RACI 매핑

### Custom Workflows
- **조건→액션**: IF/THEN 워크플로우 정의
- **병렬 실행**: 여러 액션 동시 실행
- **상태 추적**: 각 단계별 진행 상황 모니터링
- **롤백 가능**: 실행 취소 지원

### SOAR Integration
- **Phantom 플레이북**: 자동 플레이북 실행
- **Swimlane 워크플로우**: 핵심 프로세스 자동화
- **양방향 동기화**: 결과 수신 → 추가 대응
- **커스텀 통합**: REST API 기반 확장 가능

### E2E Orchestration
- **이상 탐지 → 티켓 생성**: < 1초
- **티켓 → 워크플로우 시작**: < 2초
- **워크플로우 → SOAR 플레이북**: < 3초
- **전체 대응 시간**: < 10초

---

## ✅ Success Metrics

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| 자동 티켓팅 성공률 | >99% | Jira/ServiceNow 생성 건수 |
| 워크플로우 실행률 | >95% | 실행 완료 / 시작 비율 |
| SOAR 플레이북 실행 | >90% | Phantom/Swimlane 실행 건수 |
| E2E 응답 시간 | < 10초 | CloudTrail → 인시던트 해결까지 |
| 테스트 커버리지 | 48/48 | 모든 테스트 PASS |

---

## 📋 Implementation Order

```
Week 1: Phase 1 (Ticketing)
  ├─ JiraTicketService 구현
  ├─ ServiceNowTicketService 구현
  ├─ TicketingHandler 구현
  └─ 12 tests PASS

Week 2: Phase 2 (Workflows)
  ├─ WorkflowEngine 구현
  ├─ RemediationActions 구현
  ├─ WorkflowRepository 구현
  └─ 12 tests PASS

Week 3: Phase 3 (SOAR)
  ├─ SplunkPhantomConnector 구현
  ├─ SwimlaneConnector 구현
  ├─ SOARConnector 구현
  └─ 12 tests PASS

Week 4: Phase 4 (Orchestration)
  ├─ IncidentOrchestrator 구현
  ├─ OrchestrationHandler 구현
  ├─ E2E 테스트
  └─ 12 tests PASS
```

---

## 📁 Expected File Structure

```
lambda/guardian/
├── handlers/
│   ├── ticketing_handler.py (250 lines)
│   └── orchestration_handler.py (200 lines)
├── services/
│   ├── jira_service.py (200 lines)
│   └── servicenow_service.py (200 lines)
├── workflows/
│   ├── workflow_engine.py (280 lines)
│   └── workflow_repository.py (200 lines)
├── actions/
│   └── remediation_actions.py (300 lines)
├── integrations/
│   ├── soar_connector.py (250 lines)
│   ├── splunk_phantom_connector.py (220 lines)
│   └── swimlane_connector.py (200 lines)
├── orchestrators/
│   └── incident_orchestrator.py (280 lines)
└── models/
    └── incident_model.py (150 lines)

tests/backend/
├── test_ticketing.py (12 tests)
├── test_workflows.py (12 tests)
├── test_soar_integration.py (12 tests)
└── test_orchestration.py (12 tests)

docs/sprints/
├── SPRINT_44_PLAN.md (this file)
└── SPRINT_44_COMPLETION.md (to be created)

총 코드량:
- 구현: ~2,000 lines (handlers, services, workflows, actions, integrations, orchestrators)
- 테스트: ~500 lines (48 comprehensive tests)
```

---

## 🔧 Technical Decisions

### 1. Jira vs ServiceNow
**선택:** 둘 다 지원
- **장점:** 팀 선호도 맞춤, 중복 제거 가능
- **트레이드오프:** 통합 코드 복잡도 증가
- **ROI:** 기존 ITSM 투자 활용

### 2. Splunk Phantom vs Swimlane
**선택:** 둘 다 지원 (REST API 기반)
- **장점:** 조직의 SOAR 선택에 유연한 대응
- **트레이드오프:** 플랫폼별 맞춤 개발 필요
- **활용:** 기존 플레이북 재활용

### 3. 워크플로우 정의 형식
**선택:** JSON 기반 DSL (Airflow 스타일)
```json
{
  "name": "Stop Compromised EC2",
  "trigger": "high_risk_api_call",
  "steps": [
    { "action": "stop_ec2", "params": { "force": true } },
    { "action": "snapshot_ebs", "params": { "retention_days": 30 } },
    { "action": "create_ticket", "params": { "priority": "high" } }
  ]
}
```

### 4. 이벤트 기반 조율
**선택:** EventBridge + SNS (느슨한 결합)
- **장점:** 확장 가능, 장애 격리
- **트레이드오프:** 디버깅 어려움 (분산 시스템)
- **해결:** 상세한 로깅 + 분산 추적

---

## 📌 Next Sprint (Sprint 45)

**향후 개선:**
1. 머신러닝 기반 우선순위 (심각도 예측)
2. 자동 복구 (IaC 기반)
3. 다중 클라우드 (GCP, Azure)
4. GraphQL API
5. 웹 대시보드 개선
6. 보험 통합 (위험도 기반 보험료)

---

**Sprint 44 계획 완료** 📋

**시작 준비:** 언제든 Phase 1부터 시작 가능
