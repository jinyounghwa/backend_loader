---
module: responders
path: 03-Responders
keywords: telegram, discord, notification, auto-remediation, alert
---

# Responders 개요

#module-responders #api-telegram #api-discord

## 역할

Responders는 체커 결과를 받아 알림을 발송하거나 자동 대응 조치를 실행합니다.

## Responder 목록

| Responder | 파일 | 역할 |
|-----------|------|------|
| `TelegramResponder` | `responders/telegram.py` | Telegram Bot으로 알림 발송 |
| `DiscordResponder` | `responders/discord.py` | Discord Webhook으로 Embed 발송 |
| `AutoRemediationResponder` | `responders/remediation_service.py` | EC2 중지, S3 차단 자동 실행 |
| `AWSActionExecutor` | `responders/aws_action_executor.py` | 실제 AWS API 호출 실행자 |

## AlertMessage 공통 포맷

```python
# responders/alert_formatter.py
@dataclass
class AlertMessage:
    check_name: str          # "Cost" | "EC2" | "S3" | ...
    severity: str            # "INFO" | "HIGH" | "CRITICAL"
    title: str
    items: list              # [{"label": "...", "details": [...]}]
    summary_line: str        # 한 줄 요약
    suggested_action: str    # 권장 조치
    account_info: str        # 멀티 계정 정보 (선택)
```

## 알림 포맷 비교

### Telegram (HTML)
```
🔴 💰 비용 임계값 초과
🏢 계정: 123456789012
━━━━━━━━━━━━━━━━━━━
• 오늘 비용: $15.30
  └ 전일 대비: +$5.30

━━━━━━━━━━━━━━━━━━━
⚡ 임계값($10.00) 초과
💡 AWS 콘솔에서 비용 원인을 확인하세요
```

### Discord (Embed)
```json
{
  "color": 16711680,  // CRITICAL: 빨강
  "title": "💰 비용 임계값 초과",
  "fields": [
    {"name": "오늘 비용", "value": "$15.30", "inline": true},
    {"name": "임계값", "value": "$10.00", "inline": true}
  ],
  "footer": {"text": "AWS Guardian • 2024-01-01 00:00:00"}
}
```

## 자동 대응 흐름

```
CheckResult (이상 감지)
    │
    ▼
AutoRemediationResponder.respond(result)
    │
    ├── EC2 이상 → AWSActionExecutor.stop_instance(instance_id)
    │                    │
    │                    ▼
    │               ec2.stop_instances(InstanceIds=[id])
    │
    └── S3 이상 → AWSActionExecutor.block_public_access(bucket)
                         │
                         ▼
                    s3.put_public_access_block(...)
```

## 설정 조건부 활성화

```python
# handler.py에서 설정값이 있을 때만 Responder 생성
telegram_responder = TelegramResponder() if telegram_config["bot_token"] else None
discord_responder = DiscordResponder() if discord_config["webhook_url"] else None
```

> [!tip] 왜 None 체크?
> 개발 환경에서는 Telegram/Discord 설정 없이 테스트합니다.
> None인 responder는 Orchestrator에서 스킵됩니다.

## 보안: HTML 인젝션 방지

```python
def esc(text: str) -> str:
    """Telegram HTML 메시지용 특수문자 이스케이프."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
```

> [!warning] Telegram HTML 모드
> `parse_mode="HTML"`로 메시지를 보낼 때 사용자 입력 데이터를 그대로 포함하면
> XSS와 유사한 HTML 인젝션이 발생할 수 있습니다. 반드시 `esc()` 함수로 처리합니다.

## Related Notes

- [[TelegramResponder]]
- [[DiscordResponder]]
- [[Guardian Handler]]
- [[요청 흐름 (Request Flow)]]
