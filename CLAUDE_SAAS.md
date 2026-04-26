# AWS Guardian SaaS

> AWS 계정 보안/비용 감시를 구독형 서비스로 제공.
> 사용자는 가입 → AWS 연동 → Telegram 설정만 하면 자동 감시 시작.

---

## 슬로건

**"당신의 AWS, 우리가 지켜드립니다"**

---

## v1 → SaaS 전환 핵심 변화

| 항목 | v1 (개인용) | SaaS |
|------|------------|------|
| 사용자 | 1명 (본인) | N명 (멀티테넌트) |
| AWS 연동 | 환경변수 고정 | 사용자별 IAM Role ARN / Access Key |
| Lambda | 단일 함수 | 사용자별 독립 실행 |
| 알림 설정 | 코드 수정 | 웹 대시보드 + Telegram Bot |
| 온보딩 | 직접 배포 | 웹 가입 → 5단계 위저드 |
| 과금 | 없음 | Freemium 구조 (추후 확정) |

---

## 전체 아키텍처

```
[사용자]
  웹 온보딩 (Next.js)          Telegram Bot
       │                            │
       ▼                            ▼
  Supabase Auth              /connect 명령어
  (가입/로그인)               → 웹 연동 유도
       │
       ▼
  NestJS API Server (사용자 관리 / 설정 저장)
       │
  Supabase DB (users, connections, events, alerts)
       │
       ▼
  AWS Lambda Dispatcher
  (EventBridge 1h 트리거 → 사용자 목록 조회 → 병렬 감시 실행)
       │
       ├── boto3 AssumeRole (Cross-Account)
       └── boto3 직접 키 (Access Key 방식)
            │
      ┌─────┴──────┐
   Cost          EC2/S3
   Checker      Checker
      └─────┬──────┘
            │ 이상 감지
            ▼
     자동 대응 (Stop/Block)
            │
     ┌──────┴──────┐
  Telegram       Discord
  알림            Webhook
            │
     Supabase 이벤트 로그
            │
     웹 대시보드 실시간 반영
```

---

## 온보딩 플로우 (5단계)

```
Step 1. 이메일 가입 / 소셜 로그인 (Google, GitHub)
    ↓
Step 2. Telegram 연동
        - 봇에게 /connect 입력
        - 6자리 코드 발급 → 웹에 입력
        - chat_id 자동 저장
    ↓
Step 3. AWS 연동 방식 선택
        A) Cross-Account IAM Role
           - 가이드 따라 사용자 계정에 IAM Role 생성
           - Role ARN 입력
           - 연동 테스트 (AssumeRole 검증)
        B) Access Key / Secret
           - 키 입력 → AES-256 암호화 저장
           - 최소 권한 IAM Policy 가이드 제공
    ↓
Step 4. 감시 설정
        - 감시 항목 선택 (비용 / EC2 / S3)
        - 비용 임계값 설정 (기본 $10/일)
        - 허용 리전 지정
        - 자동 대응 ON/OFF
    ↓
Step 5. 첫 감시 실행 & 결과 확인
        - 즉시 테스트 실행
        - Telegram으로 정상 알림 수신 확인
        → 온보딩 완료
```

---

## 핵심 기능

### 멀티테넌트 감시 엔진
- EventBridge 1시간 트리거 → 활성 사용자 전체 병렬 처리
- 사용자별 독립 실행 컨텍스트 (Cross-Account Isolation)
- 실패한 사용자만 재시도 (Dead Letter Queue)

### AWS 연동 보안
- Cross-Account Role: External ID 강제 적용 (혼동된 대리인 공격 방지)
- Access Key: AWS KMS + Supabase Vault 이중 암호화
- 연동 상태 주기적 검증 (권한 만료 사전 알림)

### 알림 채널
- Telegram: 이상 감지 즉시 알림 + 자동 대응 결과
- Discord: 팀 공유용 Webhook (선택)
- 웹 대시보드: 히스토리 / 통계 / 실시간 상태

### 대시보드
- 비용 추이 차트 (7일 / 30일)
- EC2 인스턴스 현황
- S3 버킷 보안 상태
- 이벤트 로그 (자동 대응 내역)
- 설정 변경 (임계값 / 리전 / 자동 대응)

---

## 수익 모델 (Freemium 기준 초안)

| 플랜 | 가격 | 제한 |
|------|------|------|
| Free | 무료 | 감시 1계정, 비용만 감시, 알림 3회/일 |
| Pro | $9/월 | 감시 3계정, 전체 감시, 무제한 알림, 자동 대응 |
| Team | $29/월 | 감시 10계정, Discord 팀 알림, 감사 로그 |

> 수익 모델 미확정이므로 플랜 구분 없이 v1 SaaS 먼저 출시 후 결정 가능

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트 | Next.js 14 (App Router), Tailwind CSS |
| 백엔드 | NestJS (API) + Supabase (DB/Auth/Realtime) |
| 감시 엔진 | AWS Lambda (Python 3.12) |
| 스케줄러 | AWS EventBridge |
| 암호화 | AWS KMS + Supabase Vault |
| 알림 | Telegram Bot API, Discord Webhook |
| 배포 | Vercel (프론트) + AWS Lambda (엔진) |
| IaC | Terraform |

---

## 스코프

### v1 SaaS (MVP)
- 이메일 가입 + Google OAuth
- Telegram 연동 온보딩
- Cross-Account IAM Role + Access Key 둘 다 지원
- 비용 / EC2 / S3 감시
- 웹 대시보드 (설정 + 이벤트 로그)
- 자동 대응 (EC2 Stop / S3 퍼블릭 차단)

### v2
- Discord Bot 대시보드
- 다중 AWS 계정 (계정 추가)
- Slack 알림
- 팀 멤버 초대

### v3
- CloudTrail IAM 이상 감지
- GuardDuty 통합
- 결제 시스템 (Stripe)
- 사용량 기반 과금

---

## 디렉토리 구조

```
aws-guardian-saas/
├── CLAUDE.md
├── SKILL.md
├── apps/
│   ├── web/                    # Next.js 프론트
│   │   ├── app/
│   │   │   ├── (auth)/         # 가입/로그인
│   │   │   ├── onboarding/     # 5단계 온보딩
│   │   │   └── dashboard/      # 메인 대시보드
│   │   └── components/
│   └── api/                    # NestJS 백엔드
│       └── src/
│           ├── auth/
│           ├── users/
│           ├── connections/     # AWS 연동 관리
│           ├── settings/        # 감시 설정
│           └── events/          # 이벤트 로그
├── lambda/
│   ├── dispatcher/              # 사용자 목록 → 병렬 실행
│   └── guardian/                # 기존 감시 엔진 (멀티테넌트 대응)
├── terraform/
└── supabase/
    └── migrations/
```

---

## 성공 지표

- 온보딩 완료율 > 70%
- Lambda 1회 실행 평균 비용 < $0.001/사용자
- 이상 감지 → 알림 도달 < 5분
- 월 인프라 비용 100명 기준 < $20
