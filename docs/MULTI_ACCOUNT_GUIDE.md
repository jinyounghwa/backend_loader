# 멀티 계정 감시 가이드 (등록부터 사용까지)

AWS Guardian 하나로 **여러 AWS 계정을 동시에 감시**하는 방법을 처음부터 끝까지 설명합니다.

## 아키텍처

```
┌─ 허브 계정 (Guardian Lambda 실행) ─────────────────────┐
│  EventBridge (1시간) → Guardian Lambda                  │
│      │  ① 계정 목록 확보 (GUARDIAN_ACCOUNTS 또는 Orgs)  │
│      │  ② 계정마다 sts:AssumeRole                       │
│      ▼                                                  │
│  [계정별 비용/EC2/S3/CloudTrail/IAM/GuardDuty 체크]     │
│      → DynamoDB 저장 → Telegram/Discord 알림(계정 표기) │
└─────────────────────────────────────────────────────────┘
          │ AssumeRole                │ AssumeRole
          ▼                           ▼
┌─ 멤버 계정 A ──────────┐  ┌─ 멤버 계정 B ──────────┐
│ aws-guardian-           │  │ aws-guardian-           │
│ cross-account-role      │  │ cross-account-role      │
│ (읽기 + EC2중지/S3차단) │  │ (읽기 + EC2중지/S3차단) │
└─────────────────────────┘  └─────────────────────────┘
```

- **허브 계정**: Guardian Lambda가 배포되는 계정 1개. 알림·저장·스케줄링을 담당합니다.
- **멤버 계정**: 감시 대상 계정들. Lambda 없이 **IAM 역할 1개만** 만들면 됩니다.

계정 목록을 얻는 방식은 두 가지이며 혼용 시 ①이 우선합니다.

| 방식 | 대상 | 설정 |
|------|------|------|
| ① 수동 등록 | 독립 계정들 (Organizations 불필요) | `GUARDIAN_ACCOUNTS` 환경변수 |
| ② 자동 탐색 | AWS Organizations 조직 | `ORGANIZATIONS_ENABLED=true` |

---

## 1단계 — 허브 계정에 Guardian 배포

```bash
# 허브 계정 자격증명으로
cd terraform
terraform init
terraform apply \
  -var="telegram_bot_token_ssm_path=/aws-guardian/telegram-bot-token" \
  -var="aws_region=ap-northeast-2"
```

허브 Lambda 역할에는 멀티 계정에 필요한 권한이 이미 포함되어 있습니다:
- `sts:AssumeRole` → `arn:aws:iam::*:role/aws-guardian-cross-account-role` 한정
- `organizations:ListAccounts` (② 방식용)

배포 후 허브 계정 ID를 확인해 둡니다:

```bash
aws sts get-caller-identity --query Account --output text
# 예: 111122223333
```

## 2단계 — 멤버 계정마다 역할 생성

각 멤버 계정에서 동봉된 CloudFormation 템플릿 하나만 배포합니다.

```bash
# 멤버 계정 자격증명으로 (계정마다 반복)
aws cloudformation deploy \
  --template-file docs/templates/guardian-member-role.yaml \
  --stack-name aws-guardian-member-role \
  --parameter-overrides HubAccountId=111122223333 \
  --capabilities CAPABILITY_NAMED_IAM
```

이 역할이 부여하는 권한은 허브와 동일한 최소권한입니다:
**읽기 전용 감시**(EC2/S3/비용/CloudTrail/IAM/GuardDuty 조회) + **자동 대응 2종**(`ec2:StopInstances`, `s3:PutPublicAccessBlock`).

> **보안 강화(선택):** `ExternalId=<비밀문자열>` 파라미터를 추가하고, 허브 Lambda에
> `CROSS_ACCOUNT_EXTERNAL_ID=<같은 문자열>` 환경변수를 설정하면 혼동 대리인
> (confused deputy) 공격을 방어합니다.
>
> **조직 전체 일괄 배포:** Organizations를 쓴다면 이 템플릿을 CloudFormation
> **StackSets**로 전 계정에 한 번에 배포할 수 있습니다.

## 3단계 — 감시할 계정 등록

### 방식 ① 수동 등록 (권장 시작점)

허브 Lambda의 환경변수 `GUARDIAN_ACCOUNTS`에 JSON 배열로 등록합니다.
`"current"`는 허브 계정 자신을 뜻합니다(역할 위임 없이 직접 조회).

