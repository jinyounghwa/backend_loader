# AWS Guardian SaaS — 마스터 기획서

> AWS 계정 보안/비용 감시 SaaS.
> 사용자는 가입 → AWS 연동 → Telegram 설정만으로 자동 감시 시작.
> 3-AI 오케스트레이션(Claude Code + GLM + Gemini) + LocalStack으로 개발.

**슬로건: "당신의 AWS, 우리가 지켜드립니다"**

---

## 1. 프로젝트 전체 구조

```
aws-guardian-saas/
├── CLAUDE.md                        # 이 파일
├── SKILL.md                         # 기술 구현 명세 (핵심 코드)
├── SKILL_SECURITY.md                # 보안 구현 명세
├── SKILL_ORCHESTRA.md               # 3-AI 개발환경 + LocalStack
│
├── .ai-orchestra/                   # AI 오케스트레이션
│   ├── orchestra.sh                 # tmux 자동 시작
│   ├── glm-proxy.py                 # GLM 구독 API 프록시
│   ├── prompts/
│   │   ├── claude.md                # Claude Code 역할 정의
│   │   ├── glm.md                   # GLM 역할 정의
│   │   └── gemini.md                # Gemini 역할 정의
│   └── shared/
│       ├── tasks/                   # Claude → GLM 태스크 지시
│       ├── review/                  # GLM → Claude 리뷰 요청
│       └── docs/                    # Claude → Gemini 문서 지시
│
├── apps/
│   ├── web/                         # Next.js 14 (App Router)
│   │   └── app/
│   │       ├── (auth)/              # 가입/로그인
│   │       ├── onboarding/          # 5단계 온보딩 위저드
│   │       └── dashboard/           # 메인 대시보드
│   └── api/                         # NestJS 백엔드
│       └── src/
│           ├── auth/
│           ├── users/
│           ├── connections/          # AWS 연동 관리
│           ├── settings/             # 감시 설정
│           └── events/               # 이벤트 로그
│
├── lambda/
│   ├── dispatcher/                  # 사용자 목록 → 병렬 실행
│   └── guardian/                    # 감시 엔진 (멀티테넌트)
│       ├── handler.py
│       ├── checkers/
│       │   ├── cost.py
│       │   ├── ec2.py
│       │   └── s3.py
│       ├── responders/
│       │   ├── telegram.py
│       │   └── discord.py
│       ├── storage/
│       │   └── supabase_logger.py
│       ├── utils/
│       │   ├── aws_client.py        # LocalStack 자동 전환
│       │   ├── credentials.py       # Role/Key 자격증명
│       │   └── security.py          # 입력 검증
│       └── discord_webhook/
│           └── handler.py
│
├── localstack/
│   ├── docker-compose.yml
│   ├── init/01-setup.sh
│   ├── mocks/cost-explorer-mock.ts  # CE API 목 서버
│   └── .env.localstack
│
├── supabase/
│   └── migrations/
│       └── 001_init.sql
│
├── terraform/
│   ├── main.tf
│   ├── lambda.tf
│   ├── eventbridge.tf
│   ├── dynamodb.tf
│   └── iam.tf
│
└── scripts/
    ├── test-localstack.sh
    └── deploy.sh
```

---

## 2. 핵심 시나리오

```
[매 1시간 — EventBridge 트리거]

Dispatcher Lambda
    → Supabase에서 활성 사용자 전체 조회
    → 사용자별 Guardian Lambda 병렬 비동기 호출

Guardian Lambda (사용자별 독립 실행)
    → AWS 자격증명 획득 (Role ARN 또는 Access Key 복호화)
    ↓
    비용 체크  → 임계값 초과? → Telegram 알림 + Supabase 로그
    EC2 체크   → 이상 감지?  → 자동 Stop + Telegram 알림
    S3 체크    → 퍼블릭?     → 자동 차단 + Telegram 알림
    ↓
    Discord Webhook 대시보드 갱신

[사용자 Discord 명령어]
/status  → Lambda 호출 → 현재 상태 Embed 반환
/stop    → EC2 중지 실행
/budget  → 비용 임계값 변경

[사용자 온보딩]
가입 → Telegram 연동 (딥링크) → AWS 연동 → 감시 설정 → 테스트 실행
```

