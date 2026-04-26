# AI Orchestra — AWS Guardian 개발 환경

> Claude Code(사령관) + GLM 5.1(구현) + Gemini(문서화)를 tmux + aider로 연결한
> 3-AI 병렬 개발 환경. LocalStack에서 AWS 서비스를 에뮬레이션하며 개발한다.

---

## 역할 분담

| AI | 역할 | 담당 범위 |
|----|------|-----------|
| Claude Code | 사령관 | 태스크 분해, 코드 리뷰, 보안 검토, 최종 승인, AI간 조율 |
| GLM 5.1 | 구현병 | Lambda 핵심 로직, NestJS API, 테스트 코드 작성 |
| Gemini | 문서병 | SKILL.md 갱신, API 문서, README, 변경 이력 |

---

## tmux 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  pane 0: Claude Code (사령관)                        │
│  $ aider --model claude-sonnet-4-5 --architect      │
├──────────────────────┬──────────────────────────────│
│  pane 1: GLM 5.1     │  pane 2: Gemini              │
│  $ aider --model     │  $ aider --model             │
│    openrouter/GLM    │    gemini/gemini-2.0-flash   │
├──────────────────────┴──────────────────────────────│
│  pane 3: LocalStack + 로그                           │
│  $ docker compose up localstack                     │
└─────────────────────────────────────────────────────┘
```

---

## 워크플로우

```
1. Claude Code → 태스크 분해 → TASK.md 작성
2. Claude Code → GLM에게 구현 지시 (shared/tasks/ 파일로 전달)
3. GLM → 코드 작성 → shared/review/ 에 PR 요청
4. Claude Code → 코드 리뷰 → 승인/수정 요청
5. Gemini → 변경 감지 → 문서 자동 갱신
6. LocalStack → 통합 테스트 자동 실행
```

---

## 디렉토리 구조

```
aws-guardian-saas/
├── .ai-orchestra/
│   ├── shared/
│   │   ├── tasks/        # Claude → GLM 태스크 지시
│   │   ├── review/       # GLM → Claude 리뷰 요청
│   │   └── docs/         # Claude → Gemini 문서 지시
│   ├── prompts/
│   │   ├── claude.md     # Claude Code 시스템 프롬프트
│   │   ├── glm.md        # GLM 시스템 프롬프트
│   │   └── gemini.md     # Gemini 시스템 프롬프트
│   └── orchestra.sh      # tmux 세션 자동 시작 스크립트
├── localstack/
│   ├── docker-compose.yml
│   ├── init/             # LocalStack 초기화 스크립트
│   └── .env.localstack
├── apps/
│   ├── web/
│   └── api/
└── lambda/
```

---

## LocalStack 에뮬레이션 서비스

| AWS 서비스 | LocalStack 포트 | 용도 |
|-----------|----------------|------|
| Lambda | 4566 | guardian, dispatcher |
| DynamoDB | 4566 | guardian-events |
| S3 | 4566 | 테스트 버킷 |
| SSM | 4566 | 파라미터 스토어 |
| STS | 4566 | AssumeRole 시뮬레이션 |
| EventBridge | 4566 | 1시간 트리거 시뮬레이션 |
| CloudWatch | 4566 | Lambda 로그 |
| KMS | 4566 | 암호화 키 |
| Cost Explorer | 4566 (mock) | 비용 데이터 모킹 |
