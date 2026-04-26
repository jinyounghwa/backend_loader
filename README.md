# AWS Guardian - Serverless AWS Account Monitoring System

**"잠자는 동안에도 AWS를 지킨다"**

AWS 계정을 자동으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응 + Discord 대시보드로 제어하는 서버리스 보안/비용 감시 시스템

## 📋 개요

| 항목 | 내용 |
|------|------|
| 배포 방식 | AWS Lambda (서버리스, 무료 티어 활용) |
| 감시 주기 | 1시간마다 EventBridge 트리거 |
| 알림 채널 | Telegram Bot |
| 제어 대시보드 | Discord Bot + Slash Command |
| 감시 대상 | EC2 인스턴스, S3 버킷, 전체 계정 비용 |
| 자동 대응 | 이상 탐지 → EC2 자동 중지 / S3 퍼블릭 차단 |

## 🎯 핵심 기능

### 1. 비용 이상 감지
- AWS Cost Explorer API로 당일/전일 비용 조회
- 임계값(기본 $10/일) 초과 시 즉시 Telegram 알림
- 월별 누적 비용 추이 Discord 대시보드에 표시

### 2. EC2 보안 감시
- 알 수 없는 인스턴스 신규 기동 감지
- 비인가 리전에서 EC2 실행 감지
- Security Group에 0.0.0.0/0 포트 오픈 감지
- 이상 감지 시 → 해당 인스턴스 자동 중지 (Stop)

### 3. S3 보안 감시
- 퍼블릭 버킷 감지 (ACL / Bucket Policy)
- 신규 버킷 생성 감지
- 이상 감지 시 → 퍼블릭 액세스 차단 자동 적용

### 4. Discord 대시보드
```
/status       : 현재 EC2, S3, 비용 상태 조회
/stop         : 수동 EC2 중지
/budget set   : 비용 임계값 변경
/history      : 최근 24시간 이벤트 로그
```

### 5. 자동 대응 로그
- 모든 자동 대응 내역 DynamoDB 저장
- Telegram + Discord 동시 알림

## 🏗️ 아키텍처

```
[EventBridge 1시간 주기]
        ↓
[Guardian Lambda]
    ├── Cost Checker (Cost Explorer API)
    ├── EC2 Checker (EC2 API)
    └── S3 Checker (S3 API)
        ↓
[Telegram Bot] + [Discord Bot]
        ↓
[DynamoDB Events Table]
```

## 📦 기술 스택

| 레이어 | 기술 |
|--------|------|
| 실행 환경 | AWS Lambda (Python 3.12) |
| 스케줄러 | AWS EventBridge (cron) |
| 비용 조회 | AWS Cost Explorer API |
| 인프라 제어 | AWS SDK (boto3) |
| 알림 | Telegram Bot API |
| 대시보드 | Discord Bot (discord.py) |
| 상태 저장 | AWS DynamoDB (무료 티어) |
| 설정 저장 | AWS SSM Parameter Store |
| 배포 | Terraform |

## 🚀 설치 및 배포

### 사전 요구사항

1. **AWS 계정** (EC2, S3, Lambda, DynamoDB, Cost Explorer 접근 권한)
2. **Telegram Bot Token** (`@BotFather`에서 생성)
3. **Discord Bot Token** (Discord Developer Portal에서 생성)
4. **LocalStack (선택사항)** - 로컬 개발/테스트용

### 설치 단계

#### 1. 저장소 클론 및 의존성 설치

```bash
cd aws-guardian
pip install -r requirements.txt
```

#### 2. 환경 변수 설정

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export DISCORD_WEBHOOK_URL="your-webhook-url"
export DISCORD_PUBLIC_KEY="your-public-key"
export AWS_REGION="us-east-1"
```

#### 3. Terraform 배포

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

또는 배포 스크립트 사용:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## 🧪 테스트

### 단위 테스트 실행

```bash
python -m pytest tests/
```

또는 개별 테스트:

```bash
python -m unittest tests.test_cost
python -m unittest tests.test_ec2
python -m unittest tests.test_s3
```

### LocalStack에서 로컬 테스트

```bash
# LocalStack 시작
localstack start

# LocalStack 토큰 설정
export LOCALSTACK_AUTH_TOKEN="ls-tAGa5429-0514-nebE-wOnE-QabIKAWu038b"

# 로컬 Lambda 함수 테스트
python lambda/guardian/handler.py
```

## 📊 사용 예시

### Telegram 알림

```
🚨 AWS Cost Alert
━━━━━━━━━━━━━━━━━━━
💰 Today's Cost: $15.50
⚠️ Threshold: $10.00
📈 Increase: 210%
📅 Date: 2024-01-15
━━━━━━━━━━━━━━━━━━━
```

### Discord 명령어

```
/status               → 현재 상태 확인
/stop i-12345678 us-east-1  → EC2 중지
/budget set 20        → 임계값을 $20으로 변경
/history              → 최근 이벤트 로그
```

## 🔒 보안

- **IAM Roles**: 최소 권한 원칙 적용
- **Secret Storage**: AWS SSM Parameter Store (Secure String)
- **Encryption**: DynamoDB 암호화 활성화
- **Logging**: CloudWatch Logs에 모든 활동 기록

## 💰 비용 추정

### 월 예상 비용 (500만 요청 기준)

| 서비스 | 사용량 | 비용 |
|--------|--------|------|
| Lambda | 720시간 | $0.01 |
| DynamoDB | 무료 티어 내 | $0.00 |
| CloudWatch | 로그 저장 | $0.03 |
| **합계** | | **< $0.50** |

> 대부분 AWS 무료 티어로 커버됨

## 📈 모니터링

### CloudWatch Metrics

```bash
# Guardian Lambda 성공률
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=aws-guardian-monitor
```

## 🔄 주기적 유지보수

### 주간 작업
- DynamoDB 이벤트 로그 검토
- 자동 응답 성공률 확인
- Cost Threshold 조정 필요성 검토

### 월간 작업
- DynamoDB 오래된 데이터 정리 (TTL)
- IAM 정책 검토
- Lambda 성능 메트릭 분석

## 🐛 문제 해결

### Lambda 함수 로그 확인

```bash
aws logs tail /aws/lambda/aws-guardian-monitor --follow
```

### DynamoDB 이벤트 쿼리

```bash
aws dynamodb scan \
  --table-name aws-guardian-events \
  --filter-expression "timestamp > :date" \
  --expression-attribute-values '{":date":{"S":"2024-01-15"}}'
```

## 📋 v1 스코프

### IN
- ✅ Lambda 기반 1시간 주기 감시
- ✅ EC2 / S3 / 비용 3종 감시
- ✅ Telegram 알림
- ✅ Discord Slash Command 대시보드
- ✅ EC2 자동 Stop / S3 퍼블릭 자동 차단

### OUT (v2 이후)
- CloudTrail 실시간 로그 분석
- IAM 권한 이상 감지
- GuardDuty 통합
- 웹 대시보드 (Next.js)
- 다중 AWS 계정 지원

## 🎯 성공 지표

- ✅ Lambda 월 실행 비용 < $0.50 (무료 티어 범위 내)
- ✅ 이상 감지 → 알림 도달 시간 < 5분
- ✅ 자동 대응 성공률 > 95%
- ✅ Discord 명령어 응답 시간 < 3초

## 📞 지원

문제 발생 시:
1. CloudWatch Logs 확인
2. DynamoDB 이벤트 로그 검토
3. IAM 권한 확인
4. LocalStack에서 로컬 테스트

## 📝 라이선스

MIT License

---

**"잠자는 동안에도 AWS를 지킨다"** 🛡️🚀