---

## 3. 기술 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| 프론트 | Next.js 14 App Router + Tailwind | Vercel 배포 |
| 백엔드 | NestJS + Supabase | Railway 배포 |
| DB/Auth | Supabase (PostgreSQL + RLS) | 멀티테넌트 격리 |
| 감시 엔진 | AWS Lambda Python 3.12 | 서버리스 |
| 스케줄러 | AWS EventBridge | 1시간 주기 |
| 암호화 | AWS KMS + AES-256 | 자격증명 이중 암호화 |
| 알림 | Telegram Bot API | 필수 |
| 대시보드 | Discord Webhook + Slash Command | 선택 |
| IaC | Terraform | 전체 인프라 |
| 개발 환경 | LocalStack + Docker | AWS 에뮬레이션 |

---

## 4. 감시 항목 (v1 스코프)

| 대상 | 감시 내용 | 자동 대응 |
|------|-----------|-----------|
| 비용 | 일일 비용 임계값 초과 | 알림만 |
| EC2 | 비인가 리전 인스턴스 실행 | 자동 Stop |
| EC2 | Security Group 위험 포트 전체 오픈 | 알림 + 수동 |
| S3 | 퍼블릭 버킷 감지 | 자동 차단 |
| S3 | 신규 버킷 생성 감지 | 알림만 |

---

## 5. 보안 대응 현황

| 위협 | 상태 | 구현 위치 |
|------|------|-----------|
| SSRF | ✅ 완료 | ssrf-guard.ts, ARN 정규식 검증 |
| IDOR | ✅ 완료 | OwnershipGuard + Supabase RLS |
| Injection | ✅ 완료 | ValidationPipe whitelist |
| Confused Deputy | ✅ 완료 | ExternalId 서버 생성 강제 |
| 자격증명 탈취 | ✅ 완료 | KMS 암호화 + 응답 마스킹 |
| Rate Limiting | ✅ 완료 | ThrottlerModule 엔드포인트별 |
| 공급망 공격 | ✅ 완료 | GitHub Actions npm audit / safety |
| 감사 로그 위조 | ✅ 완료 | INSERT ONLY 테이블 |
| OAuth PKCE | 🔴 필요 | PKCE 플로우 + state 검증 |
| Timing Attack | 🔴 필요 | timingSafeEqual 적용 |
| 테넌트 격리 실패 | 🔴 필요 | 서비스 레이어 user_id 교차 검증 |
| 시크릿 노출 | 🔴 필요 | gitleaks CI 설정 |
| JWT Rotation | 🟡 권장 | Refresh Token 1회용 교체 |
| Webhook 멱등성 | 🟡 권장 | 이벤트 중복 실행 방지 |

---

## 6. 멀티테넌트 아키텍처

```
Supabase DB (users, aws_connections, watch_settings, guardian_events, audit_logs)
    ↑ RLS 전 테이블 적용
    ↑ OwnershipGuard (NestJS)

AWS Lambda Dispatcher
    → 활성 aws_connections 조회
    → Guardian Lambda 병렬 invoke (InvocationType=Event)

Guardian Lambda
    → get_boto3_session(method: 'role' | 'key')
        role: STS.AssumeRole(RoleArn, ExternalId)  ← Cross-Account
        key:  KMS.Decrypt(access_key_enc)           ← 복호화 후 세션
    → checkers 실행
    → supabase_logger.log()
    → telegram.send()
```

---

## 7. AWS 연동 방식

**A. Cross-Account IAM Role (권장)**
- 사용자 AWS 계정에 IAM Role 생성 (가이드 제공)
- ExternalId: 서버에서 UUID 생성, 변경 불가
- Trust Policy: 서비스 계정 ID + ExternalId 조건

**B. Access Key / Secret Key**
- KMS + AES-256-CBC 이중 암호화 저장
- 응답 시 마스킹 인터셉터로 자동 제거
- 최소 권한 IAM Policy 가이드 함께 제공

---

## 8. 온보딩 5단계

