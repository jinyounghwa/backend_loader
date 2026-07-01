---
module: responders
path: 03-Responders
keywords: practice, quiz, responders, telegram, discord
---

# 연습문제 — Responders 모듈

#module-responders

## 문제 1 (개념) Telegram vs Discord 알림 방식 차이

TelegramResponder와 DiscordResponder의 메시지 형식 차이를 설명하세요.

> [!answer]- 정답 보기
> **TelegramResponder**: HTML 텍스트 포맷 사용. `<b>`, `<i>` 태그로 서식. `parse_mode="HTML"`로 전송. 단순하지만 XSS 취약점 주의 필요.
>
> **DiscordResponder**: Rich Embed JSON 사용. `color`, `title`, `fields`, `footer` 구조. 시각적으로 풍부한 카드 형태 알림. HTML 인젝션 위험 없음.

---

## 문제 2 (분석) SSL verify=True 의미

`requests.post(..., verify=True)`에서 `verify=True`를 제거하면 어떤 보안 위험이 생기나요?

> [!answer]- 정답 보기
> SSL 인증서 검증을 비활성화하면 중간자 공격(MITM)에 취약해집니다.
> 공격자가 네트워크 중간에서 Telegram/Discord API 트래픽을 가로채고 위조된 응답을 보낼 수 있습니다.
> AWS 알림 내용(보안 이벤트, 인스턴스 ID 등)이 노출될 위험이 있습니다.
> `verify=True`는 기본값이지만 명시적으로 작성해 의도를 명확히 합니다.

---

## 문제 3 (응용) 새 알림 채널 추가

Slack 알림 채널을 추가하려면 어떤 파일들을 수정/생성해야 하나요?

> [!answer]- 정답 보기
> 1. `lambda/guardian/responders/slack.py` 생성 (`SlackResponder` 클래스)
> 2. `responders/alert_formatter.py`의 `AlertMessage` 활용
> 3. `lambda/guardian/config.py`에 `get_slack_config()` 추가
> 4. `lambda/guardian/handler.py`의 `_LazyOrchestrator._build()`에 `SlackResponder` 초기화 추가
> 5. `GuardianOrchestrator`에 `slack_responder` 파라미터 추가
> 6. 환경변수 `SLACK_WEBHOOK_URL` 추가
> 7. `tests/test_slack.py` 작성

---

## 문제 4 (보안) HTML 인젝션 시나리오

공격자가 EC2 인스턴스 이름을 `<b>hacked</b><script>alert(1)</script>`로 설정했습니다.
`esc()` 함수 없이 Telegram 메시지에 포함하면 어떻게 되나요? `esc()` 처리 후에는?

> [!answer]- 정답 보기
> **esc() 없을 때**: Telegram HTML 파서가 `<b>hacked</b>`를 볼드체로 렌더링합니다. `<script>`는 Telegram에서 실행되지 않지만(봇 API 제한), HTML 구조가 깨져 메시지 포맷이 망가집니다.
>
> **esc() 처리 후**: `&lt;b&gt;hacked&lt;/b&gt;&lt;script&gt;...`로 변환되어 태그가 일반 텍스트로 표시됩니다. 안전하게 공격자의 의도된 이름이 그대로 표시됩니다.

---

## 문제 5 (응용) 타임아웃 10초 설계

Lambda에서 외부 API 호출(Telegram, Discord)에 `timeout=10`초를 설정한 이유를 설명하세요. 너무 크거나 작으면 어떤 문제가?

> [!answer]- 정답 보기
> **이유**: Lambda 함수 최대 실행 시간은 15분이지만 비용과 응답성을 위해 짧게 유지합니다. 외부 API가 응답 없이 멈추면 Lambda가 타임아웃까지 기다려 불필요한 비용이 발생합니다.
>
> **너무 작음 (1초)**: 느린 네트워크 환경에서 정상 응답도 실패로 처리됩니다.
>
> **너무 큼 (60초)**: 외부 서비스 장애 시 Lambda가 오래 실행되어 동시성 한도를 소진하고 비용이 증가합니다.
>
> 10초는 Telegram/Discord API 정상 응답 시간(보통 1-3초)의 3-10배로 적절한 여유를 줍니다.

---

## 문제 6 (개념) AlertMessage와 CheckResult 분리 이유

왜 `CheckResult` → `AlertMessage` 변환 단계가 있을까요? 직접 `CheckResult`를 알림에 쓰면 안 되나요?

> [!answer]- 정답 보기
> **관심사 분리**: `CheckResult`는 체커가 "무엇을 발견했는가"를 표현합니다. `AlertMessage`는 "어떻게 알릴 것인가"를 표현합니다.
>
> **포맷 독립성**: Telegram, Discord, Slack 등 각 채널마다 다른 포맷이 필요합니다. `AlertMessage`는 채널 중립적 중간 형식으로, 각 Responder가 채널별로 렌더링합니다.
>
> **테스트 용이성**: `AlertMessage` → Telegram HTML 변환만 독립적으로 테스트 가능합니다.

---

## 문제 7 (설계) 자동 대응 실패 시 처리

`AutoRemediationResponder`가 EC2 인스턴스 중지에 실패하면 어떻게 해야 할까요?

> [!answer]- 정답 보기
> 1. 실패 로그 기록 (`logger.error(...)`)
> 2. DynamoDB에 "자동 대응 실패" 이벤트 저장 (감사 추적)
> 3. Telegram/Discord로 "자동 대응 실패, 수동 조치 필요" 알림 발송
> 4. `suggested_action`에 수동 대응 방법 안내
> 5. 재시도 정책 (1-2회 재시도 후 포기)
>
> 자동 대응 실패가 알림 실패보다 훨씬 위험하므로 별도 에러 경로로 처리해야 합니다.

---

## 문제 8 (응용) Discord embed 색상 직접 확인

`SEVERITY_COLORS["CRITICAL"] = 16711680`을 16진수로 변환하면 무슨 색인가요? Python으로 어떻게 확인하나요?

> [!answer]- 정답 보기
> ```python
> hex(16711680)  # '0xff0000'
> ```
> `0xFF0000`은 RGB에서 **빨간색**입니다. CRITICAL 이벤트에 빨간 알림 카드가 표시됩니다.
>
> 확인 방법: `hex(16744192)` → `0xff8000` → 주황 (HIGH)

## Related Concepts

- [[Responders 개요]]
- [[TelegramResponder]]
- [[DiscordResponder]]
- [[Checkers 개요]]
