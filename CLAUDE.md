# AWS Guardian System

> AWS 계정을 자동으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응 + Discord 대시보드로 제어하는 서버리스 보안/비용 감시 시스템

---

## 슬로건

**"잠자는 동안에도 AWS를 지킨다"**

---

## 개요

| 항목 | 내용 |
|------|------|
| 배포 방식 | AWS Lambda (서버리스, 무료 티어 활용) |
| 감시 주기 | 1시간마다 EventBridge 트리거 |
| 알림 채널 | Telegram Bot |
| 제어 대시보드 | Discord Bot + Slash Command |
| 감시 대상 | EC2 인스턴스, S3 버킷, 전체 계정 비용 |
| 자동 대응 | 이상 탐지 → EC2 자동 중지 / S3 퍼블릭 차단 |

---

## 핵심 기능

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
- `/status` : 현재 EC2, S3, 비용 상태 조회
- `/stop {instance-id}` : 수동 EC2 중지
- `/budget set {amount}` : 비용 임계값 변경
- `/history` : 최근 24시간 이벤트 로그

### 5. 자동 대응 로그
- 모든 자동 대응 내역 DynamoDB 저장
- Telegram + Discord 동시 알림

---

## 시나리오

```
[매 1시간]
EventBridge → Lambda 트리거
    ↓
비용 체크 → 임계값 초과? → Telegram 알림 발송
    ↓
EC2 체크 → 이상 인스턴스? → 자동 Stop + Telegram 알림
    ↓
S3 체크 → 퍼블릭 버킷? → 자동 차단 + Telegram 알림
    ↓
결과 → DynamoDB 저장 → Discord 대시보드 갱신

[Discord 명령어]
/status → Lambda 호출 → 현재 상태 Embed 반환
/stop → Lambda 호출 → EC2 중지 실행
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 실행 환경 | AWS Lambda (Python 3.12) |
| 스케줄러 | AWS EventBridge (cron) |
| 비용 조회 | AWS Cost Explorer API |
| 인프라 제어 | AWS SDK (boto3) |
| 알림 | Telegram Bot API |
| 대시보드 | Discord Bot (discord.py / interactions) |
| 상태 저장 | AWS DynamoDB (무료 티어) |
| 설정 저장 | AWS SSM Parameter Store |
| 배포 | AWS SAM / Terraform |

---

## 스코프 (v1)

### IN
- Lambda 기반 1시간 주기 감시
- EC2 / S3 / 비용 3종 감시
- Telegram 알림
- Discord Slash Command 대시보드
- EC2 자동 Stop / S3 퍼블릭 자동 차단

### OUT (v2 이후)
- CloudTrail 실시간 로그 분석
- IAM 권한 이상 감지
- GuardDuty 통합
- 웹 대시보드 (Next.js)
- 다중 AWS 계정 지원

---

## 성공 지표

- Lambda 월 실행 비용 < $0.50 (무료 티어 범위 내)
- 이상 감지 → 알림 도달 시간 < 5분
- 자동 대응 성공률 > 95%
- Discord 명령어 응답 시간 < 3초

---

## 디렉토리 구조

```
aws-guardian/
├── CLAUDE.md
├── SKILL.md
├── lambda/
│   ├── guardian/          # 메인 감시 Lambda
│   │   ├── handler.py
│   │   ├── checkers/
│   │   │   ├── cost.py
│   │   │   ├── ec2.py
│   │   │   └── s3.py
│   │   ├── responders/
│   │   │   ├── telegram.py
│   │   │   └── discord.py
│   │   └── storage/
│   │       └── dynamodb.py
│   └── discord_webhook/   # Discord 명령어 Lambda
│       └── handler.py
├── terraform/
│   ├── main.tf
│   ├── lambda.tf
│   ├── eventbridge.tf
│   ├── dynamodb.tf
│   └── iam.tf
├── scripts/
│   └── deploy.sh
└── tests/
    ├── test_cost.py
    ├── test_ec2.py
    └── test_s3.py
```
