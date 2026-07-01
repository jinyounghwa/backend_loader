---
module: dashboard
path: 00-Dashboard
keywords: MOC, onboarding, architecture, aws-guardian
---

# AWS Guardian — 학습 지도 (Map of Content)

#dashboard #onboarding

## 아키텍처 개요
- **패턴**: Serverless Event-Driven (AWS Lambda + EventBridge)
- **언어/스택**: Python 3.12, boto3, AWS SAM, Terraform, LocalStack
- **알림 채널**: Telegram Bot, Discord Webhook
- **저장소**: DynamoDB, SSM Parameter Store
- → [[시스템 아키텍처]]
- → [[요청 흐름 (Request Flow)]]
- → [[데이터 흐름 (Data Flow)]]

## 모듈 맵

| 모듈 | 목적 | 핵심 진입점 | 노트 |
|------|------|-------------|------|
| **Entry Point** | Lambda 핸들러, 지연 초기화 | `lambda/guardian/handler.py` | [[Guardian Handler]] |
| **Checkers** | EC2/S3/비용/CloudTrail/IAM/GuardDuty 감시 | `lambda/guardian/checkers/` | [[Checkers 개요]] |
| **Responders** | Telegram/Discord 알림, 자동 대응 | `lambda/guardian/responders/` | [[Responders 개요]] |
| **Storage** | DynamoDB 이벤트 저장 | `lambda/guardian/storage/dynamodb.py` | [[DynamoDB Storage]] |
| **Config** | 환경변수/SSM 설정 관리 | `lambda/guardian/config.py` | [[Config 모듈]] |
| **Discord Webhook** | Discord Slash Command 처리 Lambda | `lambda/discord_webhook/handler.py` | [[Discord Webhook Handler]] |
| **Analytics/ML** | 비용 예측, 이상 탐지 ML | `lambda/guardian/analytics/`, `ml/` | [[Analytics & ML]] |
| **Handlers/Engines** | 자동화, 플레이북, 실시간 처리 | `lambda/guardian/handlers/`, `engines/` | [[Handlers & Engines]] |
| **Multi-Account** | 다중 AWS 계정 지원 | `lambda/guardian/multi_account/` | [[Multi-Account]] |
| **DevOps** | Terraform, Docker Compose, SAM | `terraform/`, `docker-compose.yml` | [[DevOps & 배포]] |

## Discord API Surface

| 명령어 | 기능 | 처리 위치 |
|--------|------|-----------|
| `/status` | 현재 EC2/S3/비용 상태 조회 | `discord_webhook/handler.py` |
| `/stop {instance-id}` | EC2 인스턴스 수동 중지 | `discord_webhook/handler.py` |
| `/budget set {amount}` | 비용 임계값 변경 | `discord_webhook/handler.py` |
| `/history` | 최근 24시간 이벤트 로그 | `discord_webhook/handler.py` |

## 시작하기 (Getting Started)

1. **사전 요구사항**: Python 3.12, Docker, AWS CLI, LocalStack
2. **로컬 실행**:
   ```bash
   docker-compose up -d       # LocalStack 시작
   pip install -r requirements.txt
   python -m pytest tests/    # 테스트 실행
   ```
3. **환경 설정**: `AWS_ENV=localstack` (기본값) → 실제 AWS는 `AWS_ENV=production`
4. **Lambda 배포**:
   ```bash
   sam build && sam deploy
   # 또는
   terraform apply
   ```

## 태그 인덱스

| 태그 | 설명 |
|------|------|
| `#arch-serverless` | 서버리스 아키텍처 패턴 |
| `#arch-event-driven` | 이벤트 기반 패턴 |
| `#module-checkers` | 감시 체커 모듈 |
| `#module-responders` | 알림/대응 모듈 |
| `#module-storage` | 저장소 모듈 |
| `#module-config` | 설정 모듈 |
| `#module-analytics` | 분석/ML 모듈 |
| `#pattern-lazy-init` | 지연 초기화 패턴 |
| `#pattern-base-class` | 추상 기반 클래스 패턴 |
| `#pattern-double-checked-locking` | 이중 체크 잠금 패턴 |
| `#api-telegram` | Telegram Bot API |
| `#api-discord` | Discord Webhook/Slash Command |
| `#api-aws` | AWS SDK (boto3) |
| `#config-env` | 환경변수 설정 |
| `#config-ssm` | SSM Parameter Store 설정 |

## 온보딩 학습 순서

> 신규 개발자를 위한 권장 학습 순서:

1. [[시스템 아키텍처]] — 전체 그림 파악
2. [[요청 흐름 (Request Flow)]] — Lambda 실행 흐름
3. [[Guardian Handler]] — 진입점 코드
4. [[Config 모듈]] — 설정 체계 이해
5. [[Checkers 개요]] → [[CostChecker]] → [[EC2Checker]] → [[S3Checker]] — 핵심 감시 로직
6. [[Responders 개요]] → [[TelegramResponder]] → [[DiscordResponder]] — 알림 시스템
7. [[DynamoDB Storage]] — 이벤트 저장
8. [[Discord Webhook Handler]] — Discord 명령어 처리
9. [[Analytics & ML]] — 고급 분석 기능
10. [[DevOps & 배포]] — 배포 파이프라인
11. [[온보딩 연습문제]] — 실습
