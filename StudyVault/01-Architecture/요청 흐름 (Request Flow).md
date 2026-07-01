---
module: architecture
path: 01-Architecture
keywords: request-flow, lambda, eventbridge, orchestrator
---

# 요청 흐름 (Request Flow)

#arch-serverless #arch-event-driven #pattern-lazy-init

## EventBridge 트리거 흐름 (1시간 주기 감시)

```
1. EventBridge cron (매 1시간)
        │
        ▼
2. lambda_handler(event, context)
   [lambda/guardian/handler.py]
        │
        ▼
3. _lazy.orchestrator  ← _LazyOrchestrator (지연 초기화)
   - 첫 호출 시: _build() 실행
   - 이후 호출: 캐시된 orchestrator 반환
        │
        ▼
4. GuardianOrchestrator.run_all_checks(event)
   [lambda/guardian/orchestrator.py]
        │
        ├──▶ CostChecker.check()   → CheckResult
        ├──▶ EC2Checker.check()    → CheckResult
        └──▶ S3Checker.check()     → CheckResult
                │
                ▼
5. 결과 분석 (이상 감지 여부 확인)
        │
        ├── 이상 있음 →
        │     ├── TelegramResponder.send_alert()
        │     ├── DiscordResponder.send_embed()
        │     ├── AutoRemediationResponder.respond() (자동 대응)
        │     └── DynamoDBStorage.save_event()
        │
        └── 정상 → DynamoDBStorage.save_event() (INFO 기록)
                │
                ▼
6. lambda_handler 반환 {"statusCode": 200, ...}
```

## Discord Slash Command 흐름

```
1. 사용자가 Discord에서 /status 입력
        │
        ▼
2. Discord → HTTP POST → Discord Webhook Lambda
   [lambda/discord_webhook/handler.py]
        │
        ▼
3. verify_discord_request()  ← Ed25519 서명 검증
   실패 시 → 401 Unauthorized 반환
        │
        ▼
4. 명령어 라우팅
   /status  → 체커 실행 후 현재 상태 반환
   /stop    → AWSActionExecutor.stop_instance()
   /budget  → 비용 임계값 업데이트
   /history → DynamoDBStorage 이벤트 조회
        │
        ▼
5. create_response(content) 반환
   {"type": 4, "data": {"content": "...", "flags": 0}}
```

## Cold Start 최적화 상세

> [!tip] Lazy Initialization 패턴
> Lambda가 처음 시작될 때 (cold start) 모든 의존성을 로드하면 응답 지연이 발생합니다.
> `_LazyOrchestrator`는 첫 실제 호출 시에만 Orchestrator를 생성합니다.

```python
class _LazyOrchestrator:
    def __init__(self):
        self._orchestrator = None
        self._lock = threading.Lock()   # 스레드 안전성

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            with self._lock:
                if self._orchestrator is None:  # Double-checked locking
                    self._build()
        return self._orchestrator
```

> [!warning] Double-Checked Locking
> `if self._orchestrator is None`을 두 번 확인합니다.
> 첫 번째는 lock 없이 빠른 경로, 두 번째는 lock 내에서 안전한 경로입니다.
> 동시에 여러 스레드가 처음 호출할 때 중복 초기화를 방지합니다.

## CheckResult 데이터 흐름

```
체커 실행
    │
    ▼
CheckResult(severity, title, message, details, suggested_action)
    │
    ├── severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    ├── title: 사람이 읽을 수 있는 제목
    ├── message: 상세 설명
    ├── details: dict (체커별 추가 정보)
    └── suggested_action: 권장 조치사항
    │
    ▼
Responder → 포맷팅 → Telegram/Discord 전송
    │
    ▼
DynamoDB → 이벤트 저장 (감사 로그)
```

## 에러 처리 흐름

```
lambda_handler 호출
    │
    ├── 정상 → orchestrator.run_all_checks() 결과 반환
    │
    └── 예외 발생 →
          correlation_id = uuid4()
          logger.exception(...)
          return {
            "statusCode": 500,
            "body": {"error": "...", "correlation_id": "..."}
          }
```

## Related Notes

- [[시스템 아키텍처]]
- [[Guardian Handler]]
- [[Checkers 개요]]
- [[Responders 개요]]
