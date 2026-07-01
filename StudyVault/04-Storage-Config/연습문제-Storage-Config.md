---
module: storage-config
path: 04-Storage-Config
keywords: practice, quiz, dynamodb, config, discord
---

# 연습문제 — Storage & Config 모듈

#module-storage #module-config

## 문제 1 (개념) Config 클래스 변수 캐싱

`Config._boto3_kwargs`가 인스턴스 변수가 아닌 클래스 변수인 이유를 Lambda 실행 모델 관점에서 설명하세요.

> [!answer]- 정답 보기
> Lambda 워커는 호출 간에 프로세스를 재사용합니다. 클래스 변수는 모듈 로드 시 한 번 생성되어 동일 워커의 모든 호출에서 공유됩니다.
>
> 인스턴스 변수라면 `Config()`를 호출할 때마다 새 인스턴스가 생성되어 캐시가 초기화됩니다. 클래스 변수는 워커 수명 내내 유지됩니다.
>
> SSM API 호출은 네트워크 요청이므로 캐싱으로 수십 ms의 지연을 절감합니다.

---

## 문제 2 (분석) Decimal vs float

DynamoDB에서 `float` 대신 `Decimal`을 사용하는 이유와, `Decimal(str(15.30))`이 `Decimal(15.30)`보다 안전한 이유를 설명하세요.

> [!answer]- 정답 보기
> **DynamoDB 이유**: AWS SDK가 Python `float`의 부동소수점 표현을 DynamoDB Number 타입으로 정확히 변환하지 못합니다. `Decimal`만 허용합니다.
>
> **str() 경유 이유**:
> ```python
> Decimal(15.30)      # Decimal('15.2999999999999971578290...') ← 부정확
> Decimal(str(15.30)) # Decimal('15.3') ← 문자열 표현 사용으로 정확
> Decimal('15.30')    # Decimal('15.30') ← 가장 정확 (소수점 유지)
> ```
> Python의 `float(15.30)`은 이미 부정확한 이진 표현입니다. `str()`을 거치면 10진수 표현이 복원됩니다.

---

## 문제 3 (응용) 이벤트 조회 시나리오

Discord `/history` 명령어가 최근 24시간 이벤트를 조회합니다. DynamoDB에서 어떻게 구현하면 효율적일까요?

> [!answer]- 정답 보기
> **방법 1 (현재 구현)**: `timestamp` 정렬키로 Query + 시간 범위 필터
> ```python
> table.query(
>     FilterExpression=Attr("timestamp").gte(cutoff_iso)
>     Limit=50
> )
> ```
>
> **더 효율적인 방법**: GSI(Global Secondary Index)를 account_id를 파티션키로 생성하면 특정 계정의 이벤트를 빠르게 조회합니다.
>
> **TTL 활용**: 30일 후 자동 만료로 오래된 데이터를 수동 삭제할 필요가 없습니다.

---

## 문제 4 (보안) Ed25519 서명 검증 필요성

Discord Webhook Lambda에서 서명 검증을 생략하면 어떤 공격이 가능한가요?

> [!answer]- 정답 보기
> Lambda URL이 노출되면 누구나 가짜 Discord 요청을 보낼 수 있습니다:
>
> 1. `/stop i-1234567890abcdef0` → 운영 EC2 강제 중지
> 2. `/budget set 0.01` → 임계값 $0.01로 낮춰 알림 폭풍
> 3. DDoS 공격으로 Lambda 동시 실행 한도 소진 (비용 발생)
>
> Discord는 모든 요청에 Ed25519 서명을 추가합니다. 검증으로 Discord 서버에서 온 요청만 허용합니다.

---

## 문제 5 (응용) Config.reset_cache() 필요 시점

언제 `Config.reset_cache()`를 호출해야 하나요? 두 가지 시나리오를 설명하세요.

> [!answer]- 정답 보기
> **시나리오 1 (테스트)**: 테스트 함수마다 Config가 다른 환경변수를 사용해야 할 때. 이전 테스트의 캐시가 남아있으면 환경변수 변경이 반영되지 않습니다.
> ```python
> def setUp(self):
>     Config.reset_cache()
>     os.environ["AWS_ENV"] = "localstack"
> ```
>
> **시나리오 2 (운영)**: SSM 값을 업데이트한 후 Lambda를 재시작하지 않고 즉시 반영하고 싶을 때. 하지만 실제로는 Lambda를 재시작(새 배포)하는 것이 더 안전합니다.

---

## 문제 6 (개념) Ephemeral Discord 응답

`create_response(content, ephemeral=True)`를 쓰면 어떻게 다른가요? `/stop` 명령어에 ephemeral을 써야 하는 이유는?

> [!answer]- 정답 보기
> `ephemeral=True`는 Discord `flags: 64`를 설정합니다. 해당 메시지는 명령어를 실행한 사용자에게만 보이고, 채널의 다른 사람에게는 보이지 않습니다.
>
> `/stop {instance-id}` 응답에 ephemeral을 쓰는 이유:
> - 인스턴스 ID가 채널에 공개되면 공격자가 타겟 정보를 얻음
> - "인스턴스 i-xxxxx 중지 성공" 메시지가 채널에 남으면 내부 인프라 구조 노출
> - 보안 명령어 실행 결과는 실행자에게만 표시되는 것이 바람직

---

## 문제 7 (분석) DynamoDB Table이 None인 경우

`DynamoDBStorage.__init__`에서 `self.table = None`이 되는 경우와, 그때 `save_event()`의 동작을 설명하세요.

> [!answer]- 정답 보기
> `AWSClientProvider.get_resource("dynamodb").Table(table_name)` 호출 시 예외 발생 → `self.table = None`
>
> 원인: 테이블 미존재, 권한 부족, LocalStack 미실행 등
>
> `_put_item()` 동작:
> ```python
> if not self.table:
>     logger.warning("DynamoDB table not available")
>     return False   # 저장 실패, 예외 없음
> ```
>
> 저장 실패는 경고 로그만 남기고 조용히 실패합니다. 알림(Telegram/Discord)은 이미 발송되었으므로 저장 실패는 치명적이지 않습니다.

## Related Concepts

- [[Guardian Handler]]
- [[Config 모듈]]
- [[DynamoDB Storage]]
- [[Discord Webhook Handler]]
