# AWS Guardian - 다음 작업 항목

## 📊 프로젝트 현황

**현재 상태**: Sprint 11 Phase 1 + Phase 2 완료 (2026-05-03) ✅  
**전체 진도**: 87% (115+ commits, 50+ components, 20+ API endpoints)

---

## ⚡ 빠른 참고 (Quick Reference)

### Sprint 11 완료 ✅ (2026-05-03)

**Phase 1: 다중 계정 대시보드 기초**
- ✅ AccountSelector 컴포넌트 (다중 계정 드롭다운)
- ✅ RiskScore 컴포넌트 (위험도 시각화)
- ✅ EventFeed 컴포넌트 (실시간 이벤트, 30초 폴링)
- ✅ ActionHistory 컴포넌트 (복구 작업 타임라인)
- ✅ Providers 컴포넌트 (React Context 통합)
- ✅ API 4개 엔드포인트: /accounts, /actions, /remediate, /rollback

**Phase 2: 고급 상호작용**
- ✅ ConfirmationDialog 컴포넌트 (재사용 가능 모달)
- ✅ 직접 작업 실행 버튼 (stop_instance, block_bucket)
- ✅ 에러 상태 처리 (dismissible 에러 배너)
- ✅ 로딩 상태 관리 (per-action spinners)

**품질 지표**
- TypeScript: Zero errors (strict mode)
- 빌드: 1.9초
- 페이지: 12/12 생성 완료
- Mock 데이터: 실행 가능한 pending actions

**문서**
- 📖 `docs/sprints/SPRINT_11_COMPLETION_SUMMARY.md` (450+ lines)
- 📖 `docs/sprints/SPRINT_12_DETAILED_PLAN.md` (500+ lines)
- 📖 `docs/sprints/README.md` (Sprint index)

---

## 📋 Sprint 12 상세 계획 (차기 스프린트)

**상태**: PLANNED - 상세 계획 완료, 구현 준비 완료  
**예상 기간**: 2-3 sessions (각 session = 1-2 phases)

### Phase 1: WebSocket 실시간 업데이트
- Socket.IO 서버 설정 (apps/web/src/lib/socket.ts)
- useSocket 클라이언트 훅
- EventFeed WebSocket 구독 (30초 폴링 제거)
- ActionHistory 실시간 완료 이벤트
- 방 기반 계정 격리 (room-based isolation)

**검증 체크리스트**: Socket.IO 연결, 방 구독, 즉시 업데이트 확인

### Phase 2: Toast 알림
- Toast 컴포넌트 (success/error/info/warning)
- useToast 훅
- ActionHistory 작업 결과 알림
- 자동 4초 dismiss + 수동 dismiss

**검증 체크리스트**: 올바른 스타일, 자동 dismiss, 스택 레이아웃

### Phase 3: 고급 필터링
- ActionHistoryFilter 컴포넌트
- 액션 타입/상태/날짜 범위 필터
- 강화된 /api/actions 쿼리 파라미터
- 필터 상태 관리

**검증 체크리스트**: 필터 적용, 결과 업데이트, 조합 필터

### Phase 4: DynamoDB 감사 로그 통합
- audit_logs.py 강화 (save_audit_log)
- /api/audit-logs 엔드포인트
- AuditLogViewer 컴포넌트
- Lambda 감사 로그 작성

**검증 체크리스트**: TTL 활성화, 로그 작성, 조회 기능

### Phase 5: 성능 최적화
- useDebounce 훅
- 컴포넌트 메모이제이션
- 이미지/자산 최적화
- Bundle 크기 최적화

**검증 체크리스트**: Lighthouse > 80, 콘솔 에러 없음, 번들 < 500KB

**상세 계획 참조**: `docs/sprints/SPRINT_12_DETAILED_PLAN.md`

---

## 📚 기술 스택 (최신)

### Frontend (apps/web)
- **Framework**: Next.js 16.2.4 (App Router)
- **UI Framework**: React 19
- **Styling**: Tailwind CSS v4
- **Auth**: NextAuth v5 (GitHub OAuth)
- **Icons**: lucide-react
- **차트**: recharts (대시보드)
- **상태 관리**: React Context API

### Backend (lambda/guardian)
- **Runtime**: Python 3.12
- **AWS SDK**: boto3 v3
- **스케줄러**: EventBridge (1시간 주기)
- **저장소**: DynamoDB
- **알림**: Telegram Bot API
- **감시 대상**: EC2, S3, CloudTrail, IAM, GuardDuty, Cost Explorer

