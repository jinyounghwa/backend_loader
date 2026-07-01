---
module: storage
path: 04-Storage-Config
keywords: dynamodb, storage, event-log, ttl, audit
---

# DynamoDB Storage — 이벤트 저장소

#module-storage #api-aws

## 목적

모든 감지 이벤트와 자동 대응 내역을 DynamoDB에 저장하여 감사 추적과 Discord `/history` 명령어에 활용합니다.

## 주요 파일

`lambda/guardian/storage/dynamodb.py`

## 테이블 설계

```
테이블명: aws-guardian-events (기본값, DYNAMODB_TABLE_NAME으로 변경 가능)

파티션키: event_id  (String, UUID)
정렬키:   timestamp (String, ISO8601)

속성:
  event_type: "cost_anomaly" | "ec2_anomaly" | "s3_anomaly"
              | "auto_remediation" | "discord_command"
  severity:   "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  details:    Map (체커별 상세)
  account_id: String
  ttl:        Number (Unix timestamp, 자동 만료)
```

## float → Decimal 변환

```python
def _convert_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))   # float를 Decimal로 변환
    ...
```

> [!warning] DynamoDB float 금지
> DynamoDB Python SDK는 Python `float`를 직접 저장하지 못합니다.
> 부동소수점 정밀도 문제 때문에 `Decimal`을 사용합니다.
> `Decimal(str(15.30))` → `Decimal('15.30')` (정확한 표현)

## save_event 메서드

```python
def save_event(
    self,
    event_type: str,
    severity: str,
    details: Dict[str, Any],
    account_id: str = "current"
) -> bool:
    item = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": _convert_floats(details),
        "account_id": account_id,
        "ttl": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    }
    return self._put_item(item)
```

## TTL (Time To Live)

```
저장 시각 + 30일 후 DynamoDB가 자동으로 항목 삭제
→ 감사 로그 보관 기간: 30일
→ 스토리지 비용 자동 관리
```

> [!tip] DynamoDB TTL 설정
> TTL은 DynamoDB 콘솔이나 Terraform에서 `ttl` 속성을 활성화해야 합니다.
> `terraform/dynamodb.tf`에서 TTL 설정을 확인하세요.

## AWSClientProvider 패턴

```python
class DynamoDBStorage:
    def __init__(self, table_name=None):
        self.table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
```

`AWSClientProvider`는 `Config.get_boto3_kwargs()`를 사용해 LocalStack/프로덕션 엔드포인트를 자동 선택합니다.

## 오류 처리

```python
def _put_item(self, item):
    try:
        if not self.table:
            logger.warning("DynamoDB table not available")
            return False
        self.table.put_item(Item=item)
        return True
    except Exception as e:
        logger.error("Error writing to DynamoDB: %s", e)
        return False
```

저장 실패는 치명적이지 않습니다 (알림은 이미 발송됨). 로그만 남기고 계속 진행합니다.

## Related Notes

- [[Config 모듈]]
- [[Discord Webhook Handler]]
- [[데이터 흐름 (Data Flow)]]
