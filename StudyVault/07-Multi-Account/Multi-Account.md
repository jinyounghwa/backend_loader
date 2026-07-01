---
module: multi-account
path: 07-Multi-Account
keywords: multi-account, sts, assume-role, organizations, cross-account
---

# Multi-Account — 다중 AWS 계정 지원

#module-checkers #api-aws

## 목적

단일 마스터 계정에서 여러 AWS 계정을 동시에 감시합니다.
AWS Organizations와 STS AssumeRole을 활용합니다.

## 주요 디렉토리

```
lambda/guardian/
├── multi_account/              # 다중 계정 핵심 로직
│   └── ...
├── multiaccount/               # 추가 다중 계정 지원
│   └── ...
├── aggregators/
│   └── multi_account_cost_aggregator.py  # 계정별 비용 집계
└── handlers/
    └── multi_account_handler.py          # 다중 계정 처리 핸들러
```

## 활성화 조건

```bash
# 환경변수 설정
ORGANIZATIONS_ENABLED=true
ORGANIZATION_ARN=arn:aws:organizations::123456789012:organization/o-xxxx
CROSS_ACCOUNT_ROLE_NAME=aws-guardian-cross-account-role
```

## STS AssumeRole 흐름

```
마스터 계정 Lambda
    │
    ├── STS.assume_role(
    │     RoleArn="arn:aws:iam::{account_id}:role/aws-guardian-cross-account-role",
    │     RoleSessionName="guardian-{timestamp}"
    │   )
    │       │
    │       ▼
    │   임시 자격증명 (15분 유효)
    │   {AccessKeyId, SecretAccessKey, SessionToken}
    │       │
    │       ▼
    │   boto3.client("ec2",
    │     aws_access_key_id=...,
    │     aws_secret_access_key=...,
    │     aws_session_token=...
    │   )
    │       │
    │       ▼
    │   대상 계정 리소스 조회
    │
    └── 모든 계정 결과 집계
```

## 크로스 계정 IAM 역할 설정

```json
// 각 대상 계정에 생성할 신뢰 정책
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::{master-account-id}:role/guardian-lambda-role"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

## 비용 집계

```python
# multi_account_cost_aggregator.py
class MultiAccountCostAggregator:
    def aggregate(self, account_ids: List[str]) -> Dict:
        results = {}
        for account_id in account_ids:
            credentials = assume_role(account_id)
            cost_checker = CostChecker(
                clients=build_clients(credentials),
                account_id=account_id
            )
            results[account_id] = cost_checker.check()
        return results
```

## 설정 활성화 여부 확인

```python
# 다중 계정 기능이 비활성화된 경우 단일 계정으로 동작
if not Config.is_organizations_enabled():
    return single_account_check()
```

> [!tip] 점진적 도입
> `ORGANIZATIONS_ENABLED=false` (기본값)로 시작하여 단일 계정 테스트 후
> 다중 계정으로 확장하는 것을 권장합니다.

## Related Notes

- [[시스템 아키텍처]]
- [[Analytics & ML]]
- [[Config 모듈]]
- [[Checkers 개요]]