### 인프라
- **배포**: AWS Lambda (서버리스)
- **IaC**: Terraform
- **로컬 개발**: Docker Compose + LocalStack
- **테스트**: pytest (116/116 passing)

---

## 🎯 전체 로드맵 (Roadmap)

| Sprint | 상태 | 내용 | 기간 |
|--------|------|------|------|
| **Sprint 11** | ✅ DONE | 다중 계정 대시보드 UI | 1 session |
| **Sprint 12** | 📋 NEXT | WebSocket + 필터링 + 감사 로그 | 2-3 sessions |
| Sprint 13 | 🔮 | 모바일 앱 지원 | TBD |
| Sprint 14 | 🔮 | AI 분석 (Gemini 통합) | TBD |
| Sprint 15 | 🔮 | 멀티 리전 배포 | TBD |

**진도**: Sprint 6 → 7 → 8 → 10 → 11 (총 11 sprints completed)

---

## 🚀 다음 세션 시작 가이드 (Sprint 12)

### 준비 사항
```bash
# 1. Sprint 12 계획 읽기
cat docs/sprints/SPRINT_12_DETAILED_PLAN.md

# 2. 필요한 라이브러리 설치
cd apps/web
npm install socket.io socket.io-client react-datepicker

# 3. 개발 서버 시작
npm run dev
# http://localhost:3000에서 테스트

# 4. 빌드 검증
npm run build
```

### Phase 1 (WebSocket) 구현 순서
1. `apps/web/src/lib/socket.ts` 생성 - Socket.IO 서버
2. `apps/web/src/app/api/socket/route.ts` 생성 - 초기화 핸들러
3. `apps/web/src/lib/hooks/useSocket.ts` 생성 - 클라이언트 훅
4. EventFeed.tsx 수정 - 폴링 제거, WebSocket 구독
5. ActionHistory.tsx 수정 - 실시간 업데이트

**검증**: `subscribe-account` 이벤트 확인, 즉시 업데이트 테스트

---

## 📁 디렉토리 구조 (현재)

### apps/web (Frontend)
```
apps/web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── accounts/route.ts
│   │   │   ├── actions/route.ts
│   │   │   ├── remediate/route.ts
│   │   │   ├── rollback/route.ts
│   │   │   ├── events/route.ts
│   │   │   ├── status/route.ts
│   │   │   └── auth/[...nextauth]/route.ts
│   │   ├── layout.tsx (Providers 래핑)
│   │   ├── login/page.tsx
│   │   └── page.tsx (대시보드)
│   ├── components/
│   │   ├── Providers.tsx (AccountContext + AuthSessionProvider)
│   │   ├── Dashboard/
│   │   │   ├── AccountSelector.tsx
│   │   │   ├── RiskScore.tsx
│   │   │   ├── EventFeed.tsx
│   │   │   ├── ActionHistory.tsx
│   │   │   ├── ConfirmationDialog.tsx
│   │   │   └── [Sprint 12 추가]
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   └── SessionProvider.tsx
│   │   └── [기타]
│   ├── lib/
│   │   ├── auth-utils.ts
│   │   └── [Sprint 12: socket.ts, hooks/...]
│   └── styles/
├── auth.ts (NextAuth 설정)
├── middleware.ts
└── package.json
```

### lambda/guardian (Backend)
```
lambda/guardian/
├── checkers/
│   ├── base.py
│   ├── cloudtrail.py
│   ├── iam.py
│   ├── guardduty.py
│   ├── ec2.py
│   ├── s3.py
│   └── cost.py
├── responders/
│   ├── telegram.py
│   └── discord.py
├── storage/
│   └── audit_logs.py
├── orchestrator.py
└── handler.py
```

### docs (문서)
```
docs/
├── sprints/
│   ├── README.md
│   ├── SPRINT_11_COMPLETION_SUMMARY.md
│   ├── SPRINT_12_DETAILED_PLAN.md
│   └── [과거 sprint 문서]
├── guides/
│   ├── CLOUDWATCH_MONITORING.md
│   ├── DOCKER_DEPLOYMENT.md
│   ├── LOCAL_DEVELOPMENT.md
│   └── [기타]
└── README.md
```

---

## 📈 성공 지표

### Phase 1 (WebSocket) 성공 기준
- [ ] WebSocket 가동률 > 99.5%
- [ ] 연결 시간 < 1초
- [ ] 메시지 전달 < 100ms
- [ ] 자동 재연결 작동

