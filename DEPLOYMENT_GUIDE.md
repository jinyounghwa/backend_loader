# AWS Guardian: AI 기반 클라우드 보안 및 비용 감시 시스템 개발 및 배포 가이드

이 문서는 LocalStack을 활용한 로컬 개발부터 Zhipu GLM AI를 통합한 실시간 AWS 감시 시스템의 구축, 테스트 및 배포 과정을 상세히 설명합니다.

---

## 1. 프로젝트 아키텍처

AWS Guardian은 서버리스 아키텍처를 기반으로 하며, AI를 활용하여 클라우드 자원의 이상 징후를 탐지하고 자동 대응합니다.

```
[Amazon EventBridge] -- "Scheduled (1h)" --> [Lambda: Guardian Handler]
                                                    |
                         ___________________________|___________________________
                        |            |              |
                        v            v              v
                  [Cost Explorer] [EC2 Check] [S3 Check]
                        |            |              |
                        |____________|______________|
                                     |
                    _________________|_________________
                   |                                   |
                   v                                   v
            [DynamoDB Logs]              [Zhipu GLM AI Analysis]
                   |                                   |
                   |___________________________________|
                            |
        ____________________|____________________
       |                    |                    |
       v                    v                    v
  [Telegram Bot]    [Discord Webhook]   [Auto-Remediation]
                                          - Stop EC2
                                          - Block S3 Public
```

### 핵심 구성 요소
- **Lambda Handler**: 모든 모니터링 로직을 조율하는 메인 엔진
- **Checkers**: 비용(Cost), 컴퓨팅(EC2), 스토리지(S3)의 상태를 검사
- **GLM Analyzer**: 탐지된 이상 징후를 분석하여 심각도 평가 및 권고안 생성
- **Responders**: 다중 채널(Telegram, Discord) 알림 및 즉각적인 보안 조치 수행

---

## 2. LocalStack 환경 설정

로컬에서 AWS 인프라를 시뮬레이션하기 위해 LocalStack을 사용합니다.

### 전제 조건
- Docker 및 Docker Compose 설치
- Python 3.9+ 및 `pip`

### LocalStack 기동
```bash
docker-compose up -d
```

### 환경 변수 설정 (.env)
```bash
LOCALSTACK_ENDPOINT=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=aws-guardian-events
```

### 로컬 리소스 초기화
```bash
python3 scripts/init_localstack.py
```

생성되는 리소스:
- DynamoDB 테이블: `aws-guardian-events`
- S3 버킷: `test-bucket-1`, `test-bucket-2`, `public-test-bucket`
- EC2 인스턴스: SSH 포트 노출된 테스트 인스턴스
- 보안 그룹: SSH 0.0.0.0/0 오픈 (노출 테스트용)

---

## 3. GLM API 통합 가이드

Zhipu AI의 GLM-4 모델을 사용하여 보안 위협과 비용 이상을 분석합니다.

