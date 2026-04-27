# Sprint 3: 구현 계획서

> DynamoDB GSI + API 쿼리 최적화

---

## 📋 구현 단계

### Phase 1: Terraform DynamoDB 스키마 업데이트

**파일**: `terraform/dynamodb.tf`

```hcl
# GSI 1: event_type + timestamp (최신순)
resource "aws_dynamodb_table" "events" {
  # ... 기존 설정 ...

  # GSI 추가
  global_secondary_index {
    name            = "event_type_timestamp_idx"
    hash_key        = "event_type"
    range_key       = "timestamp"
    projection_type = "KEYS_ONLY"
  }

  # GSI 2: severity + timestamp
  global_secondary_index {
    name            = "severity_timestamp_idx"
    hash_key        = "severity"
    range_key       = "timestamp"
    projection_type = "KEYS_ONLY"
  }

  # GSI 3: check_type + timestamp (향후 확장)
  # (현재 데이터 구조에서 check_type은 details 내부)
}
```

**변경 사항:**
- 기존 table 정의 유지
- GSI 2개 추가 (event_type, severity)
- Projection: KEYS_ONLY (비용 절감)

---

### Phase 2: 필드 추가 (선택사항)

**문제**: 현재 `severity` 필드가 top-level에 있지만, `check_type`은 `details` 내부에 있음

**옵션**:
1. ✅ 추천: severity GSI만 추가 (이미 top-level)
2. 향후: DynamoDB Stream으로 check_type 추출 (복잡)

---

### Phase 3: DynamoDB Query 메서드 추가

**파일**: `apps/web/src/lib/dynamodb.ts`

#### 메서드 1: 이벤트 타입별 조회

```typescript
export async function getEventsByType(
  eventType: string, 
  hours: number = 24
): Promise<any[]> {
  const cutoffTime = new Date(
    Date.now() - hours * 60 * 60 * 1000
  ).toISOString();

  const input: QueryCommandInput = {
    TableName: TABLE_NAME,
    IndexName: 'event_type_timestamp_idx',
    KeyConditionExpression: 'event_type = :et AND #ts > :cutoff',
    ExpressionAttributeNames: { '#ts': 'timestamp' },
    ExpressionAttributeValues: {
      ':et': eventType,
      ':cutoff': cutoffTime,
    },
    ScanIndexForward: false, // DESC (최신순)
    Limit: 100,
  };

  const result = await docClient.send(new QueryCommand(input));
  return result.Items || [];
}
```

#### 메서드 2: Severity별 조회

```typescript
export async function getEventsBySeverity(
  severity: string,
  hours: number = 24
): Promise<any[]> {
  const cutoffTime = new Date(
    Date.now() - hours * 60 * 60 * 1000
  ).toISOString();

  const input: QueryCommandInput = {
    TableName: TABLE_NAME,
    IndexName: 'severity_timestamp_idx',
    KeyConditionExpression: 'severity = :sev AND #ts > :cutoff',
    ExpressionAttributeNames: { '#ts': 'timestamp' },
    ExpressionAttributeValues: {
      ':sev': severity,
      ':cutoff': cutoffTime,
    },
    ScanIndexForward: false,
    Limit: 100,
  };

  const result = await docClient.send(new QueryCommand(input));
  return result.Items || [];
}
```

#### 메서드 3: 최신 Check Result 조회 (최적화)

```typescript
export async function getLatestCheckResultOptimized() {
  // event_type='check_result' GSI 사용
  const input: QueryCommandInput = {
    TableName: TABLE_NAME,
    IndexName: 'event_type_timestamp_idx',
    KeyConditionExpression: 'event_type = :et',
    ExpressionAttributeValues: { ':et': 'check_result' },
    ScanIndexForward: false, // DESC
    Limit: 1,
  };

  const result = await docClient.send(new QueryCommand(input));
  return result.Items?.[0] || null;
}
```

---

### Phase 4: API 라우트 리팩토링

**파일**: `apps/web/src/app/api/events/route.ts`