### Phase 2 (Toast) 성공 기준
- [ ] Toast 표시 시간 < 100ms
- [ ] 4초 자동 dismiss
- [ ] 수동 dismiss 버튼
- [ ] 스택 레이아웃 정렬

### Phase 3 (필터링) 성공 기준
- [ ] 필터 응답 시간 < 500ms
- [ ] 조합 필터 정확성
- [ ] 날짜 범위 피커 작동

### Phase 4 (감사 로그) 성공 기준
- [ ] DynamoDB 로그 작성 100% 성공
- [ ] 90일 TTL 작동
- [ ] 조회 성능 < 1초

### Phase 5 (성능) 성공 기준
- [ ] Lighthouse 점수 > 80
- [ ] 번들 크기 < 500KB (gzipped)
- [ ] 디바운싱 500ms
- [ ] 콘솔 에러 0개

---

## 🔧 중요한 파일 & 변경사항

### Sprint 11 신규 파일
```
✨ apps/web/src/components/Dashboard/ConfirmationDialog.tsx (40 LOC)
✨ apps/web/src/components/Dashboard/AccountSelector.tsx (65 LOC)
✨ apps/web/src/components/Dashboard/RiskScore.tsx (50 LOC)
✨ apps/web/src/components/Dashboard/EventFeed.tsx (105 LOC)
✨ apps/web/src/components/Dashboard/ActionHistory.tsx (180+ LOC)
✨ apps/web/src/components/Providers.tsx (75 LOC)
✨ apps/web/src/app/api/accounts/route.ts
✨ apps/web/src/app/api/actions/route.ts
✨ apps/web/src/app/api/remediate/route.ts
✨ apps/web/src/app/api/rollback/route.ts
```

### Sprint 11 수정 파일
```
📝 apps/web/src/app/layout.tsx (Providers 래핑)
📝 apps/web/src/app/page.tsx (컴포넌트 추가)
📝 NEXT_STEPS.md (이 파일)
```

---

## ⚙️ 환경 설정 (Env Setup)

### 필수 환경 변수 (.env.local)
```bash
# 인증
AUTH_SECRET=your-secret-key
AUTH_GITHUB_ID=your-github-oauth-id
AUTH_GITHUB_SECRET=your-github-oauth-secret
ADMIN_EMAILS=timotolkie@gmail.com

# AWS
AWS_REGION=ap-northeast-1
AWS_ACCOUNT_ID=your-account-id

# Telegram (선택사항)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### LocalStack 설정 (로컬 개발)
```bash
docker-compose up -d
# DynamoDB, Lambda, EventBridge 자동 생성
```

---

## 🧪 테스트 실행

```bash
# 전체 테스트 (Python Backend)
cd lambda
python -m pytest tests/ -v
# 결과: 116/116 passing

# Frontend 빌드 테스트
cd apps/web
npm run build
# 예상: Zero errors

# 개발 서버 시작
npm run dev
# http://localhost:3000 접근 가능
```

---

## 🐛 알려진 이슈 & 제약사항

### 현재 제약사항 (Sprint 11)
- ✅ 30초 폴링 (WebSocket 대체 예정 → Sprint 12)
- ✅ Mock 데이터 사용 (실제 AWS SDK 호출 향후)
- ✅ 단일 리전 지원 (멀티 리전 → Sprint 13)

### 향후 개선 (Backlog)
- [ ] 실시간 CloudTrail/GuardDuty 이벤트
- [ ] 웹소켓 자동 재연결
- [ ] 모바일 앱 (React Native)
- [ ] Gemini AI 분석
- [ ] SAML/OIDC 지원
- [ ] 멀티 리전 배포
- [ ] 커스텀 룰 엔진

---

## 📞 문의 & 피드백

**문제 발생 시**:
1. CLAUDE.md 확인 (프로젝트 가이드)
2. docs/guides/ 참조 (배포, 개발 가이드)
3. 커밋 로그 확인 (git log --oneline)

**다음 세션 체크리스트**:
- [ ] Sprint 12 계획 읽음 (`docs/sprints/SPRINT_12_DETAILED_PLAN.md`)
- [ ] 필요한 라이브러리 설치 (socket.io, react-datepicker)
- [ ] 개발 서버 실행 가능 (npm run dev)
- [ ] Phase 1 구현 시작 준비 완료

---

**Last Updated**: 2026-05-03  
**Status**: Sprint 11 Complete, Ready for Sprint 12  
**Next Session**: WebSocket Integration + Toast Notifications
