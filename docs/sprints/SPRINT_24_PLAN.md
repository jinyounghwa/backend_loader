# Sprint 24: Deployment & Validation

**Status:** 📋 PLANNED  
**Target:** AWS 배포, 테스트 검증, 성능 벤치마크, v1.3.0 정식 릴리스

---

## Sprint 24 Overview

Sprint 23에서 완성된 v1.3.0-rc1을 정식 릴리스하기 위한 최종 검증 및 배포:

1. **SAM 배포** - AWS Lambda, EventBridge, DynamoDB 배포
2. **테스트 검증** - 31+ 테스트 실행 및 커버리지 확인
3. **성능 벤치마크** - 3x+ 성능 개선 검증
4. **v1.3.0 정식 릴리스** - GitHub Release 생성

---

## 4.1: AWS 배포

### SAM CLI 배포 (Interactive)

```bash
# SAM 설정 및 배포
cd /path/to/backend_loader
sam deploy --guided -t sam.yaml

# 질문 항목:
# - Stack Name: aws-guardian-v1.3
# - AWS Region: ap-northeast-2 (또는 선택)
# - Parameter overrides: (엔터로 기본값 사용 또는 커스텀)
#   - TelegramBotToken: [봇 토큰]
#   - TelegramChatId: [채팅 ID]
#   - CostThreshold: 10.0
# - Confirm changes before deploy: Y
# - Allow SAM CLI IAM role creation: Y
# - Save parameters to samconfig.toml: Y
```

### 배포 후 확인

```bash
# CloudFormation Stack 확인
aws cloudformation describe-stacks \
  --stack-name aws-guardian-v1.3 \
  --query 'Stacks[0].{StackStatus:StackStatus,CreationTime:CreationTime}'

# Lambda 함수 확인
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `guardian`)].{Name:FunctionName,Runtime:Runtime}'

# EventBridge 규칙 확인
aws events list-rules \
  --query 'Rules[?contains(Name, `guardian`)].{Name:Name,State:State,ScheduleExpression:ScheduleExpression}'

# DynamoDB 테이블 확인
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `guardian`)]'
```

### 환경 변수 설정 (배포 후)

```bash
# Lambda 환경 변수 업데이트
aws lambda update-function-configuration \
  --function-name guardianChecker \
  --environment Variables='{
    "CACHE_BACKEND":"redis",
    "REDIS_URL":"redis://elasticache-endpoint:6379/0",
    "AWS_ORGANIZATIONS_ENABLED":"true"
  }'
```

---

## 4.2: 테스트 검증

### 테스트 환경 재설정

```bash
# 새로운 가상환경 생성
rm -rf venv_sprint24
python3 -m venv venv_sprint24
source venv_sprint24/bin/activate

# 의존성 설치
pip install -r lambda/requirements.txt
pip install pytest pytest-asyncio pytest-mock
```

### Unit 테스트 실행

```bash
# 캐시 테스트 (11 test cases)
pytest tests/guardian/test_cache.py -v

# 비동기 체커 테스트 (12 test cases)
pytest tests/guardian/test_async_checkers.py -v

# 멀티 어카운트 테스트 (8 test cases)
pytest tests/guardian/test_multi_account.py -v

# 전체 단위 테스트
pytest tests/guardian/test_cache.py tests/guardian/test_async_checkers.py tests/guardian/test_multi_account.py -v --tb=short
```

**예상 결과:** 31 passing, 0 failing

### Integration 테스트 (LocalStack)

```bash
# LocalStack이 실행 중인지 확인
docker-compose ps | grep localstack

# LocalStack 헬스 체크
curl -s http://localhost:4566/_localstack/health | jq '.services.s3'

# Integration 테스트 실행
export LOCALSTACK_ENDPOINT=http://localhost:4566
pytest tests/guardian/test_integration_localstack.py -v -s --tb=short

# 테스트별 검증
# - CostChecker: 비용 조회 정확성
# - EC2Checker: 인스턴스 감지 및 보안 그룹
# - S3Checker: 퍼블릭 버킷 감지
# - Multi-Checker: 동시 실행 및 결과 집계
```

### 코드 커버리지 분석

```bash
# 전체 커버리지 리포트 생성
pytest tests/guardian/ --cov=lambda/guardian --cov-report=html --cov-report=term-missing

# 예상 커버리지
# - Cache layer: >95%
# - Async checkers: >85%
# - Orchestrator: >87%
# - Overall: >85%

# HTML 리포트 확인
open htmlcov/index.html
```

---

## 4.3: 성능 벤치마크

### 비동기 성능 검증

```bash
# 성능 테스트 실행
pytest tests/guardian/test_performance.py -v -s

# 예상 결과:
# ✅ Memory cache set: <0.1ms per operation
# ✅ Memory cache get: <1ms per operation
# ✅ TTL expiration: <100ms for 1000 items
# ✅ EC2 parallel regions: 3x speedup (0.1s vs 0.3s)
# ✅ S3 parallel buckets: 3x speedup (0.1s vs 0.5s)
# ✅ 10 concurrent checkers: <0.2s (parallel) vs 1.0s (sequential)
```

### 캐시 효율성

```bash
# Redis 캐시 적중률 모니터링
redis-cli -h elasticache-endpoint INFO stats

# 예상 적중률
# - Cold start (0-5분): 0-10%
# - Warm cache (5분+): 65-70%
# - API 호출 절감: -60%
```

