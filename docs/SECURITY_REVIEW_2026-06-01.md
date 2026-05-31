# 보안 검토 및 리팩토링 보고서

> **검토 일자:** 2026-06-01
> **대상:** AWS Guardian 전체 코드베이스 (529개 소스 파일)
> **결과:** 실질적 취약점 1건 + 로직 결함 1건 수정, 리팩토링 2건 / 전체 테스트 2,356건 통과

---

## 1. 개요

AWS Guardian 프로젝트 전체(`lambda/`, `scripts/`, `apps/`, `frontend/`)를 대상으로 보안
취약점 점검 및 코드 품질 개선을 수행했다. 위험 패턴 정적 스캔 → 핵심 공격 표면 수동 검토 →
발견 사항 수정 → 회귀 테스트 추가 순으로 진행했다.

**결론: 코드베이스는 전반적으로 매우 견고하다.** 시크릿 관리, 입력 검증, 서명 검증, 권한
검증, 프롬프트 인젝션 방어, CVE 인식 의존성 관리가 잘 갖춰져 있었다. 발견된 실질적 문제는
Telegram 알림의 HTML 인젝션 1건이었다.

---

## 2. 점검 결과 (이상 없음)

| 점검 항목 | 결과 |
|---|---|
| `eval` / `exec` / `os.system` / `shell=True` | ✅ 없음 |
| `pickle` / `yaml.load` 등 안전하지 않은 역직렬화 | ✅ 없음 |
| 하드코딩된 비밀정보 (`.env`는 gitignore, test 플레이스홀더만 존재) | ✅ 없음 |
| 약한 해시(md5/sha1), TLS 검증 비활성화(`verify=False`) | ✅ 없음 |
| SQL/NoSQL 인젝션 (DynamoDB `Key`/`Attr` 파라미터화 표현식 사용) | ✅ 안전 |
| 시크릿 관리 (런타임 SSM 조회 + IAM 역할 폴백, env에 시크릿 미저장) | ✅ 우수 |
| Discord 웹훅 Ed25519 서명 검증 (fail-closed) | ✅ 양호 |
| destructive API 라우트 권한 검증 (`admin`/`owner` 역할 강제) | ✅ 양호 |
| LLM 분석 라우트 프롬프트 인젝션 방어 (키 allowlist + 값 truncate + 인증) | ✅ 양호 |
| 프론트엔드 XSS (`dangerouslySetInnerHTML` / `innerHTML` / `eval`) | ✅ 없음 |
| AWS 액션 실행기 입력 검증 (instance-id / bucket / region 정규식) | ✅ 양호 |

---

## 3. 발견 및 수정 사항

### 3.1 🔴 Telegram HTML 인젝션 (실질적 취약점)

**위치:** `lambda/guardian/responders/telegram.py`, `lambda/guardian/responders/alert_formatter.py`

**문제:**
Telegram 알림을 `parse_mode="HTML"`로 전송하면서, AWS 리소스에서 유래한 신뢰 불가 데이터를
이스케이프 없이 `<b>` / `<code>` 구조 태그 사이에 직접 삽입했다. 해당 데이터에는 다음이 포함된다.

- IAM username, CloudTrail `source_ip`, `event_name`
- GuardDuty finding `type` / `resource_id`
- S3 버킷명, `public_reasons`
- EC2 instance-id / region, 계정명(account name)
- 자동 대응 알림의 `resource_id` / `region` / `rule_id`

**영향:**
- 공격자가 제어 가능한 리소스 이름/태그(예: 조작된 S3 버킷명, IAM 엔티티명)에 HTML을 삽입해
  보안팀이 받는 알림 내용을 **위조(spoofing)** 할 수 있다.
- `<` 또는 `&` 문자가 포함되면 Telegram API의 HTML 파싱이 실패해 메시지 전송이 거부되고,
  결과적으로 **보안 알림 자체가 누락(silent drop)** 될 수 있다.