```bash
aws lambda update-function-configuration \
  --function-name aws-guardian-checker \
  --environment 'Variables={
    AWS_ENV=production,
    GUARDIAN_ACCOUNTS=[
      {"account_id": "current",      "account_name": "Hub"},
      {"account_id": "222233334444", "account_name": "Production"},
      {"account_id": "555566667777", "account_name": "Staging"}
    ]
  }'
```

- account_id는 12자리 숫자만 유효합니다. 형식이 틀린 항목은 **경고 로그 후 건너뛰고** 나머지 계정 감시는 계속됩니다.
- 계정 추가/제거 = 이 환경변수 수정이 전부입니다(재배포 불필요).

### 방식 ② Organizations 자동 탐색

관리 계정(또는 위임된 관리자)에 허브를 배포한 경우:

```bash
aws lambda update-function-configuration \
  --function-name aws-guardian-checker \
  --environment 'Variables={AWS_ENV=production,ORGANIZATIONS_ENABLED=true}'
```

조직의 모든 ACTIVE 계정이 자동으로 감시 대상이 됩니다. 신규 계정도 역할(2단계)만 만들어지면 다음 주기부터 자동 포함됩니다.

## 4단계 — 동작 확인

```bash
# 수동 1회 실행
aws lambda invoke --function-name aws-guardian-checker \
  --payload '{"check_type": "all"}' /tmp/out.json && cat /tmp/out.json | python3 -m json.tool | head -30
```

정상이라면:
- 응답의 `"accounts"` 배열에 등록한 계정 수만큼 항목이 있고, `"checks"` 키가 `cost_222233334444`처럼 **계정 ID 접미사**로 나뉩니다.
- CloudWatch Logs에 `Running checks for account: Production (222233334444)` / `Assumed role for account ...`가 보입니다.
- 역할 위임 실패 시 해당 계정만 `Skipping account ... role assumption failed`로 건너뜁니다(다른 계정 감시는 계속).

## 5단계 — 일상 사용

**Telegram / Discord 알림** — 모든 알림에 계정이 표기됩니다:

```
🟠 ⚠️ EC2: Security Issues Detected
🏢 Production (222233334444)
━━━━━━━━━━━━━━━━━━━
🌍 Unauthorized Region: ap-southeast-1
  └ i-0abc123def456
⚡ 1 instance auto-stopped
```

**Discord 명령어:**

| 명령 | 동작 |
|------|------|
| `/status` | 전 계정 종합 상태 (비용/EC2/S3 이슈 수) |
| `/stop instance_id:i-xxx region:ap-northeast-2` | EC2 수동 중지 |
| `/budget set 20` | 일일 비용 임계값 변경 — SSM에 저장되어 **전 계정 공통** 적용 |
| `/history` | 최근 24시간 이벤트 (계정 ID 포함) |

**자동 대응**은 계정 구분 없이 동일하게 동작합니다: 이상 EC2 → 해당 멤버 계정 자격증명으로 Stop, 퍼블릭 S3 → 해당 계정에서 차단. 모든 대응은 DynamoDB에 `account_id`와 함께 기록됩니다.

## 트러블슈팅

| 증상 | 원인/해결 |
|------|-----------|
| `Skipping account ... role assumption failed` | 2단계 역할 미생성, `RoleName` 불일치, 또는 ExternalId 불일치. 멤버 계정에서 스택 상태와 `HubAccountId` 확인 |
| 멤버 계정 결과가 허브와 동일 | `GUARDIAN_ACCOUNTS` JSON 문법 오류(로그에 `not valid JSON` 경고) — 항목이 무시되고 단일 계정 모드로 동작 중 |
| Organizations 모드에서 계정이 안 잡힘 | 허브가 관리 계정이 아니거나 `organizations:ListAccounts` 권한 누락. 로그의 `Failed to get accounts from Organizations` 확인 |
| 비용이 계정마다 0 | 멤버 계정에서 Cost Explorer 최초 활성화까지 최대 24시간 소요 |
| 특정 계정만 감시 제외하고 싶음 | 방식 ①로 전환해 원하는 계정만 나열 (①이 ②보다 우선) |

## 요금 참고

- 멤버 계정 추가 비용: **IAM 역할뿐이므로 0원.** AssumeRole/Describe API 호출도 무료입니다.
- 유일한 과금 항목: **Cost Explorer API** — `GetCostAndUsage` 요청당 $0.01. 계정 10개 × 1시간 주기 ≈ 월 $72이므로, 계정이 많다면 EventBridge 주기를 조정하거나 `check_type=security`(비용 체크 제외)와 병행하는 구성을 권합니다.