### 메모리 사용량

```bash
# Lambda CloudWatch 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=guardianChecker \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-11T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum

# 예상 결과
# - v1.2 vs v1.3 비교: 2.9x 속도 개선
# - 메모리: 256MB Lambda로 동시성 2배 증가
# - 비용: 월 40-50% 절감
```

---

## 4.4: 릴리스 준비

### GitHub Release 생성

```bash
# v1.3.0 릴리스 노트 작성
gh release create v1.3.0 \
  --title "AWS Guardian v1.3.0 - Performance & Async Release" \
  --notes "$(cat docs/V1_3_RELEASE_NOTES.md)"

# 또는 웹 UI로 생성
# 1. GitHub → Releases → Draft a new release
# 2. Tag: v1.3.0
# 3. Title: "AWS Guardian v1.3.0 - Performance & Async Release"
# 4. Description: docs/V1_3_RELEASE_NOTES.md 내용 복사
# 5. "Publish release" 클릭
```

### 릴리스 체크리스트

- [ ] v1.3.0 태그 GitHub에 푸시됨
- [ ] 31+ 단위 테스트 통과
- [ ] Integration 테스트 LocalStack 통과
- [ ] 성능 벤치마크 3x+ 확인
- [ ] 코드 커버리지 >85%
- [ ] 배포 가이드 검토
- [ ] GitHub Release 생성
- [ ] 배포 완료 (AWS Lambda)
- [ ] CloudWatch 메트릭 모니터링 시작

---

## 4.5: 배포 후 모니터링

### CloudWatch 대시보드 설정

```bash
# 메인 메트릭 모니터링
# 1. Duration - Lambda 실행 시간
# 2. ErrorCount - 에러 발생 횟수
# 3. Invocations - 호출 횟수
# 4. Throttles - 스로틀링 발생 여부

# 알람 설정 (권장)
aws cloudwatch put-metric-alarm \
  --alarm-name guardian-high-errors \
  --metric-name ErrorCount \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### 24시간 모니터링

```bash
# Telegram 알림 확인
# - 1시간마다 scheduler 실행
# - 비용 이상 감지 → 즉시 알림
# - EC2/S3 이상 감지 → 즉시 알림

# DynamoDB 이벤트 로그 확인
aws dynamodb scan \
  --table-name guardian-events \
  --limit 10 \
  --query 'Items[].[timestamp,severity,check_type]' \
  --output table
```

---

## 4.6: 문제 해결 & 롤백

### 배포 실패 시 롤백

```bash
# 이전 버전으로 복구
sam deploy -t sam.yaml \
  --parameter-overrides LambdaCodeVersion=v1.2.0

# 또는 CloudFormation으로 롤백
aws cloudformation cancel-update-stack \
  --stack-name aws-guardian-v1.3
```

### 테스트 실패 시 대응

```bash
# 실패한 테스트 디버깅
pytest tests/guardian/test_async_checkers.py::TestEC2CheckerAsync -vv --tb=long

# LocalStack 문제
docker-compose -f docker-compose.localstack.yml logs localstack | tail -50

# Redis 연결 문제
redis-cli -h elasticache-endpoint PING
```

---

## 4.7: 성공 기준

✅ **배포**
- AWS Lambda, EventBridge, DynamoDB 정상 배포
- CloudWatch 메트릭 수집 시작
- Telegram 알림 정상 작동

✅ **테스트**
- 31+ 테스트 모두 통과
- 코드 커버리지 >85%
- Integration 테스트 LocalStack 통과

✅ **성능**
- 비동기 실행 3x+ 성능 개선 확인
- 캐시 적중률 65-70%
- 메모리 사용량 50% 감소

✅ **릴리스**
- GitHub Release v1.3.0 생성
- 배포 가이드 완성
- 릴리스 노트 공개

---

## 4.8: 타임라인 & 리소스

| 작업 | 예상 시간 | 필수 리소스 |
|------|----------|-----------|
| SAM 배포 설정 | 10 min | AWS 계정, SAM CLI |
| 테스트 환경 재설정 | 5 min | Python 3.12+, pip |
| 단위 테스트 실행 | 5 min | pytest |
| Integration 테스트 | 10 min | LocalStack, Docker |
| 성능 벤치마크 | 10 min | pytest |
| 커버리지 분석 | 5 min | pytest-cov |
| GitHub Release 생성 | 5 min | GitHub CLI/웹 UI |
| 모니터링 설정 | 10 min | AWS CLI |
| **Total** | **60 min** | - |

---

## 4.9: 다음 단계 (Sprint 25)

Sprint 24 완료 후:

1. **웹 대시보드** - Next.js 기반 실시간 모니터링
2. **고급 위협 감지** - ML 기반 이상 탐지
3. **알림 개선** - Slack, PagerDuty 통합
4. **다중 계정 확장** - Organizations API 풀 지원
5. **성능 최적화** - Lambda 메모리 자동 조정

---

## 참고자료

- **배포 가이드**: `docs/DEPLOYMENT_GUIDE_V1_3.md`
- **릴리스 노트**: `docs/V1_3_RELEASE_NOTES.md`
- **테스트 계획**: `docs/sprints/SPRINT_23_PHASE_3_PLAN.md`
- **SAM 문서**: https://docs.aws.amazon.com/serverless-application-model/
- **aioboto3 문서**: https://github.com/aio-libs/aioboto3

---

**Sprint 24 시작 준비 완료!** 🚀
