---
module: checkers
path: 02-Checkers
keywords: cloudtrail, api-audit, suspicious-events, iam
---

# CloudTrailChecker — 의심 API 활동 감지

#module-checkers #api-aws

## 목적

CloudTrail에 기록된 API 호출을 분석하여 의심스러운 활동을 탐지합니다.

## 주요 파일

`lambda/guardian/checkers/cloudtrail.py`

## 의심 이벤트 목록 (SUSPICIOUS_EVENTS)

```python
SUSPICIOUS_EVENTS = {
    # IAM 권한 변경
    "CreateAccessKey", "CreateUser", "AttachUserPolicy",
    "PutUserPolicy", "CreatePolicy", "CreateRole",
    # 인프라 변경
    "CreateSecurityGroup",
    # 데이터 삭제
    "DeleteBucket", "DeleteTable",
    # 인스턴스 조작
    "TerminateInstances", "StopInstances",
    # DB 변경
    "ModifyDBInstance", "DeleteDBInstance",
}
```

## 관련 이벤트 소스 (RELEVANT_EVENT_SOURCES)

```python
RELEVANT_EVENT_SOURCES = {
    "iam.amazonaws.com",
    "ec2.amazonaws.com",
    "s3.amazonaws.com",
    "dynamodb.amazonaws.com",
    "rds.amazonaws.com",
}
```

## 탐지 로직

```
CloudTrail.lookup_events(
    LookupAttributes=[{"ReadOnly": False}],   # 쓰기 작업만
    StartTime=now - 1시간,
    EndTime=now
)
    │
    ▼
이벤트 필터링:
  - eventName ∈ SUSPICIOUS_EVENTS
  - eventSource ∈ RELEVANT_EVENT_SOURCES
    │
    ▼
의심 이벤트 목록 → CheckResult
```

> [!warning] CloudTrail 이벤트 지연
> CloudTrail 이벤트는 최대 15분 지연될 수 있습니다.
> 1시간 주기 스캔과 함께 사용하면 실질적으로 모든 이벤트를 커버합니다.

## 빈도 분석

동일 이벤트가 짧은 시간 내에 반복되면 (예: `CreateUser` 5회/시간) 공격 가능성이 높습니다.

```python
from collections import Counter
event_counts = Counter(e["EventName"] for e in events)
for event_name, count in event_counts.items():
    if count > HIGH_FREQUENCY_THRESHOLD:
        # HIGH frequency attack detected
```

## CheckResult 예시

```python
CheckResult(
    severity="HIGH",
    title="의심스러운 CloudTrail 활동",
    message="CreateAccessKey 이벤트 감지 (by: root, 3회)",
    details={
        "suspicious_events": [
            {"event_name": "CreateAccessKey", "user": "root", "count": 3}
        ]
    },
    suggested_action="해당 액세스 키를 즉시 비활성화하고 조사하세요"
)
```

## Related Notes

- [[Checkers 개요]]
- [[IAMChecker]]
- [[Handlers & Engines]]
