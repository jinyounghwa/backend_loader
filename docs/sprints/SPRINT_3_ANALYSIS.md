# Sprint 3: DynamoDB API 최적화 - 현재 분석

> GSI (Global Secondary Index) 설계 및 API 쿼리 최적화

**상태**: 🔄 진행 중 (Gemini CLI 분석 중)  
**시작일**: 2026-04-27

---

## 📊 현재 상황 분석

### 현재 DynamoDB 구조

**테이블: `aws-guardian-events`**
```
Partition Key: timestamp (S)
Sort Key: event_type (S)
Billing: PAY_PER_REQUEST
TTL: expiration_time (30일 자동 삭제)
```

**테이블: `aws-guardian-responses`**
```
Partition Key: timestamp (S)
Sort Key: action_type (S)
Billing: PAY_PER_REQUEST
```

### 🔴 현재 문제점

1. **비효율한 쿼리**
   ```typescript
   // api/events/route.ts 현재 방식:
   const rawEvents = await getRecentEvents(hours);  // ❌ 모든 데이터 스캔
   events.filter(e => e.event_type === typeFilter)  // ❌ 메모리에서 필터
   ```

2. **GSI 부재**
   - event_type으로 효율적으로 조회 불가
   - severity로 조회 불가
   - check_type으로 조회 불가

3. **쿼리 패턴 분석**
   ```
   현재 접근 패턴:
   1. 최근 24시간 모든 이벤트 → Full Scan
   2. event_type 필터 → 메모리 필터
   3. severity 필터 → 메모리 필터
   4. 날짜 범위 필터 → 메모리 필터
   ```

4. **비용 영향**
   ```
   - 매일 scan 작업 → RCU 소비 증가
   - 대규모 데이터 → 메모리 필터로 비효율
   - 예: 10,000 이벤트 스캔해서 100개만 필터 = 99% 낭비
   ```

---

## 🎯 필요한 GSI 설계

### GSI 1: event_type + timestamp (역순)
```
Partition Key: event_type
Sort Key: timestamp (DESC)
Projection: KEYS_ONLY (cost 절감)

쿼리 예:
- "ec2" 타입의 모든 이벤트
- "s3" 타입의 최근 24시간 이벤트
```

### GSI 2: severity + timestamp (역순)
```
Partition Key: severity
Sort Key: timestamp (DESC)
Projection: KEYS_ONLY

쿼리 예:
- "critical" 이벤트만 조회
- "warning" 이벤트 (최근 7일)
```

### GSI 3: check_type + timestamp (역순)
```
Partition Key: check_type (요약 정보에서)
Sort Key: timestamp (DESC)
Projection: ALL (필드 추가 필요)

쿼리 예:
- "cost" 체크 결과만
- "ec2" 체크 결과 (시간 범위)
```

---

## 📋 Gemini CLI 분석 대기

**실행 명령**:
```bash
./scripts/gemini-ask.sh "Design a Global Secondary Index (GSI) strategy..."
```

**예상 분석 내용**:
1. ✅ GSI 설계 (pk, sk, projection)
2. ✅ Query vs Scan 최적화
3. ✅ 비용 영향 분석
4. ✅ API 라우트 리팩토링

---

## 🛠️ 예상 구현 (Claude Code)

### 1. Terraform DynamoDB 업데이트
```hcl
# Global Secondary Index 추가
resource "aws_dynamodb_table_gsi" "event_type_idx" {
  hash_key       = "event_type"
  range_key      = "timestamp"
  projection_type = "KEYS_ONLY"
}

resource "aws_dynamodb_table_gsi" "severity_idx" {
  hash_key       = "severity"
  range_key      = "timestamp"
  projection_type = "KEYS_ONLY"
}
```

### 2. DynamoDB 쿼리 최적화
```python
# storage/dynamodb.py
def get_events_by_type(self, event_type: str, hours: int = 24):
    """GSI를 사용해서 효율적으로 조회"""
    from boto3.dynamodb.conditions import Key
    
    # Query (Scan 대신)
    response = self.table.query(
        IndexName='event_type_idx',
        KeyConditionExpression=Key('event_type').eq(event_type) & 
                               Key('timestamp').gt(cutoff_time)
    )
    return response['Items']
```

### 3. API 라우트 리팩토링
```typescript
// api/events/route.ts - 최적화된 버전
async function GET(request: Request) {
  const typeFilter = searchParams.get('type');
  const severityFilter = searchParams.get('severity');
  
  if (typeFilter && typeFilter !== 'all') {
    // GSI 쿼리 사용
    return queryByType(typeFilter, hours);
  } else if (severityFilter && severityFilter !== 'all') {
    // severity GSI 쿼리
    return queryBySeverity(severityFilter, hours);
  } else {
    // 기본 쿼리 (timestamp 기반)
    return getRecentEvents(hours);
  }
}
```

---

## 📊 성능 예상

| 메트릭 | Before | After | 개선율 |
|--------|--------|-------|--------|
| **Query Time** | 2-3초 (scan) | 200-400ms (query) | 85-90% ⬇️ |
| **RCU/Query** | 1000+ | 10-100 | 90-99% ⬇️ |
| **Cost/Day** | ~$0.50 | ~$0.05 | 90% ⬇️ |
| **Latency** | 높음 | 낮음 | ✅ |

---

## ✅ 다음 단계

1. ⏳ Gemini 분석 완료 대기
2. 🔍 분석 결과 검토
3. 🛠️ Terraform + API 구현
4. 🧪 로컬 테스트 (LocalStack)
5. 📝 NEXT_STEPS.md 업데이트
6. ✨ git commit

---

## 📌 참고

- DynamoDB 쿼리 비용: 읽은 항목 수 기준 (Scan은 필터링 전 계산)
- GSI는 별도의 스루풋 프로비저닝 필요 없음 (PAY_PER_REQUEST)
- TTL 설정으로 자동 정리 (30일)
