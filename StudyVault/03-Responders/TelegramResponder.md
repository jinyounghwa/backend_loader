---
module: responders
path: 03-Responders
keywords: telegram, bot-api, html, notification
---

# TelegramResponder — Telegram 알림

#module-responders #api-telegram

## 목적

Telegram Bot API를 통해 보안 이상 알림을 채팅으로 전송합니다.

## 주요 파일

`lambda/guardian/responders/telegram.py`

## 초기화

```python
TelegramResponder(
    bot_token="...",   # 없으면 환경변수 TELEGRAM_BOT_TOKEN
    chat_id="..."      # 없으면 환경변수 TELEGRAM_CHAT_ID
)
```

## API 엔드포인트

```
POST https://api.telegram.org/bot{token}/sendMessage
{
  "chat_id": "...",
  "text": "...",
  "parse_mode": "HTML"
}
```

## 메시지 렌더링

```python
def _render_alert(self, alert: AlertMessage) -> str:
    icon = check_emoji(alert.check_name)   # 💰/🖥️/📦
    sev_icon = severity_icon(alert.severity)  # 🔴/🟠/🟡
    parts = [f"{sev_icon} <b>{icon} {alert.title}</b>"]
    ...
    return "\n".join(parts)
```

## 심각도 아이콘

| 심각도 | 아이콘 |
|--------|--------|
| CRITICAL | 🔴 |
| HIGH | 🟠 |
| MEDIUM | 🟡 |
| LOW | 🔵 |
| INFO | ✅ |

## 보안 주의사항

> [!warning] HTML 인젝션 방지 필수
> AWS 리소스 이름, 사용자 이름 등 외부 데이터가 메시지에 포함될 때
> 반드시 `esc()` 함수로 HTML 특수문자를 이스케이프해야 합니다.
>
> ```python
> # 잘못된 예 (취약)
> parts.append(f"버킷: {bucket_name}")
>
> # 올바른 예
> parts.append(f"버킷: {esc(bucket_name)}")
> ```

## 타임아웃 설정

```python
requests.post(..., timeout=10)  # 10초 타임아웃
```

Lambda는 최대 실행 시간이 있으므로 외부 API 호출에 타임아웃이 필수입니다.

## Related Notes

- [[Responders 개요]]
- [[DiscordResponder]]
