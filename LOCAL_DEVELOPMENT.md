# AWS Guardian - Local Development Guide

**LocalStack + GLM API 기반 로컬 개발 환경**

## 🚀 빠른 시작 (5분)

### 1. LocalStack 실행

```bash
docker-compose up -d
```

### 2. LocalStack 초기화

```bash
cd /Users/younghwa.jin/Documents/backend_loader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 scripts/init_localstack.py
```

### 3. 환경변수 설정

```bash
export LOCALSTACK_ENDPOINT=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export GLM_API_KEY=5fafb543164c452bacbb13aaafdd31a4.yEj71FHKcqNB8o2f
```

### 4. 로컬 테스트 실행

```bash
# GLM 통합 테스트
python3 -m pytest tests/test_glm_integration.py -v

# 전체 핸들러 실행
python3 -c "from lambda.guardian.handler import lambda_handler; lambda_handler({'time': '2024-01-15T10:00:00Z'}, None)"
```

---

## 📊 LocalStack 리소스

생성된 테스트 리소스:

### DynamoDB
- **Table**: `aws-guardian-events`
- **Schema**: `timestamp` (PK) + `event_type` (SK)

### S3 Buckets
- `test-bucket-1` - 일반 버킷
- `test-bucket-2` - 일반 버킷
- `public-test-bucket` - 퍼블릭 버킷 (테스트용)

### EC2
- **Instance**: `i-77d62f267079efef3` (t2.micro)
- **Security Group**: `sg-a191d78382fe9b81d`
  - SSH (22) 포트 `0.0.0.0/0` 오픈 (노출 감지 테스트용)

### SSM Parameters
- `/aws-guardian/cost-threshold` = `10.0`
- `/aws-guardian/authorized-regions` = `us-east-1,us-west-2`

---

## 🧪 테스트 시나리오

### 시나리오 1: EC2 이상 탐지
```bash
# 새로운 인스턴스가 감지됨 (last 1 hour)
# 결과: [LocalStack] Would send EC2 alert
```

### 시나리오 2: S3 새 버킷 감지
```bash
# 3개의 새 버킷이 감지됨 (last 24 hours)
# 결과: [LocalStack] Would send S3 alert
```

### 시나리오 3: 비용 이상 감지
```bash
# Mock 비용: $5.50/day (정상)
# Threshold: $10.00/day
# 결과: ✓ Cost normal (임계값 초과 아님)
```

---

## 🤖 GLM API 통합

### GLM 분석 기능
1. **Cost Anomaly Analysis**
   - 근본 원인 분석
   - 심각도 평가
   - 최적화 권고사항

2. **EC2 Security Analysis**
   - 위협도 평가
   - 자동 대응 제안
   - 조사 절차

3. **S3 Compliance Analysis**
   - 규정 준수 위험 평가
   - 액션 권고
   - 암호화 제안

### API 테스트

```bash
# GLM 없이 테스트 (항상 성공)
python3 -m pytest tests/test_glm_integration.py::TestGLMWithoutAPI -v

# GLM 포함 테스트 (API 키 필요)
export GLM_API_KEY=your_key_here
python3 -m pytest tests/test_glm_integration.py::TestGLMIntegration -v
```

---

## 🔧 개발 워크플로우

### 코드 변경 후 테스트

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. 환경변수 설정
export LOCALSTACK_ENDPOINT=http://localhost:4566
export GLM_API_KEY=5fafb543164c452bacbb13aaafdd31a4.yEj71FHKcqNB8o2f

# 3. 단위 테스트
python3 -m pytest tests/test_cost.py -v
python3 -m pytest tests/test_ec2.py -v
python3 -m pytest tests/test_s3.py -v

# 4. 통합 테스트
python3 -m pytest tests/test_glm_integration.py -v

# 5. 핸들러 실행
cd lambda
python3 guardian/handler.py
```

---

## 📝 주요 파일

```
lambda/guardian/
├── config.py               # 환경설정 (LocalStack 호환)
├── handler.py              # 메인 Lambda 핸들러
├── checkers/
│   ├── cost.py             # Cost Explorer API
│   ├── ec2.py              # EC2 보안 감시
│   └── s3.py               # S3 보안 감시
├── responders/
│   ├── telegram.py         # Telegram 알림
│   ├── discord.py          # Discord 알림
│   └── glm.py              # GLM AI 분석 ⭐
└── storage/
    └── dynamodb.py         # DynamoDB 저장소

scripts/
├── init_localstack.py      # LocalStack 초기화
├── dev-local.sh            # 로컬 개발 설정
└── localstack-init.sh      # LocalStack 헬스 체크

tests/
├── test_cost.py            # Cost Checker 테스트
├── test_ec2.py             # EC2 Checker 테스트
├── test_s3.py              # S3 Checker 테스트
└── test_glm_integration.py # GLM API 통합 테스트
```

---

## 🐛 문제 해결

### LocalStack 다시 시작

```bash
docker-compose down
docker-compose up -d
python3 scripts/init_localstack.py
```

### DynamoDB 테이블 확인

```bash
source venv/bin/activate
export LOCALSTACK_ENDPOINT=http://localhost:4566
python3 -c "
import boto3
dynamodb = boto3.client('dynamodb', endpoint_url='http://localhost:4566')
print(dynamodb.list_tables())
"
```

### GLM API 테스트

```bash
python3 -c "
import os
from lambda.guardian.responders.glm import GLMAnalyzer
os.environ['GLM_API_KEY'] = 'your_key'
analyzer = GLMAnalyzer()
print(f'GLM Available: {analyzer.is_available}')
"
```

---

## 📚 참고

- [LocalStack 문서](https://docs.localstack.cloud/)
- [GLM API 문서](https://open.bigmodel.cn/docs)
- [boto3 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

## ✨ 다음 단계

1. **AWS 배포**
   ```bash
   cd terraform
   terraform init
   terraform plan -var-file=terraform.tfvars
   terraform apply
   ```

2. **GLM API 키 설정**
   - Zhipu AI 플랫폼에서 API 키 발급
   - `terraform.tfvars`에 입력
   - Terraform 재배포

3. **Telegram/Discord 연동**
   - Bot Token 설정
   - Webhook URL 설정
   - 테스트 메시지 발송

---

**Happy Developing! 🚀**
