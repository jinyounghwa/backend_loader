# AWS Guardian

AWS 계정을 자동으로 감시하고 위협 탐지 시 텔레그램 알림, 자동 대응, 디스코드 대시보드 제어를 제공하는 서버리스 보안 및 비용 감시 시스템입니다.

## 빠른 시작

로컬 개발 환경에서 LocalStack을 사용하여 즉시 시작할 수 있습니다.

```bash
# 1. 저장소 클론 및 이동
cd backend_loader

# 2. 원클릭 시작 스크립트 실행 (Docker 필요)
chmod +x start.sh
./start.sh
```

스크립트는 LocalStack 컨테이너 실행, 리소스 초기화, 프론트엔드 대시보드 기동을 자동으로 처리합니다.

## 사전 요구사항

- Docker 및 Docker Compose
- Python 3.9 이상
- 텔레그램 봇 (선택 사항, 알림 수신용)
- AWS CLI (배포용)

## 아키텍처

```
[LocalStack / AWS]
       ↓
[EventBridge (1시간 주기)]
       ↓
[Guardian Lambda] ───┐
    ├── Cost Checker (Mock/Explorer)
    ├── EC2 Checker
    └── S3 Checker
       ↓
[Telegram / Discord Webhook]
       ↓
[Next.js Dashboard (apps/web)]
```

## 주요 기능

- 비용 이상 감지: 설정된 임계값 초과 시 즉시 알림
- EC2 보안 감시: 비인가 리전 기동 및 보안 그룹 노출 감지 시 자동 중지
- S3 보안 감시: 퍼블릭 버킷 생성 감지 시 즉시 차단
- 통합 대시보드: Next.js 기반의 실시간 상태 모니터링
- 디스코드 제어: 슬래시 명령어를 통한 인스턴스 중지 및 설정 변경

## 기술 스택

| 구분 | 기술 |
|------|------|
| 실행 환경 | AWS Lambda (Python 3.12) |
| 로컬 환경 | LocalStack |
| 인프라 관리 | Terraform |
| 프론트엔드 | Next.js (apps/web) |
| 데이터베이스 | DynamoDB |
| 설정 관리 | SSM Parameter Store |
| 알림 채널 | Telegram, Discord |

## 로컬 테스트

LocalStack 모드에서는 실제 AWS 비용이 발생하지 않습니다.

```bash
# 환경 변수 설정 (기본값: localstack)
export AWS_ENV=localstack

# 테스트 실행
python3 -m pytest tests/
```

## 상용 AWS 배포

상용 환경에 배포하려면 `AWS_ENV`를 `production`으로 설정해야 합니다.

```bash
# 환경 변수 변경
export AWS_ENV=production

# Terraform 배포
cd terraform
terraform init
terraform apply
```

상세한 배포 방법은 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)를 참고하세요.

## 라이선스

MIT License