**수정:**
- `alert_formatter.py`에 공용 `esc()` 헬퍼(`html.escape(value, quote=False)`)를 추가.
- 데이터 출처 시점(각 빌더 / 렌더러의 보간 지점)에서 **신뢰 불가 값만** 이스케이프하고,
  구조 태그(`<b>`, `<code>`)는 그대로 유지하는 방식으로 적용.
- `alert_formatter.py`(cost/ec2/s3/generic 빌더, 계정 정보)와 `telegram.py`
  (cloudtrail/iam/guardduty 렌더러, 자동 대응 알림, 일일 요약)의 모든 삽입 지점에 적용.
- 이중 이스케이프를 방지하기 위해 "출처에서 한 번만 이스케이프" 원칙을 적용.

**회귀 테스트:** `tests/test_telegram.py`에 3건 추가
- `test_s3_bucket_name_is_escaped`
- `test_cloudtrail_fields_are_escaped`
- `test_auto_response_resource_id_is_escaped`

---

### 3.2 🟡 CloudTrail 빈도 탐지 로직 결함 (버그)

**위치:** `lambda/guardian/pipelines/cloudtrail_pipeline.py`

**문제:**
이벤트 히스토리 보존 윈도우(1시간)를 **이벤트 자체의 `eventTime`** 기준으로 필터링했다.
이로 인해 `eventTime`이 1시간보다 오래된 이벤트(재생/지연 처리되거나, 공격자가 백데이트한
이벤트)는 빈도 분석 이전에 모두 폐기되어, **버스트 빈도 탐지가 동작하지 않았다.**
(시간 의존 테스트 `test_pipeline_anomaly_scoring` 실패의 근본 원인)

**영향:**
- 짧은 시간에 다수의 의심스러운 API 호출이 발생해도, 해당 이벤트들의 `eventTime`이 윈도우를
  벗어나면 빈도 이상 점수가 0으로 계산되어 **탐지를 우회**할 수 있다.

**수정:**
- 보존 기준을 이벤트의 `eventTime`이 아닌 **수집 시각(`_ingested_at`, 관측 시점)** 으로 변경.
- 빈도 탐지는 의도대로 `eventTime` 기준 분 단위 버킷팅을 유지(활동 발생 속도 측정).
- 결과적으로 더 정확한 탐지 동작이며, 시간 의존 취약 테스트도 해소됨.

---

### 3.3 🔧 리팩토링

**Discord 핸들러 예외 처리 정리** — `lambda/discord_webhook/handler.py`
- 중복된 예외 튜플 `except (BadSignatureError, ValueError, Exception)`을 `except Exception`으로
  단순화하고, fail-closed(어떤 오류든 미신뢰로 간주) 의도를 주석으로 명확화.

**미사용 import 제거** — `lambda/guardian/pipelines/cloudtrail_pipeline.py`
- `typing.Optional`, `json` 미사용 import 제거 (flake8 F401 해소).

---

## 4. 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `lambda/guardian/responders/alert_formatter.py` | `esc()` 헬퍼 추가 + 빌더 이스케이프 |
| `lambda/guardian/responders/telegram.py` | 렌더러/알림/요약 이스케이프 |
| `lambda/discord_webhook/handler.py` | 예외 처리 정리 (fail-closed 유지) |
| `lambda/guardian/pipelines/cloudtrail_pipeline.py` | 수집 시각 기준 보존 + import 정리 |
| `tests/test_telegram.py` | HTML 이스케이프 회귀 테스트 3건 추가 |

---

## 5. 검증

- **flake8:** 변경 파일 전체 통과 (경고 0)
- **테스트:** `2,356 passed, 61 skipped` (이전 실패 1건 → 해소, 신규 3건 추가)

---

## 6. 권고 사항 (후속, 선택)

- `telegram_bot.py`의 명령 결과 메시지도 동일한 `esc()` 적용 검토 (현재는 검증된 내부 값
  위주이나 방어적 적용 권장).
- 코드 전반의 `datetime.utcnow()` (deprecated) → `datetime.now(timezone.utc)` 마이그레이션
  (다수 DeprecationWarning 발생 중, 기능 영향 없음).