```
Step 1  이메일 가입 / Google OAuth
Step 2  Telegram 연동 (딥링크 t.me/BotName?start=CODE → Supabase Realtime 자동 감지)
Step 3  AWS 연동 방식 선택 (Role ARN 또는 Access Key)
Step 4  감시 설정 (항목 선택 / 임계값 / 리전 / 자동 대응 ON·OFF)
Step 5  즉시 테스트 실행 → Telegram 수신 확인 → 완료
```

---

## 9. 수익 모델 (미확정 — v1은 전체 무료로 출시)

| 플랜 | 가격 | 주요 제한 |
|------|------|-----------|
| Free | 무료 | 1계정, 비용 감시만, 알림 3회/일 |
| Pro | $9/월 | 3계정, 전체 감시, 무제한, 자동 대응 |
| Team | $29/월 | 10계정, Discord 팀 알림, 감사 로그 |

---

## 10. 3-AI 개발 환경

| AI | 역할 | 실행 방식 |
|----|------|-----------|
| Claude Code | 사령관 (태스크 분해·리뷰·보안 검토) | `claude` 구독 CLI |
| GLM 5.1 | 구현 (Lambda·NestJS·테스트) | `aider` + 구독 API 프록시 |
| Gemini | 문서화 (SKILL·README·API docs) | `gemini` 구독 CLI |

**tmux 레이아웃**
```
┌─────────────────────────────────────────┐
│  pane 0: Claude Code (사령관)            │
├────────────────────┬────────────────────┤
│  pane 1: GLM 5.1   │  pane 2: Gemini    │
├────────────────────┴────────────────────┤
│  pane 3: LocalStack + 로그               │
└─────────────────────────────────────────┘
```

**AI 간 통신 (파일 기반 비동기)**
```
Claude → shared/tasks/TASK_NNN.md  → GLM 구현
GLM    → shared/review/REVIEW_NNN.md → Claude 리뷰
Claude → shared/docs/DOC_NNN.md    → Gemini 문서화
```

---

## 11. LocalStack 에뮬레이션

| AWS 서비스 | 용도 | 비고 |
|-----------|------|------|
| Lambda | Guardian / Dispatcher | Docker executor |
| DynamoDB | guardian-events 테이블 | TTL 30일 |
| S3 | 테스트 버킷 (정상/퍼블릭) | 감지 시나리오 |
| SSM | 파라미터 스토어 | 임계값 / 토큰 |
| KMS | 자격증명 암호화 키 | alias/guardian-key |
| STS | AssumeRole 시뮬레이션 | ExternalId 테스트 |
| EventBridge | 5분 주기 (개발용 단축) | 실제는 1시간 |
| CE (Cost Explorer) | **LocalStack 미지원** | Mock 서버 port 4580 |

---

## 12. GLM 구독 API 연결 (aider)

GLM API가 OpenAI 호환 엔드포인트이므로 aider의
`--openai-api-base` 로 직접 연결한다.

**인증 방식에 따른 패턴**

| 패턴 | 조건 | 방법 |
|------|------|------|
| A | `Authorization: Bearer KEY` 동작 | aider 옵션 2개만 추가 |
| B | 커스텀 헤더 필요 | `glm-proxy.py` 로컬 프록시 (port 8765) |
| C | JWT 발급 + 만료 갱신 | 프록시에 TokenManager 추가 |

```bash
# 패턴 A (가장 단순)
aider \
  --model openai/glm-4-plus \
  --openai-api-base $GLM_API_BASE \
  --openai-api-key  $GLM_API_KEY \
  ...

# 패턴 B/C (프록시 경유)
python .ai-orchestra/glm-proxy.py &
aider \
  --model openai/glm-4-plus \
  --openai-api-base http://127.0.0.1:8765 \
  --openai-api-key  dummy \
  ...
```

---

## 13. 구현 로드맵 (v1 MVP)

### Day 1 — 개발 환경
- [ ] 저장소 초기화, .gitignore, 디렉토리 구조 생성
- [ ] orchestra.sh 실행 → tmux 4-pane 확인
- [ ] LocalStack docker-compose 기동 + 01-setup.sh 실행
- [ ] GLM 프록시 연결 테스트 (curl 확인)
- [ ] Cost Explorer Mock 서버 기동 확인

