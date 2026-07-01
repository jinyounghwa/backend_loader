---
module: entry-point
path: 04-Storage-Config
keywords: lambda-handler, lazy-init, orchestrator, cold-start
---

# Guardian Handler — Lambda 진입점

#arch-serverless #pattern-lazy-init #pattern-double-checked-locking

## 목적

AWS Lambda의 진입점. `_LazyOrchestrator`로 cold start를 최적화하고
모든 체커/응답자의 생명주기를 관리합니다.

## 주요 파일

`lambda/guardian/handler.py`

## 핵심 구조

```python
# 모듈 로드 시 단 한 번만 실행 (Lambda 워커 재사용)
_lazy = _LazyOrchestrator()

def lambda_handler(event, context):
    return _lazy.orchestrator.run_all_checks(event)
```

## _LazyOrchestrator 설계

```
첫 호출:
  lambda_handler() 호출
      │
      ▼
  _lazy.orchestrator (property)
      │
      ├── self._orchestrator is None → True
      │
      ▼
  with self._lock:               ← 스레드 안전 보장
      │
      ├── self._orchestrator is None → True (double-check)
      │
      ▼
  self._build()                  ← 실제 초기화
      │
      ▼
  CostChecker, EC2Checker, S3Checker, ...
  TelegramResponder, DiscordResponder, ...
  DynamoDBStorage 생성

이후 호출:
  lambda_handler()
      │
      ▼
  _lazy.orchestrator
      │
      ├── self._orchestrator is not None → 캐시된 객체 반환
```

## Lambda 재사용 메커니즘

> [!important] Lambda Execution Context 재사용
> Lambda는 동일 함수를 짧은 시간 내에 다시 호출할 때 동일한 프로세스(워커)를 재사용합니다.
> `_lazy`는 모듈 레벨에서 생성되므로, 워커 재사용 시 이미 초기화된 상태입니다.
> → cold start 시에만 `_build()` 실행, 이후 호출은 초기화 비용 0

## 에러 처리 설계

```python
try:
    return _lazy.orchestrator.run_all_checks(event)
except Exception as e:
    correlation_id = str(uuid.uuid4())   # 추적용 고유 ID
    logger.exception("Fatal error [correlation_id=%s]: %s", correlation_id, e)
    return {
        "statusCode": 500,
        "body": json.dumps({
            "error": "Internal server error",
            "correlation_id": correlation_id,
        })
    }
```

> [!tip] Correlation ID 패턴
> 분산 시스템에서 오류를 추적하기 위해 각 오류에 고유 ID를 부여합니다.
> CloudWatch 로그에서 `correlation_id`로 검색하면 해당 오류의 전체 스택 트레이스를 찾을 수 있습니다.

## 로컬 실행

```python
if __name__ == "__main__":
    test_event = {"time": "2024-01-01T00:00:00Z", "source": "aws.events"}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
```

## Related Notes

- [[시스템 아키텍처]]
- [[요청 흐름 (Request Flow)]]
- [[Config 모듈]]
- [[Checkers 개요]]
