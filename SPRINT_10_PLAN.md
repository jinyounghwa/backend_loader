# Sprint 10: Lambda 성능 최적화 + 모니터링 강화

**상태**: 📋 계획 중 (Gemini 협업 예정)
**계획 수립**: 2026-05-03
**시작 예정**: 2026-05-12
**완료 예정**: 2026-05-12 (3시간)

---

## 목표

Lambda 콜드 스타트 성능 개선 + CloudWatch 모니터링 확장

---

## 현재 상황 분석

### 성능 현황
- **Lambda 메모리**: 512MB (Sprint 9에서 256MB → 512MB 증설)
- **Timeout**: 300초 (충분함)
- **콜드 스타트**: 미측정 (목표: <500ms)
- **실행 시간**: 평균 5-10초 (추정)

### 모니터링 현황
- **CloudWatch Logs**: 활성화 (retention 14일)
- **메트릭**: Duration, Errors, Throttles만 수집
- **대시보드**: 없음 (수동 확인 필요)
- **알람**: 없음 (에러 감지 불가)

### 병목 지점 (예상)
1. **boto3 초기화**: 매 호출마다 클라이언트 생성
2. **DynamoDB 쿼리**: 페이지네이션 반복문
3. **Gemini API**: 네트워크 지연 (1-2초)
4. **PDF 생성**: fpdf2 메모리 사용 (대용량 파일)

---

## Phase 1: Lambda 콜드 스타트 최적화 (1.5시간)

### 1.1 boto3 세션 캐싱

**현재 코드**:
```python
def get_status():
    ec2 = AWSClientProvider.get_client('ec2')  # 매번 생성
    s3 = AWSClientProvider.get_client('s3')
    # ...
```

**최적화 방법** (Gemini 검증 필요):
- 글로벌 스코프에서 클라이언트 초기화
- Lambda 컨테이너 재사용 시 캐시된 클라이언트 사용
- 리전별 캐싱 지원

**구현 파일**:
```
terraform/lambda.tf: 환경변수 추가 (CACHE_BOTO3=true)
lambda/guardian/aws_client_provider.py: REFACTOR
  - _client_cache: dict (리전별 클라이언트 저장)
  - get_client(): 캐시 확인 → 없으면 생성 → 저장
```

### 1.2 DynamoDB 쿼리 최적화

**문제**: 페이지네이션 반복문에서 여러 API 호출

**최적화**:
- `Limit` 파라미터 조정 (1000 이벤트 한 번에 조회)
- GSI 선택 최적화 (AllEventsIndex vs TypeTimestampIndex)
- 불필요한 속성 필터링 (`ProjectionExpression`)

**구현**:
```python
# 전: 10번 Query 호출 (페이지네이션)
# 후: 1-2번 Query 호출 (Limit 1000)
```

### 1.3 Lambda 레이어 최적화

**현재**: 모든 의존성을 포함 (크기: ~50MB 추정)

**최적화**:
- 불필요한 패키지 제거
- 컴파일된 바이너리 정리 (`.pyc`, `__pycache__`)
- 선택적 의존성 분리 (Gemini API는 `/insights` 명령어에서만 사용)

**빌드 스크립트**:
```bash
# python_dependencies.zip 최적화
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete
# 크기 목표: <100MB (Lambda 250MB 제한)
```

---

## Phase 2: 모니터링 강화 (1시간)

### 2.1 CloudWatch 메트릭 수집

**신규 메트릭**:
- `ColdStartDuration`: 콜드 스타트 시간 (구분 필요)
- `DynamoDBQueryTime`: 각 쿼리 실행 시간
- `GeminiAPILatency`: Gemini API 응답 시간
- `MemoryUsed`: 실제 메모리 사용량 (CloudWatch Logs Insights)

**구현**:
```python
# CloudWatch 메트릭 발행
cloudwatch = AWSClientProvider.get_client('cloudwatch')

def emit_metric(metric_name: str, value: float, unit: str = 'Milliseconds'):
    cloudwatch.put_metric_data(
        Namespace='aws-guardian',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.now(timezone.utc)
        }]
    )
```

### 2.2 CloudWatch 대시보드

**대시보드**: `aws-guardian-performance.json` (Terraform)