### Day 2-3 — Lambda 감시 엔진
- [ ] `utils/aws_client.py` LocalStack 자동 전환
- [ ] `utils/credentials.py` Role / Key 세션 팩토리
- [ ] `checkers/cost.py` + LocalStack CE Mock 연동
- [ ] `checkers/ec2.py` + LocalStack EC2 감지
- [ ] `checkers/s3.py` + LocalStack 퍼블릭 버킷 감지
- [ ] `responders/telegram.py`
- [ ] `storage/supabase_logger.py`
- [ ] `handler.py` 통합 + test-localstack.sh 전체 통과

### Day 4-5 — Dispatcher + 멀티테넌트
- [ ] `lambda/dispatcher/handler.py`
- [ ] Supabase 스키마 마이그레이션 (001_init.sql)
- [ ] RLS 정책 전 테이블 적용
- [ ] Dispatcher → Guardian 병렬 invoke 테스트

### Day 6-7 — NestJS API
- [ ] Auth 모듈 (Supabase JWT 검증)
- [ ] Connections 모듈 (Role ARN / Access Key 등록)
- [ ] OwnershipGuard + ValidationPipe
- [ ] SSRF Guard (assertValidRoleArn / assertSafeWebhook)
- [ ] KMS 암호화 서비스
- [ ] Settings / Events 모듈

### Day 8-9 — Telegram Bot + 온보딩
- [ ] /connect 딥링크 코드 발급
- [ ] Supabase Realtime 연동 (자동 감지)
- [ ] /status 명령어
- [ ] Next.js 온보딩 5단계 위저드

### Day 10 — Discord + 보안 마무리
- [ ] Discord Slash Command Lambda
- [ ] ed25519 서명 검증
- [ ] gitleaks CI 설정
- [ ] timingSafeEqual 적용
- [ ] OAuth PKCE 플로우
- [ ] 전체 E2E 테스트

### Day 11+ — Terraform + 배포
- [ ] Terraform 전체 리소스 정의
- [ ] Vercel (Next.js) + Railway (NestJS) 배포
- [ ] 실제 AWS 연동 스모크 테스트

---

## 14. 환경변수 목록

```bash
# ── NestJS API ──
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ENCRYPTION_KEY=          # openssl rand -hex 32
KMS_KEY_ID=              # alias/guardian-key
TELEGRAM_BOT_TOKEN=
NEXT_PUBLIC_TELEGRAM_BOT_NAME=
WEB_URL=                 # CORS 허용 도메인

# ── Lambda ──
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ENCRYPTION_KEY=
TELEGRAM_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
GUARDIAN_FUNCTION_NAME=aws-guardian-worker
GUARDIAN_ACCOUNT_ID=     # 서비스 운영 계정 ID
AWS_ENDPOINT_URL=        # LocalStack: http://localhost:4566

# ── GLM 프록시 ──
GLM_API_BASE=            # GLM 구독 엔드포인트
GLM_API_KEY=             # 구독 키
GLM_MODEL=glm-4-plus
GLM_AUTH_HEADER=Authorization
GLM_AUTH_PREFIX=Bearer

# ── LocalStack 개발 ──
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=ap-northeast-2
AWS_ENDPOINT_URL=http://localhost:4566
MOCK_COST_AMOUNT=8.50    # CE Mock 금액 (10 이상이면 경보)
```

---

## 15. 예상 운영 비용

| 규모 | 인프라 비용/월 | 비고 |
|------|--------------|------|
| 개발/테스트 | ~$0 | LocalStack 무료 |
| 100명 | ~$6.50 | Lambda + Railway |
| 1,000명 | ~$25 | Lambda 스케일 |

---

## 16. v2 / v3 로드맵

```
v2.0  CloudTrail Root 로그인 감지
v2.0  IAM 비인가 사용자 생성 감지
v2.0  다중 AWS 계정 지원
v2.5  Slack 알림 / 팀 멤버 초대
v3.0  GuardDuty 통합
v3.0  결제 시스템 (Stripe)
v3.0  웹 대시보드 고도화
```
