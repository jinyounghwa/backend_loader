---
module: responders
path: 03-Responders
keywords: discord, webhook, embed, slash-command
---

# DiscordResponder — Discord 알림

#module-responders #api-discord

## 목적

Discord Webhook을 통해 Rich Embed 형식으로 보안 알림을 전송합니다.

## 주요 파일

`lambda/guardian/responders/discord.py`

## 심각도별 색상 코드

```python
SEVERITY_COLORS = {
    "CRITICAL": 16711680,  # #FF0000 빨강
    "HIGH":     16744192,  # #FF8000 주황
    "MEDIUM":   16776960,  # #FFFF00 노랑
    "LOW":       5814783,  # #58A9FF 파랑
    "INFO":        65280,  # #00FF00 초록
}
```

## Embed 구조

```python
embed = {
    "color": SEVERITY_COLORS[severity],
    "title": f"{icon} {title}",
    "fields": [
        {"name": "항목", "value": "값", "inline": True},
        ...
    ],
    "footer": {"text": "AWS Guardian • {timestamp}"}
}
```

## Webhook 전송

```python
requests.post(
    self.webhook_url,
    json={"embeds": [embed]},
    timeout=10,
    verify=True  # SSL 검증 활성화
)
# 성공: 200 또는 204
```

## Discord Slash Command (별도 Lambda)

Discord 명령어는 `lambda/discord_webhook/handler.py`에서 처리합니다.
`DiscordResponder`는 **알림 전송 전용**이고, 명령어 처리는 별도 Lambda입니다.

```
알림 흐름:
  Guardian Lambda → DiscordResponder → Webhook → Discord 채널

명령어 흐름:
  Discord 사용자 → Slash Command → Discord Webhook Lambda → 응답
```

## Related Notes

- [[Responders 개요]]
- [[Discord Webhook Handler]]
- [[TelegramResponder]]