```json
{
  "name": "AWS Guardian Performance",
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["aws-guardian", "Duration", {"stat": "Average"}],
          ["aws-guardian", "ColdStartDuration"],
          ["aws-guardian", "DynamoDBQueryTime"],
          ["aws-guardian", "GeminiAPILatency"],
          ["aws-guardian", "MemoryUsed"]
        ],
        "period": 300,
        "stat": "Average"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "fields @duration, @memoryUsed | stats avg(@duration) as avgDuration"
      }
    }
  ]
}
```

### 2.3 CloudWatch 알람

**알람**:
- Lambda 에러율 > 5% (1분): SNS 알림
- Lambda 실행 시간 > 30초: 경고
- DynamoDB 제한된 요청: 경고

---

## Phase 3: 로그 분석 및 최적화 (1시간)

### 3.1 CloudWatch Logs Insights 쿼리

**쿼리 1**: 콜드 스타트 식별
```sql
fields @timestamp, @duration, @initDuration
| filter @initDuration > 0
| stats count() as coldStarts, avg(@initDuration) as avgColdStart
```

**쿼리 2**: 느린 요청 식별
```sql
fields @timestamp, @duration, @message
| filter @duration > 10000
| stats count() as slowRequests by @message
```

**쿼리 3**: 메모리 사용량
```sql
fields @memoryUsed, @memorySize
| stats avg(@memoryUsed) as avgMemory, max(@memoryUsed) as maxMemory
```

### 3.2 성능 병목 분석

**분석 기준**:
- 콜드 스타트: > 1초 (높음)
- 쿼리 시간: > 1초 (높음)
- 메모리 사용량: > 80% (높음)

**개선 우선순위**:
1. 콜드 스타트 (경영진이 가장 관심)
2. 메모리 사용량 (비용 영향)
3. 쿼리 성능 (사용자 경험)

---

## Gemini 협업 체크리스트

### Phase 1: 아키텍처 검증
- [ ] boto3 캐싱 전략 (스레드 안전성, 리전별 처리)
- [ ] DynamoDB 쿼리 최적화 (Limit vs 페이지네이션 트레이드오프)
- [ ] Lambda 레이어 크기 최적화 (250MB 제한)
- [ ] 메모리 설정 (512MB vs 1GB vs 1.5GB 비교)

**Gemini 검증 항목**:
- ⚠️ boto3 싱글톤 패턴 (스레드 안전성)
- ⚠️ DynamoDB Limit 값 선택 (메모리 vs API 호출)
- ⚠️ Lambda 콜드 스타트 측정 방법
- ⚠️ 메모리 증설의 비용-성능 트레이드오프

### Phase 2: 구현
- [ ] CloudWatch 메트릭 발행
- [ ] 대시보드 생성
- [ ] 알람 설정

### Phase 3: 검증
- [ ] CloudWatch Logs Insights 쿼리 작성
- [ ] 성능 병목 분석
- [ ] 개선 효과 측정

---

## 예상 효과

| 항목 | Before | After | 개선율 |
|------|--------|-------|--------|
| 콜드 스타트 | 2-3초 (추정) | <1초 | 70% |
| 쿼리 시간 | 500-800ms | 200-300ms | 60% |
| Lambda 비용 | ~$1/월 | ~$0.5/월 | 50% |
| 메모리 사용 | 350MB | 250MB | 30% |

---

## 파일 변경 요약

| 파일 | 변경 내용 |
|------|---------|
| terraform/lambda.tf | 메트릭 발행용 IAM 정책 추가 |
| terraform/cloudwatch.tf | 대시보드 + 알람 정의 |
| lambda/guardian/aws_client_provider.py | boto3 캐싱 (리전별) |
| lambda/guardian/handlers/metrics.py | 메트릭 발행 헬퍼 |
| lambda/guardian/responders/telegram_bot.py | 메트릭 로깅 추가 |
| scripts/analyze-performance.sh | CloudWatch Logs Insights 쿼리 |

---

## 시작 체크리스트

- [ ] Gemini 아키텍처 검증 받기
- [ ] boto3 캐싱 구현
- [ ] CloudWatch 메트릭 발행
- [ ] 대시보드 생성
- [ ] CloudWatch Insights 쿼리 작성
- [ ] 성능 기준 수집 (1주일)
- [ ] 개선 효과 측정

---

## 참고 자료

- [Lambda 콜드 스타트 최적화](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [CloudWatch 메트릭](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/cloudwatch-limits-eventbridge.html)
- [DynamoDB 성능 튜닝](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices.html)