#### Before (Scan 사용)
```typescript
const rawEvents = await getRecentEvents(hours);  // ❌ Full Scan
events = events.filter(e => e.event_type === typeFilter);  // ❌ 메모리 필터
```

#### After (Query 사용)
```typescript
let rawEvents;

if (typeFilter && typeFilter !== 'all') {
  // ✅ GSI Query로 직접 조회
  rawEvents = await getEventsByType(typeFilter, hours);
} else if (severityFilter && severityFilter !== 'all') {
  // ✅ GSI Query로 직접 조회
  rawEvents = await getEventsBySeverity(severityFilter, hours);
} else {
  // 기본: timestamp로 전체 조회 (기존 방식)
  rawEvents = await getRecentEvents(hours);
}

// ✅ 필터링 필요 없음 (DB에서 이미 필터됨)
```

---

## 📊 성능 비교

### Before (Scan 방식)
```
Query: getRecentEvents(24)
└─ ScanCommand
   ├─ 모든 데이터 스캔 (예: 10,000개)
   ├─ FilterExpression 적용 (예: timestamp, event_type)
   ├─ 결과: 100개만 반환
   └─ RCU 비용: 10,000 RCU (!) 낭비
```

### After (Query 방식)
```
Query: getEventsByType('ec2', 24)
└─ QueryCommand on event_type_timestamp_idx
   ├─ event_type = 'ec2' 직접 조회
   ├─ timestamp 범위 필터 적용
   ├─ 결과: 100개 반환
   └─ RCU 비용: 10-50 RCU (✅ 99% 절감)
```

---

## ✅ 검증 계획

### 1. LocalStack 테스트
```bash
./start.sh
# DynamoDB 테이블 생성 및 GSI 확인
aws dynamodb describe-table \
  --table-name aws-guardian-events \
  --endpoint-url http://localhost:4566
```

### 2. 쿼리 성능 테스트
```bash
# Before: Scan (느림)
time curl "http://localhost:3000/api/events?hours=24&type=ec2"

# After: Query (빠름)
# 응답 시간 비교
```

### 3. 데이터 검증
- ✅ 필터링 결과 동일성 확인
- ✅ 정렬 순서 확인 (DESC)
- ✅ 시간 범위 필터 동작 확인

---

## 📌 주의사항

### 1. 기존 데이터 호환성
- GSI 추가는 기존 테이블 영향 없음
- 새 데이터부터 GSI 인덱싱됨
- 기존 Scan 쿼리는 계속 동작

### 2. Projection 전략
```
KEYS_ONLY (권장) vs ALL
- KEYS_ONLY: 비용 낮음 (pk, sk만 저장)
- ALL: 모든 속성 저장 (추가 비용)

현재: KEYS_ONLY
(details는 필요시 pk/sk로 원본 조회)
```

### 3. 비용 계산
```
Before: ~$0.50/월
After: ~$0.05/월

GSI 추가 비용: 미미 (PAY_PER_REQUEST)
쿼리 효율: 99% ⬆️
```

---

## 🔄 배포 순서

1. ✅ Terraform 코드 작성
2. ✅ DynamoDB 마이그레이션 계획
3. ✅ Query 메서드 구현
4. ✅ API 라우트 리팩토링
5. ✅ LocalStack 테스트
6. ✅ 성능 검증
7. ✅ git commit
8. ⏳ (선택) AWS 배포

---

## 📝 관련 파일

| 파일 | 변경 내용 |
|------|---------|
| `terraform/dynamodb.tf` | GSI 추가 |
| `apps/web/src/lib/dynamodb.ts` | Query 메서드 추가 |
| `apps/web/src/app/api/events/route.ts` | Query 사용으로 리팩토링 |
| `lambda/guardian/storage/dynamodb.py` | (선택) Python Query 메서드 추가 |

---

## ⏸️ 대기 중

🔄 **Gemini CLI 분석 결과 대기 중**
- GSI 설계 최적화
- 추가 인덱싱 전략
- 쿼리 성능 권장사항
