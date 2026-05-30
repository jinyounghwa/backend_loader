# AWS Guardian: 완벽한 시작 가이드 (시작→배포→운영)

**이 가이드는 처음부터 끝까지 AWS Guardian을 배포하고 운영할 때 필요한 모든 단계를 다룹니다.**

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [Telegram 봇 설정](#2-telegram-봇-설정)
3. [AWS 계정 및 권한 설정](#3-aws-계정-및-권한-설정)
4. [로컬 개발 환경 구성](#4-로컬-개발-환경-구성)
5. [Lambda 함수 배포](#5-lambda-함수-배포)
6. [웹 대시보드 배포](#6-웹-대시보드-배포)
7. [첫 실행 및 테스트](#7-첫-실행-및-테스트)
8. [운영 및 모니터링](#8-운영-및-모니터링)
9. [트러블슈팅](#9-트러블슈팅)

---

## 1. 사전 준비

### 1.1 필요한 것들

| 항목 | 목적 | 설치 |
|------|------|------|
| **AWS 계정** | Lambda, DynamoDB, EventBridge 호스팅 | [aws.amazon.com](https://aws.amazon.com) |
| **AWS CLI v2** | AWS 서비스 제어 | `pip install awscliv2` |
| **Python 3.12** | Lambda 런타임 | [python.org](https://www.python.org/downloads/) |
| **Node.js 18+** | 웹 대시보드 | [nodejs.org](https://nodejs.org) |
| **Git** | 코드 관리 | `brew install git` (Mac) |
| **SAM CLI** | Lambda 배포 도구 | `pip install aws-sam-cli` |
| **Docker** | 로컬 Lambda 테스트 | [docker.com](https://www.docker.com) |

### 1.2 AWS 계정 설정

```bash
# 1단계: AWS CLI 설정
aws configure
# 다음 정보 입력:
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region: ap-northeast-1  (또는 원하는 리전)
# Default output format: json

# 2단계: 계정 확인
aws sts get-caller-identity
# 출력 예:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

### 1.3 비용 확인

**무료 티어 범위 (월):**
- Lambda: 1,000,000 호출 무료 ✅
- DynamoDB: 25GB 스토리지 무료 ✅
- CloudWatch: 5GB 로그 무료 ✅
- EventBridge: 처음 100만 이벤트 무료 ✅

**예상 월 비용: $0 ~ $2.20** (무료 티어 활용 시)

> **주의**: 이 비용 추정은 설계 기준입니다. 실제 AWS 환경에서의 검증은 아직 이루어지지 않았습니다.

---

## 2. Telegram 봇 설정

### 2.1 Telegram 봇 생성

```
1단계: Telegram 앱 열기
2단계: @BotFather 검색 및 채팅 시작
3단계: /newbot 입력
4단계: 봇 이름 입력 (예: AWS Guardian Bot)
5단계: 봇 username 입력 (예: aws_guardian_bot)

🤖 봇 생성 완료!
BotFather가 API Token을 제공합니다:
→ 복사: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ-1234567890

⚠️ 이 토큰을 안전하게 보관하세요!
```

### 2.2 Telegram 채널 설정

```bash
# 1단계: 그룹 또는 채널 생성
Telegram → New Channel → Private Channel 생성
채널명: aws-guardian-alerts

# 2단계: 봇을 채널에 추가
봇 링크: https://t.me/[YOUR_BOT_USERNAME]
→ 채널에 초대 → Admin 권한 부여

# 3단계: Chat ID 확인
다음 스크립트로 Chat ID를 확인할 수 있습니다:

curl "https://api.telegram.org/bot[YOUR_BOT_TOKEN]/getMe"

# 또는 봇에 메시지를 보낸 후:
curl "https://api.telegram.org/bot[YOUR_BOT_TOKEN]/getUpdates"

응답 예:
{
  "ok": true,
  "result": [
    {
      "update_id": 123456789,
      "message": {
        "chat": {
          "id": -987654321,  # ← 이것이 Chat ID
          "title": "aws-guardian-alerts"
        }
      }
    }
  ]
}
```

### 2.3 환경 변수 저장

```bash
# AWS Systems Manager Parameter Store에 저장
aws ssm put-parameter \
  --name /guardian/telegram/bot-token \
  --value "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ-1234567890" \
  --type SecureString

aws ssm put-parameter \
  --name /guardian/telegram/chat-id \
  --value "-987654321" \
  --type SecureString
```

---

## 3. AWS 계정 및 권한 설정

### 3.1 IAM 역할 생성

```bash
# 1단계: Lambda 실행 역할 생성
aws iam create-role \
  --role-name GuardianLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# 2단계: 필요한 정책 추가
aws iam put-role-policy \
  --role-name GuardianLambdaRole \
  --policy-name GuardianPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ec2:Describe*",
          "ec2:StopInstances",
          "s3:ListAllMyBuckets",
          "s3:GetBucketPolicy",
          "s3:GetBucketPublicAccessBlock",
          "s3:PutBucketPublicAccessBlock",
          "ce:GetCostAndUsage",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "ssm:GetParameter"
        ],
        "Resource": "*"
      }
    ]
  }'

# 역할 ARN 확인
aws iam get-role --role-name GuardianLambdaRole --query 'Role.Arn'
# 출력: arn:aws:iam::123456789012:role/GuardianLambdaRole
```

### 3.2 DynamoDB 테이블 생성

```bash
# 이벤트 로그 테이블
aws dynamodb create-table \
  --table-name guardian-events \
  --attribute-definitions \
    AttributeName=event_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=event_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# 자동 대응 로그 테이블
aws dynamodb create-table \
  --table-name guardian-actions \
  --attribute-definitions \
    AttributeName=action_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=action_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# 테이블 생성 확인
aws dynamodb list-tables
```

### 3.3 CloudWatch 로그 그룹 생성

```bash
aws logs create-log-group --log-group-name /aws/lambda/guardianChecker
aws logs create-log-group --log-group-name /aws/lambda/guardianWeb
aws logs create-log-group --log-group-name /aws/guardian/application
```

---

## 4. 로컬 개발 환경 구성

### 4.1 프로젝트 클론

```bash
# 1단계: 저장소 클론
git clone https://github.com/your-org/aws-guardian.git
cd aws-guardian

# 2단계: 브랜치 확인
git branch -a
git checkout main  # 또는 main 브랜치
```

### 4.2 Python 환경 설정

```bash
# 1단계: Python 가상 환경 생성
python3.12 -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는 Windows:
# venv\Scripts\activate

# 2단계: 의존성 설치
cd lambda
pip install -r requirements.txt

# 3단계: 설치 확인
pip list | grep -E "boto|aioboto|redis|pydantic|scikit"
```

### 4.3 Node.js 환경 설정

```bash
# 1단계: 패키지 설치
cd apps/web
npm install

# 2단계: 환경 변수 설정
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:3000
NEXT_PUBLIC_REFRESH_INTERVAL=30000
EOF

# 3단계: 개발 서버 실행
npm run dev
# 브라우저: http://localhost:3000/dashboard
```

---

## 5. Lambda 함수 배포

### 5.1 SAM 템플릿 확인

```bash
# sam.yaml 파일 확인
cat sam.yaml

# 기본 구조:
# - guardianChecker: 메인 감시 함수 (1시간마다)
# - guardianWeb: API 제공 함수
# - remediationEngine: 자동 대응 함수
```

### 5.2 로컬 테스트

```bash
# 1단계: Lambda 함수 로컬 테스트
sam local invoke guardianChecker -e events/test-event.json

# 2단계: API 로컬 테스트
sam local start-api
# http://localhost:3000/guardian/status

# 3단계: 결과 확인
curl http://localhost:3000/guardian/status
```

### 5.3 AWS에 배포

```bash
# 1단계: S3 버킷 생성 (SAM 아티팩트용)
aws s3 mb s3://guardian-deploy-$(date +%s) --region ap-northeast-1

# 2단계: SAM 빌드
sam build

# 3단계: SAM 배포
sam deploy \
  --guided \
  --stack-name guardian-stack \
  --region ap-northeast-1 \
  --capabilities CAPABILITY_IAM

# 배포 중 입력 예:
# Stack Name: guardian-stack
# AWS Region: ap-northeast-1
# Confirm changes before deploy: Y
# Allow SAM CLI IAM role creation: Y
# Disable rollback: N
# Save parameters to defaults: Y

# 4단계: 배포 확인
aws cloudformation describe-stacks --stack-name guardian-stack --query 'Stacks[0].StackStatus'
# 출력: CREATE_COMPLETE
```

### 5.4 환경 변수 설정

```bash
# Lambda 함수에 환경 변수 설정
aws lambda update-function-configuration \
  --function-name guardianChecker \
  --environment Variables='{
    "CACHE_BACKEND":"redis",
    "TELEGRAM_BOT_TOKEN":"123456789:ABCdefGHIjklMNOpqrSTUvwxYZ-1234567890",
    "TELEGRAM_CHAT_ID":"-987654321",
    "DYNAMODB_TABLE_EVENTS":"guardian-events",
    "DYNAMODB_TABLE_ACTIONS":"guardian-actions",
    "COST_THRESHOLD":"10.0",
    "AWS_REGION":"ap-northeast-1"
  }'

# 설정 확인
aws lambda get-function-configuration --function-name guardianChecker --query 'Environment'
```

### 5.5 EventBridge 스케줄러 설정

```bash
# 1시간마다 실행하는 EventBridge Rule 생성
aws events put-rule \
  --name guardian-hourly-check \
  --schedule-expression "rate(1 hour)" \
  --state ENABLED

# Lambda를 대상으로 추가
aws events put-targets \
  --rule guardian-hourly-check \
  --targets "Id"="1","Arn"="arn:aws:lambda:ap-northeast-1:123456789012:function:guardianChecker","RoleArn"="arn:aws:iam::123456789012:role/service-role/GuardianEventBridgeRole"

# Lambda에 EventBridge 호출 권한 추가
aws lambda add-permission \
  --function-name guardianChecker \
  --statement-id AllowEventBridgeInvoke \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:ap-northeast-1:123456789012:rule/guardian-hourly-check
```

---

## 6. 웹 대시보드 배포

### 6.1 Vercel에 배포 (권장)

```bash
# 1단계: Vercel CLI 설치
npm install -g vercel

# 2단계: Vercel에 배포
cd apps/web
vercel

# 3단계: 환경 변수 설정
vercel env add NEXT_PUBLIC_API_URL
# 값: https://your-lambda-api-url.com

vercel env add NEXT_PUBLIC_REFRESH_INTERVAL
# 값: 30000

# 4단계: 배포 완료
# URL: https://guardian-dashboard.vercel.app
```

### 6.2 AWS Amplify에 배포 (대안)

```bash
# 1단계: Amplify CLI 설치
npm install -g @aws-amplify/cli

# 2단계: 프로젝트 초기화
amplify init

# 3단계: 호스팅 추가
amplify add hosting

# 4단계: 배포
amplify publish
```

### 6.3 API Gateway 연결

```bash
# Lambda 함수를 API Gateway로 노출
aws apigateway create-rest-api \
  --name guardian-api \
  --description "AWS Guardian API"

# API Key 생성 (선택사항)
aws apigateway create-api-key \
  --name guardian-api-key \
  --enabled

# 웹 대시보드의 API_URL을 API Gateway 엔드포인트로 설정
# 예: https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod
```

---

## 7. 첫 실행 및 테스트

### 7.1 기본 기능 테스트

```bash
# 1단계: EC2 체크 테스트
aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"action":"check_ec2"}' \
  response.json

cat response.json
# 출력:
# {
#   "status": "success",
#   "ec2": {
#     "total_instances": 5,
#     "healthy": 4,
#     "warnings": 1,
#     "checks_performed": [...],
#     "timestamp": "2026-05-11T10:30:00Z"
#   }
# }

# 2단계: S3 체크 테스트
aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"action":"check_s3"}' \
  response.json

# 3단계: 비용 체크 테스트
aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"action":"check_cost"}' \
  response.json
```

### 7.2 Telegram 알림 테스트

```bash
# 1단계: 테스트 이벤트 생성
aws dynamodb put-item \
  --table-name guardian-events \
  --item '{
    "event_id": {"S": "test-event-001"},
    "timestamp": {"N": "1620000000"},
    "event_type": {"S": "cost_alert"},
    "severity": {"S": "high"},
    "message": {"S": "높은 비용 증가 감지: $25.50 (임계값: $10.00)"}
  }'

# 2단계: Telegram 전송 함수 실행
aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"action":"send_telegram_alert","event":"test-event-001"}' \
  response.json

# 3단계: Telegram 채널에서 알림 확인
# → aws-guardian-alerts 채널에 메시지 도착 확인
```

### 7.3 웹 대시보드 테스트

```bash
# 1단계: 대시보드 접속
# https://guardian-dashboard.vercel.app (또는 로컬 주소)

# 2단계: 상태 카드 확인
# - EC2 상태
# - S3 상태
# - 비용 상태

# 3단계: 이벤트 로그 확인
# - 실시간 이벤트 스트림 (SSE)
# - 이벤트 필터링

# 4단계: 자동 대응 테스트
# - 대응 규칙 생성
# - 테스트 실행
```

### 7.4 성능 테스트

```bash
# 1단계: 응답 시간 측정
time aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"action":"check_all"}' \
  response.json

# 예상 결과:
# guardianChecker  0.43s  ✅ (3배 개선)

# 2단계: 메모리 사용량 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=guardianChecker \
  --start-time 2026-05-11T00:00:00Z \
  --end-time 2026-05-11T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# 3단계: API 호출 수 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=guardianChecker \
  --start-time 2026-05-11T00:00:00Z \
  --end-time 2026-05-11T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## 8. 운영 및 모니터링

### 8.1 CloudWatch 대시보드 생성

```bash
# 메인 대시보드 생성
aws cloudwatch put-dashboard \
  --dashboard-name GuardianDashboard \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/Lambda", "Duration", {"stat": "Average"}],
            ["AWS/Lambda", "Errors", {"stat": "Sum"}],
            ["AWS/Lambda", "Invocations", {"stat": "Sum"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "ap-northeast-1",
          "title": "Lambda Performance"
        }
      }
    ]
  }'

# CloudWatch 대시보드 접속
# AWS Console → CloudWatch → Dashboards → GuardianDashboard
```

### 8.2 알림 설정

```bash
# Lambda 에러 알림 설정
aws cloudwatch put-metric-alarm \
  --alarm-name guardian-lambda-errors \
  --alarm-description "Alert when Lambda has errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:ap-northeast-1:123456789012:GuardianAlerts

# DynamoDB 용량 알림
aws cloudwatch put-metric-alarm \
  --alarm-name guardian-dynamodb-throttle \
  --alarm-description "Alert when DynamoDB is throttled" \
  --metric-name UserErrors \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold
```

### 8.3 로그 확인

```bash
# 최근 Lambda 로그 확인
aws logs tail /aws/lambda/guardianChecker --follow

# 특정 시간의 로그 확인
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardianChecker \
  --start-time 1620000000000 \
  --end-time 1620003600000

# 에러 로그만 필터링
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardianChecker \
  --filter-pattern "[ERROR]"

# JSON 형식으로 로그 검색
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardianChecker \
  --filter-pattern '{ ($.level = "ERROR") }'
```

### 8.4 정기 점검 체크리스트

**매주 점검:**
- [ ] Lambda 함수 에러율 확인 (0% 목표)
- [ ] Telegram 알림 수신 확인
- [ ] 웹 대시보드 응답 시간 확인 (< 1초)
- [ ] DynamoDB 스토리지 사용량 확인

**매월 점검:**
- [ ] CloudWatch 로그 아카이빙 (90일 이상 보관)
- [ ] Cost Explorer에서 비용 검토
- [ ] Lambda 함수 성능 트렌드 분석
- [ ] 보안 감사 (IAM 권한, VPC 설정)

---

## 9. 트러블슈팅

### 9.1 Lambda 배포 실패

**증상:** `sam deploy` 실패

```bash
# 원인 1: S3 버킷 없음
해결: aws s3 mb s3://guardian-deploy-$(date +%s) --region ap-northeast-1

# 원인 2: IAM 권한 없음
해결: AWS Console → IAM → User → Add inline policy
정책: CloudFormation, Lambda, S3, DynamoDB 권한 추가

# 원인 3: 스택 이름 충돌
해결: aws cloudformation list-stacks
기존 스택 삭제 후 재배포
```

### 9.2 Telegram 알림 미수신

**증상:** Lambda 실행되지만 Telegram 메시지 없음

```bash
# 1단계: 환경 변수 확인
aws lambda get-function-configuration \
  --function-name guardianChecker \
  --query 'Environment.Variables'

# 2단계: Bot Token 유효성 확인
curl "https://api.telegram.org/bot[YOUR_BOT_TOKEN]/getMe"
# 응답: {"ok":true,"result":{"id":123456789,"is_bot":true,...}}

# 3단계: Chat ID 확인
curl "https://api.telegram.org/bot[YOUR_BOT_TOKEN]/getUpdates"

# 4단계: Lambda 로그 확인
aws logs tail /aws/lambda/guardianChecker --follow
# "Telegram send failed" 에러 메시지 확인

# 5단계: 수동 테스트
python3 << 'EOF'
import requests
token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
message = "Test message"
url = f"https://api.telegram.org/bot{token}/sendMessage"
response = requests.post(url, json={"chat_id": chat_id, "text": message})
print(response.json())
EOF
```

### 9.3 웹 대시보드 API 연결 실패

**증상:** "Failed to connect to API" 에러

```bash
# 1단계: API Gateway 엔드포인트 확인
aws apigateway get-rest-apis --query 'items[0].id'

# 2단계: CORS 설정 확인
aws apigateway get-stage \
  --rest-api-id [API_ID] \
  --stage-name prod

# 3단계: CORS 문제 해결
aws apigateway put-integration-response \
  --rest-api-id [API_ID] \
  --resource-id [RESOURCE_ID] \
  --http-method GET \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}'

# 4단계: 웹 대시보드 .env.local 확인
cat apps/web/.env.local
# NEXT_PUBLIC_API_URL=https://[API_ENDPOINT]/prod
```

### 9.4 DynamoDB 용량 초과

**증상:** "Request rate exceeded" 에러

```bash
# 1단계: 현재 용량 확인
aws dynamodb describe-table --table-name guardian-events

# 2단계: 온디맨드 모드로 변경 (권장)
aws dynamodb update-table \
  --table-name guardian-events \
  --billing-mode PAY_PER_REQUEST

# 3단계: 또는 프로비저닝 용량 증가
aws dynamodb update-table \
  --table-name guardian-events \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# 4단계: 오래된 데이터 정리 (TTL 설정)
aws dynamodb update-time-to-live \
  --table-name guardian-events \
  --time-to-live-specification AttributeName=ttl,Enabled=true
```

### 9.5 성능 저하

**증상:** Lambda 실행 시간 > 5초

```bash
# 1단계: CloudWatch Logs Insights로 분석
aws logs start-query \
  --log-group-name /aws/lambda/guardianChecker \
  --start-time 1620000000 \
  --end-time 1620010000 \
  --query-string 'fields @duration | stats avg(@duration) as avg_duration'

# 2단계: 병목 확인
# - EC2 API 호출 수 많음? → 캐싱 활성화
# - S3 ListBuckets 느림? → 버킷 수 감소
# - 비용 조회 느림? → Cost Explorer API 캐싱

# 3단계: 캐시 설정 확인
aws lambda get-function-configuration \
  --function-name guardianChecker \
  --query 'Environment.Variables.CACHE_BACKEND'
# 출력: redis

# 4단계: Redis 연결 확인
redis-cli -h [REDIS_ENDPOINT] ping
# 출력: PONG
```

---

## 10. 운영 팁

### 10.1 정기 업데이트

```bash
# 월 1회: Lambda 함수 업데이트
cd lambda
git pull origin main
sam build && sam deploy

# 월 1회: 웹 대시보드 업데이트
cd apps/web
git pull origin main
npm run build
vercel deploy --prod
```

### 10.2 비용 절감

```bash
# 1. EventBridge 빈도 조정
# 1시간 → 6시간 (비용 6배 감소)
aws events put-rule \
  --name guardian-hourly-check \
  --schedule-expression "rate(6 hours)"

# 2. Lambda 메모리 최적화
# 256MB → 128MB (실행 시간 약 2배 증가)
aws lambda update-function-configuration \
  --function-name guardianChecker \
  --memory-size 128

# 3. CloudWatch 로그 보관 기간 단축
# 무제한 → 30일
aws logs put-retention-policy \
  --log-group-name /aws/lambda/guardianChecker \
  --retention-in-days 30
```

### 10.3 보안 강화

```bash
# 1. Lambda 함수 VPC 설정
aws lambda update-function-configuration \
  --function-name guardianChecker \
  --vpc-config SubnetIds=subnet-123,SecurityGroupIds=sg-456

# 2. IAM 권한 최소화 (최소 권한 원칙)
# 불필요한 권한 제거 (예: ec2:*)
# 필요한 권한만 명시 (예: ec2:DescribeInstances, ec2:StopInstances)

# 3. Secrets Manager에 토큰 저장
aws secretsmanager create-secret \
  --name guardian/telegram-token \
  --secret-string '{"token":"YOUR_TOKEN","chat_id":"YOUR_CHAT_ID"}'

# Lambda에서 조회
import boto3
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='guardian/telegram-token')
```

---

## 11. 요약 체크리스트

### 초기 설정 (1~2시간)
- [ ] AWS 계정 생성 및 CLI 설정
- [ ] Telegram 봇 생성 및 Channel ID 확인
- [ ] IAM 역할 및 정책 생성
- [ ] DynamoDB 테이블 생성

### 배포 (30분)
- [ ] 로컬 환경 설정 (Python + Node.js)
- [ ] Lambda 함수 로컬 테스트
- [ ] Lambda 함수를 AWS에 배포 (SAM)
- [ ] 웹 대시보드를 Vercel에 배포

### 검증 (30분)
- [ ] Lambda 함수 실행 확인
- [ ] Telegram 알림 수신 확인
- [ ] 웹 대시보드 접속 확인
- [ ] 자동 대응 기능 테스트

### 운영 준비 (진행중)
- [ ] CloudWatch 알림 설정
- [ ] 정기 점검 계획 수립
- [ ] 백업 및 복구 계획 수립
- [ ] 문서 정리

---

**축하합니다! 이제 AWS Guardian을 실제로 배포하고 운영할 준비가 되었습니다! 🚀**

더 궁금한 사항이 있으면 다음을 참고하세요:
- AWS 문서: https://docs.aws.amazon.com/
- Telegram Bot API: https://core.telegram.org/bots/api
- AWS CLI 가이드: https://docs.aws.amazon.com/cli/latest/userguide/
