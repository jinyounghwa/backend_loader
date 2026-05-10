# Sprint 25: AWS 배포 & 웹 대시보드

**Status:** 📋 PLANNED  
**Target:** AWS 정식 배포, 웹 대시보드 개발, v1.3.0 정식 릴리스

---

## Sprint 25 Overview

Sprint 24에서 준비한 v1.3.0을 AWS에 정식 배포하고, Next.js 기반 웹 대시보드 개발 시작:

1. **AWS 배포** - SAM CLI로 Lambda, EventBridge, DynamoDB 배포
2. **웹 대시보드** - Next.js 기반 실시간 모니터링 UI
3. **GitHub Release** - v1.3.0 정식 릴리스
4. **모니터링** - CloudWatch, Telegram 알림 검증

---

## 5.1: AWS 배포

### 사전 준비

```bash
# AWS 계정 설정
aws configure

# 확인
aws sts get-caller-identity
```

### SAM 배포 (Interactive)

```bash
cd /path/to/backend_loader
sam deploy --guided -t sam.yaml

# 프롬프트:
# Stack Name: aws-guardian-v1.3
# Region: ap-northeast-2
# TelegramBotToken: [봇 토큰]
# TelegramChatId: [채팅 ID]
# CostThreshold: 10.0
# Confirm changes: Y
# Allow IAM role creation: Y
# Save parameters: Y
```

### 배포 검증

```bash
# CloudFormation Stack 확인
aws cloudformation describe-stacks \
  --stack-name aws-guardian-v1.3 \
  --query 'Stacks[0].StackStatus'

# Lambda 함수 확인
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `guardian`)].FunctionName'

# EventBridge 규칙 확인
aws events list-rules \
  --query 'Rules[?contains(Name, `guardian`)].{Name:Name,ScheduleExpression:ScheduleExpression}'

# 테스트 호출
aws lambda invoke \
  --function-name guardianChecker \
  --payload '{"check_type":"cost"}' \
  response.json && cat response.json
```

---

## 5.2: 웹 대시보드 개발

### 목표
- EC2, S3, 비용 상태 실시간 조회
- 이상 탐지 이벤트 로그
- 자동 대응 기록 조회

### 구조

```
apps/web/
├── src/app/
│   ├── dashboard/
│   │   └── page.tsx          # 메인 대시보드
│   ├── api/
│   │   ├── status/           # 현재 상태 API
│   │   ├── events/           # 이벤트 로그 API
│   │   └── actions/          # 자동 대응 API
│   └── layout.tsx
├── components/
│   ├── StatusCard.tsx        # EC2/S3/Cost 카드
│   ├── EventLog.tsx          # 이벤트 로그 테이블
│   └── ActionHistory.tsx     # 대응 기록
└── lib/
    └── api.ts               # API 호출 함수
```

### API 엔드포인트

**GET /api/status**
```json
{
  "ec2": {
    "total_instances": 5,
    "running": 4,
    "unauthorized_regions": 0,
    "security_issues": 0
  },
  "s3": {
    "total_buckets": 12,
    "public_buckets": 0,
    "issues": 0
  },
  "cost": {
    "daily_cost": "15.50",
    "monthly_estimate": "465.00",
    "threshold": "10.00",
    "within_budget": false
  }
}
```

**GET /api/events?limit=20&severity=HIGH**
```json
{
  "events": [
    {
      "timestamp": "2026-05-10T12:30:00Z",
      "severity": "HIGH",
      "check_type": "cost",
      "message": "Daily cost $25.50 exceeds threshold $10.00",
      "details": {...}
    }
  ],
  "total": 156
}
```

**GET /api/actions?limit=10**
```json
{
  "actions": [
    {
      "timestamp": "2026-05-10T12:30:00Z",
      "action_type": "ec2_stop",
      "resource_id": "i-1234567890abcdef0",
      "status": "success",
      "message": "Instance stopped successfully"
    }
  ]
}
```

---

## 5.3: GitHub Release 생성

```bash
# v1.3.0 릴리스 생성
gh release create v1.3.0 \
  --title "AWS Guardian v1.3.0 - Async & Caching Performance Release" \
  --notes "$(cat docs/V1_3_RELEASE_NOTES.md)"

# 또는 웹 UI로 생성
# https://github.com/jinyounghwa/backend_loader/releases/new
```

