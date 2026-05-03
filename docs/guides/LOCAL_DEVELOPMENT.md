# 로컬 개발 가이드

AWS Guardian은 로컬 개발 환경에서 LocalStack을 기본으로 사용합니다. 이를 통해 실제 AWS 비용 발생 없이 시스템을 개발하고 테스트할 수 있습니다.

## 빠른 시작

단일 명령어로 모든 로컬 환경을 구성할 수 있습니다.

```bash
./start.sh
```

이 스크립트는 다음 작업을 수행합니다.
- Docker Compose를 통한 LocalStack 기동
- 필요한 AWS 리소스(DynamoDB, S3, EC2, SSM) 초기화
- 프론트엔드 대시보드(apps/web) 실행

## 수동 설정 방법

스크립트를 사용하지 않고 직접 구성하려면 다음 단계를 따르세요.

```bash
# 1. LocalStack 기동
docker-compose up -d

# 2. 파이썬 가상환경 설정 및 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 리소스 초기화 스크립트 실행
python3 scripts/init_localstack.py
```

## 환경 변수 설정

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| AWS_ENV | localstack | localstack 또는 production 설정 |
| MOCK_DAILY_COST | 5.0 | LocalStack 모드에서의 가상 일일 비용 |
| MOCK_MONTHLY_COST | 150.0 | LocalStack 모드에서의 가상 월간 비용 |
| TELEGRAM_BOT_TOKEN | - | 텔레그램 알림용 토큰 |
| TELEGRAM_CHAT_ID | - | 텔레그램 알림용 채팅 ID |

## SSM 파라미터 경로

시스템 설정은 SSM Parameter Store를 사용하며, 경로는 반드시 `/guardian/`으로 시작해야 합니다.
- `/guardian/cost-threshold`: 비용 경고 임계값
- `/guardian/authorized-regions`: 허용된 리전 목록

## 텔레그램 연동

로컬 환경에서도 텔레그램 연동이 가능합니다. `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`를 환경 변수로 설정하면 LocalStack 모드에서 실제 메시지가 발송됩니다.

## 프론트엔드 대시보드

대시보드는 `apps/web/` 경로에 있으며 Next.js로 작성되었습니다.

```bash
cd apps/web
npm install
npm run dev
```

접속 주소: `http://localhost:3000`

## 테스트 실행

```bash
# 단위 테스트
python3 -m pytest tests/

# 특정 체커 테스트
python3 -m pytest tests/test_ec2.py
```

## 문제 해결

- LocalStack 리소스가 보이지 않을 경우: `scripts/init_localstack.py`를 다시 실행하세요.
- 포트 충돌: 4566(LocalStack) 또는 3000(Next.js) 포트가 사용 중인지 확인하세요.
- 도커 실행 확인: `docker ps` 명령어로 LocalStack 컨테이너 상태를 확인하세요.
