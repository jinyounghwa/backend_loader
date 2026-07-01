---
module: handlers-engines
path: 05-Handlers-Engines
keywords: handlers, engines, automation, playbook, realtime, remediation
---

# Handlers & Engines — 자동화 처리 레이어

#module-checkers #arch-serverless

## 목적

Handlers와 Engines는 Guardian의 고급 기능을 담당합니다.
기본 체커/응답자 레이어 위에서 실시간 처리, 플레이북 실행, 자동 대응을 조율합니다.

## 주요 디렉토리

```
lambda/guardian/
├── handlers/          # 이벤트 핸들러 (각 기능별 특화)
├── engines/           # 핵심 처리 엔진
├── automation/        # 자동화 스케줄링
├── correlation/       # 이벤트 상관관계 분석
└── playbooks/         # 위협 대응 플레이북
```

## 핵심 Handlers

| 파일 | 역할 |
|------|------|
| `alert_handler.py` | 알림 라우팅 및 에스컬레이션 |
| `audit_handler.py` | 감사 로그 처리 |
| `automation_handler.py` | 자동화 작업 관리 |
| `cloudtrail_stream_handler.py` | CloudTrail 실시간 스트림 처리 |
| `correlation_handler.py` | 이벤트 상관관계 분석 |
| `cost_alert_handler.py` | 비용 알림 특화 처리 |
| `ml_handler.py` | ML 모델 추론 처리 |
| `playbook_handler.py` | 위협 대응 플레이북 실행 |
| `realtime_handler.py` | 실시간 이벤트 처리 |
| `remediation_handler.py` | 자동 대응 조율 |
| `websocket_handler.py` | WebSocket 실시간 연결 |

## 핵심 Engines

| 파일 | 역할 |
|------|------|
| `decision_engine.py` | 탐지 결과 기반 대응 결정 |
| `smart_remediation_engine.py` | 상황 인식 자동 대응 |
| `threat_correlation_engine.py` | 위협 이벤트 상관관계 분석 |
| `threat_clustering_engine.py` | 위협 클러스터링 (ML) |
| `playbook_execution_engine.py` | 플레이북 단계별 실행 |
| `auto_cleanup_engine.py` | 자동 리소스 정리 |

## 처리 흐름 예시: 위협 대응 플레이북

```
CloudTrail 이상 감지 (고빈도 API 호출)
    │
    ▼
threat_correlation_engine.py
  - 관련 이벤트 클러스터링
  - 공격 체인 식별
    │
    ▼
decision_engine.py
  - 자동 대응 여부 결정
  - 심각도 기반 에스컬레이션
    │
    ├── 자동 대응 승인 →
    │     playbook_execution_engine.py
    │       1. EC2 격리 (보안그룹 변경)
    │       2. IAM 키 비활성화
    │       3. 스냅샷 생성 (증거 보존)
    │       4. 알림 발송
    │
    └── 수동 대응 필요 →
          alert_handler.py → 에스컬레이션 알림
```

## 실시간 처리 (WebSocket)

```
CloudTrail Event
    │
    ▼
cloudtrail_stream_handler.py
    │
    ▼
realtime_correlation.py
    │
    ▼
websocket_handler.py → 실시간 대시보드 업데이트
```

## 자동화 (Automation)

| 파일 | 기능 |
|------|------|
| `predictive_scaling.py` | 비용 예측 기반 리소스 스케일링 |
| `schedule_optimizer.py` | Lambda 실행 스케줄 최적화 |
| `smart_remediation.py` | 상황별 맞춤 자동 대응 |

## Related Notes

- [[Analytics & ML]]
- [[시스템 아키텍처]]
- [[Checkers 개요]]
- [[Multi-Account]]
