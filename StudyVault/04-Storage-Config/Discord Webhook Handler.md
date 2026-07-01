---
module: discord-webhook
path: 04-Storage-Config
keywords: discord, slash-command, ed25519, signature-verification
---

# Discord Webhook Handler — Slash Command Lambda

#module-responders #api-discord

## 목적

Discord Slash Command를 처리하는 별도 Lambda 함수입니다.
Guardian Lambda(감시)와 독립적으로 배포되어 사용자 요청에 즉시 응답합니다.

## 주요 파일

`lambda/discord_webhook/handler.py`

## 지원 명령어

| 명령어 | 동작 |
|--------|------|
| `/status` | EC2/S3/비용 현재 상태 즉시 조회 |
| `/stop {instance-id}` | EC2 인스턴스 수동 중지 |
| `/budget set {amount}` | 비용 임계값 변경 |
| `/history` | 최근 24시간 DynamoDB 이벤트 조회 |

## 보안: Ed25519 서명 검증

```python
def verify_discord_request(request_body, signature, timestamp) -> bool:
    from nacl.signing import VerifyKey

    public_key = os.getenv("DISCORD_PUBLIC_KEY", "")
    verify_key = VerifyKey(bytes.fromhex(public_key))
    message = (timestamp + request_body).encode("utf-8")
    verify_key.verify(message, bytes.fromhex(signature))   # 실패 시 예외
    return True
```

> [!important] Fail-Closed 보안 원칙
> 서명 검증 중 어떤 예외도 False 반환 (인증 실패로 처리)
> "안전하다고 증명되지 않으면 거부"
>
> ```python
> except Exception as e:
>     logger.warning("Discord signature verification failed: %s", e)
>     return False   # 예외 = 실패로 처리
> ```

## 입력 검증 (정규식)

```python
INSTANCE_ID_PATTERN = re.compile(r"^i-[0-9a-f]{8,17}$")
REGION_PATTERN = re.compile(
    r"^(us|eu|ap|sa|ca|me|af)-(east|west|south|north|central|southeast|northeast)-[0-9]$"
)
MIN_THRESHOLD = 0.01
MAX_THRESHOLD = 1000000.0
```

> [!warning] 입력 검증 필수
> Discord 명령어는 외부 사용자 입력입니다. 검증 없이 AWS API에 전달하면
> 임의 리소스 조작, 비용 폭탄, 보안 취약점이 발생할 수 있습니다.

## 응답 포맷

```python
def create_response(content: str, ephemeral: bool = False):
    return {
        "type": 4,          # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "content": content,
            "flags": 64 if ephemeral else 0   # 64 = 나에게만 보임
        }
    }
```

## Discord 상호작용 타입

| type | 의미 |
|------|------|
| 1 | PING (Discord 서버 검증) |
| 2 | APPLICATION_COMMAND (Slash Command) |

```python
if interaction.get("type") == 1:
    return {"type": 1}  # PONG 응답
```

## Related Notes

- [[Responders 개요]]
- [[DiscordResponder]]
- [[DynamoDB Storage]]
- [[시스템 아키텍처]]
