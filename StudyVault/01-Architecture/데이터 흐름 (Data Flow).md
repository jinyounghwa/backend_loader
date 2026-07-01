---
module: architecture
path: 01-Architecture
keywords: data-flow, dynamodb, ssm, checkresult
---

# 데이터 흐름 (Data Flow)

#arch-serverless #module-storage #module-config

## 설정 데이터 흐름

```
환경변수 (Lambda 설정)
    │
    ├── AWS_ENV=localstack  →  boto3 엔드포인트: http://localhost:4566
    ├── AWS_ENV=production  →  boto3 실제 AWS 사용
    │
    ├── TELEGRAM_BOT_TOKEN  →  직접 사용 (개발/테스트)
    │   또는
    │   SSM_TELEGRAM_BOT_TOKEN_PATH  →  SSM.get_parameter()  →  실제 토큰 (프로덕션)
    │
    └── COST_THRESHOLD=10.0  →  CostChecker.threshold
```

## 체커 데이터 흐름

```
AWS API 호출 (boto3)
    │
    ├── Cost Explorer API
    │       │
    │       ▼
    │   오늘/어제 비용 조회 → $10 초과? → CheckResult(severity=HIGH)
    │
    ├── EC2 API (describe_instances, describe_security_groups)
    │       │
    │       ▼
    │   인스턴스 목록 → 비인가 리전? / 0.0.0.0/0 포트? → CheckResult
    │
    └── S3 API (list_buckets, get_bucket_acl, get_bucket_policy)
            │
            ▼
        버킷 목록 → 퍼블릭 ACL/Policy? → CheckResult
```

## DynamoDB 저장 스키마

```
테이블: aws-guardian-events

파티션키: event_id (UUID)
정렬키:   timestamp (ISO8601)

속성:
  event_type: "cost_anomaly" | "ec2_anomaly" | "s3_anomaly" | ...
  severity:   "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  details:    {...}  (체커별 상세 정보)
  account_id: "current" | "123456789012"
  ttl:        timestamp + 30일 (자동 만료)
```

## 알림 데이터 변환

```
CheckResult (내부 형식)
    │
    ▼
AlertMessage (responders/alert_formatter.py)
  ├── check_name: "Cost" | "EC2" | "S3"
  ├── severity: CheckResult.severity
  ├── title: CheckResult.title
  ├── items: [{"label": ..., "details": [...]}]
  ├── summary_line: 요약 한 줄
  └── suggested_action: CheckResult.suggested_action
    │
    ├──▶ TelegramResponder._render_alert()
    │       → HTML 포맷 문자열
    │       → POST https://api.telegram.org/bot{token}/sendMessage
    │
    └──▶ DiscordResponder._render_alert_embed()
            → Discord Embed JSON {"color": ..., "fields": [...]}
            → POST {webhook_url}
```

## 멀티 계정 데이터 흐름 (고급)

```
마스터 계정 Lambda
    │
    ├── STS.assume_role("arn:aws:iam::{account_id}:role/aws-guardian-cross-account-role")
    │       │
    │       ▼
    │   임시 자격증명 (AccessKeyId, SecretAccessKey, SessionToken)
    │       │
    │       ▼
    │   대상 계정 boto3 클라이언트 생성
    │       │
    │       ▼
    │   체커 실행 (account_id 파라미터 포함)
    │
    └── 결과 집계 → 통합 알림 발송
```

## Related Notes

- [[시스템 아키텍처]]
- [[DynamoDB Storage]]
- [[Config 모듈]]
- [[Responders 개요]]
- [[Multi-Account]]
