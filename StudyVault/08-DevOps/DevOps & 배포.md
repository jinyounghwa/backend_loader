---
module: devops
path: 08-DevOps
keywords: terraform, docker-compose, localstack, sam, deployment, ci-cd
---

# DevOps & 배포 — 인프라 및 배포

#arch-serverless #config-env

## 목적

AWS Guardian의 인프라 정의, 로컬 개발환경, 배포 파이프라인을 관리합니다.

## 주요 파일

```
backend_loader/
├── terraform/
│   ├── main.tf           # 공통 설정, 프로바이더
│   ├── lambda.tf         # Lambda 함수 정의
│   ├── eventbridge.tf    # EventBridge 스케줄 룰
│   ├── dynamodb.tf       # DynamoDB 테이블
│   └── iam.tf            # IAM 역할 및 정책
├── docker-compose.yml             # 로컬 개발환경
├── docker-compose.production.yml  # 프로덕션 설정
├── build-lambda-local.sh          # 로컬 Lambda 빌드
└── template.yaml                  # AWS SAM 템플릿 (추정)
```

## 로컬 개발환경 (LocalStack)

```bash
# 1. LocalStack 시작
docker-compose up -d

# 확인
docker-compose ps
curl http://localhost:4566/_localstack/health

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 테스트 실행 (LocalStack에 연결)
AWS_ENV=localstack python -m pytest tests/ -v
```

## docker-compose.yml 구조

```yaml
services:
  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"    # LocalStack 메인 포트
    environment:
      - SERVICES=lambda,dynamodb,s3,ec2,ssm,cloudtrail,iam,ce
      - DEFAULT_REGION=us-east-1
    volumes:
      - "./localstack-data:/var/lib/localstack"  # 상태 유지
```

## Terraform 인프라 코드

### lambda.tf 핵심 구조

```hcl
resource "aws_lambda_function" "guardian" {
  function_name = "aws-guardian"
  runtime       = "python3.12"
  handler       = "guardian.handler.lambda_handler"
  timeout       = 300    # 5분 (모든 체커 실행 시간)
  memory_size   = 256    # MB

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.events.name
      AWS_ENV             = "production"
      # 시크릿은 SSM에서 런타임에 로드
      SSM_TELEGRAM_BOT_TOKEN_PATH = "/guardian/telegram/token"
    }
  }
}
```

### eventbridge.tf 핵심 구조

```hcl
resource "aws_cloudwatch_event_rule" "guardian_schedule" {
  name                = "guardian-hourly"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "guardian" {
  rule = aws_cloudwatch_event_rule.guardian_schedule.name
  arn  = aws_lambda_function.guardian.arn
}
```

### dynamodb.tf 핵심 구조

```hcl
resource "aws_dynamodb_table" "events" {
  name           = "aws-guardian-events"
  billing_mode   = "PAY_PER_REQUEST"    # 서버리스 비용 모델
  hash_key       = "event_id"
  range_key      = "timestamp"

  ttl {
    attribute_name = "ttl"
    enabled        = true    # 30일 자동 만료
  }
}
```

## AWS SAM 배포

```bash
# 빌드
sam build

# 첫 배포 (대화형 설정)
sam deploy --guided

# 이후 배포 (저장된 설정 사용)
sam deploy
```

## IAM 역할 최소 권한 원칙

```
guardian-lambda-role 권한:
  ✅ ce:GetCostAndUsage          (비용 조회)
  ✅ ec2:DescribeInstances        (EC2 조회)
  ✅ ec2:StopInstances            (자동 대응)
  ✅ s3:ListBuckets               (S3 조회)
  ✅ s3:PutPublicAccessBlock      (자동 대응)
  ✅ cloudtrail:LookupEvents      (감사 로그 조회)
  ✅ iam:ListUsers                (IAM 조회)
  ✅ dynamodb:PutItem/Query       (이벤트 저장)
  ✅ ssm:GetParameter             (설정 조회)
  ✅ sts:AssumeRole               (멀티 계정)
  ❌ s3:DeleteBucket              (불필요)
  ❌ iam:CreateUser               (불필요, 위험)
```

## 비용 최적화

| 리소스 | 무료 티어 | Guardian 예상 사용량 |
|--------|----------|-------------------|
| Lambda | 월 100만 호출, 400,000 GB-초 | ~720 호출/월 (1회/시간) |
| DynamoDB | 25GB 저장, 25RCU/25WCU | 낮은 사용량 |
| SSM Parameter | 표준 파라미터 무료 | 5-10개 파라미터 |
| CloudWatch Logs | 5GB/월 무료 | 낮은 사용량 |

## Related Notes

- [[시스템 아키텍처]]
- [[Config 모듈]]
- [[Guardian Handler]]
