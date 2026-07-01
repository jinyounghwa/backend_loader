---
module: dashboard
path: 00-Dashboard
keywords: quick-reference, commands, setup, aws-guardian
---

# Quick Reference — AWS Guardian

#dashboard #quick-reference

## 핵심 명령어

| 작업 | 명령어 |
|------|--------|
| LocalStack 시작 | `docker-compose up -d` |
| 테스트 전체 실행 | `python -m pytest tests/ -v` |
| 특정 테스트 실행 | `python -m pytest tests/test_cost.py -v` |
| Lambda 로컬 빌드 | `bash build-lambda-local.sh` |
| SAM 빌드 | `sam build` |
| SAM 배포 | `sam deploy --guided` |
| Terraform 적용 | `cd terraform && terraform apply` |
| 타입 체크 | `mypy lambda/` |

## 환경변수 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `AWS_ENV` | `localstack` | `localstack` 또는 `production` |
| `AWS_REGION` | `us-east-1` | AWS 리전 |
| `LOCALSTACK_ENDPOINT` | `http://localhost:4566` | LocalStack 엔드포인트 |
| `COST_THRESHOLD` | `10.0` | 일일 비용 임계값 ($) |
| `DYNAMODB_TABLE_NAME` | `aws-guardian-events` | DynamoDB 테이블 |
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot 토큰 |
| `TELEGRAM_CHAT_ID` | — | Telegram 채팅 ID |
| `DISCORD_WEBHOOK_URL` | — | Discord Webhook URL |
| `DISCORD_PUBLIC_KEY` | — | Discord 앱 공개키 |
| `AUTHORIZED_REGIONS` | (모든 리전) | 허용 EC2 리전 목록 (쉼표 구분) |
| `ORGANIZATIONS_ENABLED` | `false` | 다중 계정 활성화 |

## SSM Parameter Store 경로 (프로덕션)

| 변수 | SSM 경로 변수 |
|------|--------------|
| Telegram Bot Token | `SSM_TELEGRAM_BOT_TOKEN_PATH` |
| Telegram Chat ID | `SSM_TELEGRAM_CHAT_ID_PATH` |
| Discord Webhook URL | `SSM_DISCORD_WEBHOOK_URL_PATH` |
| 비용 임계값 | `/aws-guardian/cost-threshold` |

## 중요 파일 위치

| 파일/디렉토리 | 목적 |
|--------------|------|
| `lambda/guardian/handler.py` | **Lambda 메인 진입점** |
| `lambda/guardian/config.py` | 중앙 설정 관리 |
| `lambda/guardian/checkers/base.py` | 체커 추상 기반 클래스 |
| `lambda/guardian/checkers/cost.py` | 비용 이상 감지 |
| `lambda/guardian/checkers/ec2.py` | EC2 보안 감시 |
| `lambda/guardian/checkers/s3.py` | S3 보안 감시 |
| `lambda/guardian/checkers/cloudtrail.py` | CloudTrail 감시 |
| `lambda/guardian/checkers/iam.py` | IAM 이상 감지 |
| `lambda/guardian/responders/telegram.py` | Telegram 알림 |
| `lambda/guardian/responders/discord.py` | Discord 알림 |
| `lambda/guardian/storage/dynamodb.py` | DynamoDB 저장 |
| `lambda/discord_webhook/handler.py` | Discord 명령어 Lambda |
| `terraform/` | 인프라 코드 (IaC) |
| `docker-compose.yml` | LocalStack 개발환경 |
| `tests/` | 테스트 모음 |

## 심각도(Severity) 레벨

| 레벨 | 용도 |
|------|------|
| `CRITICAL` | 즉각 대응 필요 (퍼블릭 S3, 무단 EC2 등) |
| `HIGH` | 높은 위험 / 체커 오류 |
| `MEDIUM` | 주의 필요 |
| `LOW` | 낮은 위험 |
| `INFO` | 정상 상태 / 참고 정보 |

## Discord 색상 코드

| 심각도 | 색상 (hex) | 의미 |
|--------|-----------|------|
| CRITICAL | `#FF0000` (빨강) | 즉각 조치 |
| HIGH | `#FF8000` (주황) | 경고 |
| MEDIUM | `#FFFF00` (노랑) | 주의 |
| LOW | `#58A9FF` (파랑) | 낮은 위험 |
| INFO | `#00FF00` (초록) | 정상 |

## 디버깅 가이드

| 증상 | 확인 위치 | 관련 노트 |
|------|-----------|----------|
| Lambda cold start 느림 | `handler.py` `_LazyOrchestrator` | [[Guardian Handler]] |
| 비용 체크 실패 | `checkers/cost.py`, Cost Explorer 권한 | [[CostChecker]] |
| Telegram 알림 미수신 | 환경변수 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | [[TelegramResponder]] |
| DynamoDB 쓰기 오류 | `AWS_ENV` 설정, 테이블 존재 여부 | [[DynamoDB Storage]] |
| Discord 서명 검증 실패 | `DISCORD_PUBLIC_KEY` 환경변수 | [[Discord Webhook Handler]] |
| LocalStack 연결 오류 | `docker-compose up -d` 상태 확인 | [[DevOps & 배포]] |