### API 키 발급
1. [Zhipu AI 오픈 플랫폼](https://open.bigmodel.cn/)에 가입합니다.
2. API Keys 메뉴에서 키를 생성합니다.
3. 환경 변수로 설정: `export GLM_API_KEY=your_api_key_here`

### 시스템 통합
시스템은 `GLM_API_KEY` 환경 변수를 자동으로 감지하여 활성화됩니다.

**분석 범위:**
- 비용 급증 원인 분석
- 노출된 EC2 위험도 평가  
- S3 공개 설정 준수 여부 점검
- 자동 수정 단계 생성
- 24시간 AI 인사이트 요약 보고서

### 테스트
```bash
python3 -m pytest tests/test_glm_integration.py -v
```

---

## 4. 로컬 테스트 실행 방법

### 의존성 설치
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Guardian Handler 실행
```bash
export LOCALSTACK_ENDPOINT=http://localhost:4566
export GLM_API_KEY=5fafb543164c452bacbb13aaafdd31a4.yEj71FHKcqNB8o2f
cd lambda
python3 guardian/handler.py
```

### 단위 테스트
```bash
# 비용 체커
python3 -m pytest tests/test_cost.py -v

# EC2 체커
python3 -m pytest tests/test_ec2.py -v

# S3 체커
python3 -m pytest tests/test_s3.py -v

# GLM 통합
python3 -m pytest tests/test_glm_integration.py -v
```

---

## 5. AWS 배포 단계별 가이드

### 1단계: 코드 패키징
```bash
cd lambda
zip -r ../lambda-package.zip guardian/
zip -r ../discord-package.zip discord_webhook/
```

### 2단계: IAM 역할 생성
Lambda에 부여할 권한:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
        "ec2:DescribeSecurityGroups",
        "ec2:StopInstances",
        "s3:ListAllMyBuckets",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicy",
        "s3:GetPublicAccessBlock",
        "s3:PutPublicAccessBlock",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "ssm:GetParameter",
        "ssm:PutParameter",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3단계: Lambda 함수 생성
```bash
aws lambda create-function \
  --function-name aws-guardian-monitor \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-guardian-role \
  --handler guardian.handler.lambda_handler \
  --zip-file fileb://lambda-package.zip \
  --timeout 300 \
  --memory-size 256 \
  --environment Variables={
    TELEGRAM_BOT_TOKEN=your_token,
    TELEGRAM_CHAT_ID=your_chat_id,
    DISCORD_WEBHOOK_URL=your_webhook_url,
    GLM_API_KEY=your_glm_key
  }
```

### 4단계: EventBridge 규칙 생성
```bash
aws events put-rule \
  --name aws-guardian-hourly \
  --schedule-expression "rate(1 hour)" \
  --state ENABLED

aws events put-targets \
  --rule aws-guardian-hourly \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT_ID:function:aws-guardian-monitor","RoleArn"="arn:aws:iam::ACCOUNT_ID:role/eventbridge-role"
```

### 5단계: DynamoDB 테이블 생성
```bash
aws dynamodb create-table \
  --table-name aws-guardian-events \
  --attribute-definitions AttributeName=timestamp,AttributeType=S AttributeName=event_type,AttributeType=S \
  --key-schema AttributeName=timestamp,KeyType=HASH AttributeName=event_type,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

---

## 6. Terraform 설정 설명

### 주요 리소스
```hcl
# Lambda 함수
resource "aws_lambda_function" "guardian" {
  function_name = "aws-guardian-monitor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "guardian.handler.lambda_handler"
  runtime       = "python3.12"
  environment {
    variables = {
      GLM_API_KEY = var.glm_api_key
      TELEGRAM_BOT_TOKEN = var.telegram_bot_token
      DISCORD_WEBHOOK_URL = var.discord_webhook_url
    }
  }
}

# EventBridge 규칙
resource "aws_cloudwatch_event_rule" "hourly" {
  name = "aws-guardian-hourly"
  schedule_expression = "rate(1 hour)"
}

# DynamoDB 테이블
resource "aws_dynamodb_table" "events" {
  name = "aws-guardian-events"
  hash_key = "timestamp"
  range_key = "event_type"
  billing_mode = "PAY_PER_REQUEST"
  
  attribute {
    name = "timestamp"
    type = "S"
  }
  
  attribute {
    name = "event_type"
    type = "S"
  }
}
```

### 배포
```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply
```

---

## 7. 모니터링 및 대시보드 사용법

### Discord 명령어
```
/status              - 현재 상태 확인
/stop <instance-id>  - EC2 인스턴스 중지
/budget set <amount> - 비용 임계값 설정
/history             - 최근 이벤트 로그
```

### 실시간 알림
- **Discord**: 리치 임베드 형식으로 시각화된 경고
- **Telegram**: AI 요약 보고서 및 자동 조치 결과

### 이벤트 로그 조회
```bash
aws dynamodb scan \
  --table-name aws-guardian-events \
  --filter-expression "event_type = :type" \
  --expression-attribute-values '{":type":{"S":"cost"}}'
```

---

## 8. 문제 해결 가이드

### Lambda 로그 확인
```bash
aws logs tail /aws/lambda/aws-guardian-monitor --follow
```

### DynamoDB 테이블 상태 확인
```bash
aws dynamodb describe-table --table-name aws-guardian-events
```

### GLM API 연결 테스트
```bash
python3 -c "
from lambda.guardian.responders.glm import GLMAnalyzer
analyzer = GLMAnalyzer('your_api_key')
print(f'GLM Available: {analyzer.is_available}')
"
```

### 일반적인 에러 및 해결책

| 문제 | 해결 방법 |
|------|---------|
| Cost Explorer 데이터 부재 | API 활성화 후 24시간 대기 필요 |
| GLM API 400 에러 | API 키 형식 확인, 요청 형식 검증 |
| EC2 중지 권한 에러 | IAM Role에 `ec2:StopInstances` 권한 확인 |
| S3 조치 실패 | `s3:PutPublicAccessBlock` 권한 확인 |
| LocalStack 연결 실패 | 4566 포트 열림 상태 확인 |

---

## 9. 성능 및 비용 최적화

### CloudWatch Logs 비용 감소
```hcl
resource "aws_cloudwatch_log_group" "guardian" {
  name              = "/aws/lambda/aws-guardian-monitor"
  retention_in_days = 7  # 7일 자동 삭제
}
```

### DynamoDB 비용 최적화
- PAY_PER_REQUEST 모드 사용 (예측 불가능한 트래픽에 최적)
- TTL 설정으로 자동 데이터 삭제

### Lambda 비용 추정
- 월 720회 실행 (1시간마다)
- 각 실행 시간: 30초
- 메모리: 256MB
- **월 예상 비용**: < $0.50 (무료 티어 범위 내)

---

## 10. 보안 모범 사례

### 환경 변수 관리
- AWS Secrets Manager 또는 SSM Parameter Store에 민감한 정보 저장
- Lambda 환경 변수로 일반 설정만 관리

### IAM 최소 권한 원칙
- Checker/Responder별로 필요한 권한만 부여
- 와일드카드 리소스 사용 최소화

### 암호화
- DynamoDB 암호화 활성화
- S3 버킷 암호화 의무화
- Lambda 환경 변수 암호화

---

*본 문서는 AWS Guardian v1.0.0 기준으로 작성되었습니다.*
*Last Updated: 2026-04-26*