### 릴리스 체크리스트

- [ ] v1.3.0 태그 확인
- [ ] 배포 가이드 완성
- [ ] 릴리스 노트 공개
- [ ] GitHub Release 생성
- [ ] AWS 배포 완료
- [ ] Telegram 알림 테스트
- [ ] 웹 대시보드 접속 가능

---

## 5.4: 모니터링 & 검증

### 1시간 테스트

```bash
# 1. EventBridge 트리거 대기
# 매 1시간마다 자동 실행

# 2. CloudWatch 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=guardianChecker \
  --statistics Average,Maximum

# 3. Telegram 알림 확인
# Telegram 채팅방에서 알림 수신 확인

# 4. DynamoDB 이벤트 로그 확인
aws dynamodb scan \
  --table-name guardian-events \
  --limit 5 \
  --query 'Items'
```

### CloudWatch 대시보드

```bash
# 메인 메트릭 모니터링
# - Lambda Duration (실행 시간)
# - ErrorCount (에러)
# - Invocations (호출 횟수)
# - Cache Hit Rate (캐시 적중률)
```

---

## 5.5: 문제 해결

### 배포 실패

```bash
# CloudFormation 로그 확인
aws cloudformation describe-stack-events \
  --stack-name aws-guardian-v1.3 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# 롤백
aws cloudformation delete-stack \
  --stack-name aws-guardian-v1.3
```

### Lambda 실행 오류

```bash
# 로그 확인
aws logs tail /aws/lambda/guardianChecker --follow

# 최근 오류만
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardianChecker \
  --filter-pattern "ERROR"
```

### Redis 연결 오류

```bash
# ElastiCache 상태 확인
aws elasticache describe-cache-clusters \
  --cache-cluster-id guardian-cache \
  --query 'CacheClusters[0].CacheClusterStatus'

# 수동 재시작
aws elasticache reboot-cache-cluster \
  --cache-cluster-id guardian-cache
```

---

## 5.6: 성공 기준

✅ **배포**
- AWS Lambda 정상 작동
- EventBridge 1시간 스케줄 실행
- Telegram 알림 수신

✅ **웹 대시보드**
- 상태 페이지 조회 가능
- 이벤트 로그 표시
- 자동 대응 기록 조회

✅ **모니터링**
- CloudWatch 메트릭 수집
- 알림 전달 정상
- 로그 저장 정상

✅ **릴리스**
- v1.3.0 GitHub Release 생성
- 배포 가이드 완성
- 릴리스 노트 공개

---

## 5.7: 타임라인

| 단계 | 예상 시간 | 필수 리소스 |
|------|----------|-----------|
| AWS 배포 설정 | 10 min | AWS 계정, SAM |
| SAM deploy | 15 min | AWS 권한 |
| 웹 대시보드 개발 | 60 min | Node.js, Next.js |
| API 엔드포인트 | 30 min | Python, boto3 |
| 모니터링 설정 | 15 min | AWS CLI |
| GitHub Release | 5 min | gh CLI |
| **Total** | **135 min** | - |

---

## 5.8: 다음 단계 (Sprint 26)

Sprint 25 완료 후:

1. **웹 대시보드 고도화**
   - 실시간 이벤트 스트림 (WebSocket)
   - 수동 작업 실행 (EC2 중지, S3 차단)
   - 알림 설정 UI

2. **ML 기반 위협 감지**
   - 이상 탐지 알고리즘
   - 위협 점수 계산
   - 자동 격리 규칙

3. **모바일 앱**
   - React Native 기반
   - 푸시 알림
   - 모바일 대시보드

4. **고급 통합**
   - Slack 채널
   - PagerDuty 인시던트
   - Datadog 메트릭

---

## 참고자료

- **배포 가이드**: `docs/DEPLOYMENT_GUIDE_V1_3.md`
- **릴리스 노트**: `docs/V1_3_RELEASE_NOTES.md`
- **SAM 문서**: https://docs.aws.amazon.com/serverless-application-model/
- **Next.js 문서**: https://nextjs.org/docs

---

**Sprint 25 준비 완료!** 🚀
