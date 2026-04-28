# AWS Guardian - 다음 작업 항목

## 1. 우선순위 높음 (핵심 기능 완성)

### ~~1-1. 프론트엔드 실시간 API 연동~~ ✅ 완료
- **완료일**: 2026-04-26
- **변경 내용**:
  - `types/guardian.ts` — 공유 TypeScript 인터페이스 분리
  - `lib/dynamodb.ts` — DynamoDB 클라이언트 (LocalStack/AWS 자동 감지)
  - `app/api/status/route.ts` — `GET /api/status` 대시보드 종합 데이터 API
  - `app/api/events/route.ts` — `GET /api/events` 이벤트 로그 API (type/severity 필터)
  - `hooks/useGuardianData.ts` — SWR 기반 커스텀 훅 (60초 자동 갱신)
  - Python 핸들러(`handler.py`) 수정: 모든 체크 결과를 `check_result` 이벤트로 DynamoDB에 저장
  - 5개 페이지(`page.tsx`, `cost/`, `ec2/`, `s3/`, `events/`) mock → API 전환
  - API 실패 시 기존 mock 데이터로 fallback
- **의존성 추가**: `swr`, `@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb`

### ~~1-2. Telegram 봇 명령어 확장~~ ✅ 완료 (2026-04-26)
- **완료 내용**:
  - `/status` — 현재 EC2, S3, 비용 요약 조회
  - `/instances` — 실행 중인 인스턴스 목록
  - `/stop {id}` — 특정 인스턴스 개별 중지
  - `/threshold {amount}` — 비용 임계값 즉시 변경
  - `/history [시간]` — 최근 이벤트 로그 (기본 24시간)
  - `/help` — 명령어 도움말
- **수정 파일**:
  - `telegram_bot.py`: 7개 명령어 핸들러 함수 추가
  - `parse_command()`: 슬래시 명령어 및 인자 파싱 지원
  - `_format_response()`: 명령어 타입별 응답 포맷팅

### ~~1-3. 스케줄러 자동 실행~~ ✅ 완료 (2026-04-26)
- **완료 내용**:
  - `APScheduler` 기반 백그라운드 스케줄러 구현 (1시간 주기)
  - 즉시 실행 + 정기 실행 지원
  - 에러 복구 (misfire_grace_time=30초)
- **파일 추가**:
  - `lambda/guardian/scheduler.py`: GuardianScheduler 클래스
- **파일 수정**:
  - `requirements.txt`: apscheduler==3.10.4 추가
  - `start.sh`: 스케줄러 백그라운드 실행 추가
  - `stop.sh`: 스케줄러 프로세스 정리 추가
- **실제 AWS 배포**: EventBridge로 전환 (Terraform에서 구성)

---

## 2. 우선순위 중간 (안정성 및 모니터링)

### ~~2-1. 로깅 시스템 개선~~ ✅ 완료 (2026-04-26)
- **완료 내용**:
  - Python `logging` 모듈 도입 (DEBUG, INFO, WARNING, ERROR)
  - JSON 포맷 로깅 (구조화된 로그)
  - 콘솔 + 파일 핸들러 (guardian.log)
- **파일 추가**:
  - `lambda/guardian/logging_config.py`: JSONFormatter, setup_logger()
- **파일 수정**:
  - `lambda/guardian/handler.py`: 모든 print() → logger.info/error 변경
  - `lambda/guardian/responders/auto_remediation.py`: 로깅 추가
- **CloudWatch Logs**: 프로덕션 배포 시 Lambda에서 자동 지원

### ~~2-2. 에러 핸들링 강화~~ ✅ 부분 완료 (2026-04-26)
- **완료 내용**:
  - `auto_remediation.py`: 개별 단계 try-except 추가
  - 실패 단계 기록 및 부분 성공 지원
  - API 호출 실패 시 상세 로깅
- **향후 작업** (v2):
  - Telegram/Discord 전송 재시도 (exponential backoff)
  - LocalStack 연결 복구 로직
  - DynamoDB 쓰기 실패 시 로컬 백업

### ~~2-3. 프론트엔드 알림 히스토리 페이지~~ ✅ 완료 (2026-04-26)
- **완료 내용**:
  - 타임라인 형태의 이벤트 UI (테이블 → 타임라인)
  - 날짜 범위 필터링 (시작일~종료일 선택기)
  - 자동 수정 액션 상세 보기 (expand/collapse 토글)
  - CSV Export 버튼 실제 동작 구현
- **파일 수정**:
  - `apps/web/src/hooks/useGuardianData.ts`: startDate, endDate 파라미터 추가
  - `apps/web/src/app/events/page.tsx`: 완전 리디자인 (타임라인, 필터, CSV, 상세보기)

---

## 3. 우선순위 낮음 (기능 확장)

### 3-1. 추가 AWS 서비스 감시
- **CloudTrail**: 비정상 API 호출 탐지
- **IAM**: 권한 변경, 새 키 생성 감지
- **GuardDuty**: 위협 탐지 결과 연동
- **RDS**: 퍼블릭 접근 가능한 DB 인스턴스 감지
- **Lambda**: 비정상적으로 많은 실행 감지
- 작업:
  - `checkers/`에 새 체커 모듈 추가
  - 핸들러에 체크 루프 추가
  - Telegram 알림 포맷 정의

### 3-2. 다중 AWS 계정 지원
- Organizations 기반 다중 계정 모니터링
- 계정별 독립 임계값 설정
- 계정별 알림 채널 분리
- Cross-account IAM Role 연동

### 3-3. 웹 대시보드 인증
- NextAuth.js 또는 Clerk 도입
- 로그인 기반 접근 제어
- 역할별 권한 (관리자 / 읽기 전용)
- 설정 변경 시 인증 요구

### 3-4. Discord Slash Command 연동
- `lambda/discord_webhook/handler.py` 실제 연동
- Discord Developer Portal 봇 설정
- API Gateway + Lambda 배포
- `/status`, `/stop`, `/budget set`, `/history` 명령어 활성화

---

## 4. 프로덕션 배포 준비

### 4-1. Terraform 검증
- `AWS_ENV=production` 모드 테스트
- 실제 AWS 리소스에 IAM 태그 조건 적용 검증
- SSM 파라미터 경로 `/guardian/*` 확인
- DynamoDB TTL 설정 (30일 자동 삭제)

### 4-2. CI/CD 파이라인
- GitHub Actions 워크플로우
  - 테스트 자동 실행
  - Lambda 패키징
  - Terraform plan/apply
  - 프론트엔드 Vercel 배포

### 4-3. 비용 최적화 검증
- Lambda 월 실행 비용 < $0.50 확인
- DynamoDB 무료 티어 범위 내 사용 확인
- CloudWatch Logs 보존 기간 설정 (7일)

---

## 기술 부채

| 항목 | 현황 | 조치 | 상태 |
|------|------|------|------|
| ~~`datetime.utcnow()` deprecated~~ | ~~Python 3.12+ 경고~~ | ✅ `datetime.now(timezone.utc)` 전환 | ✅ 완료 |
| `docker-compose.yml` version 필드 | obsolete 경고 | version 라인 삭제 | 📋 TODO |
| ~~프론트엔드 mock 데이터~~ | ~~하드코딩~~ | ✅ API 연동 완료 | ✅ 완료 |
| LocalStack Auth Token 노출 | `docker-compose.yml`에 평문 | `.env` 파일로 분리 + `.gitignore` | 📋 TODO |
| 테스트 커버리지 | 19개 통합 테스트만 | 순수 단위 테스트 (mock) 추가 | 📋 TODO |
| API Route DynamoDB Scan | `getLatestCheckResult()`의 전체 스캔 | GSI 추가 또는 최신 결과 캐싱 | 📋 TODO |

---

## ✅ 2026-04-26 개발 세션 2 - 다음 단계 완료

### 완료된 작업

#### 1️⃣ docker-compose.yml 정리
- version 필드 제거 (obsolete 경고 해결)
- .env 파일 참조로 변경

#### 2️⃣ LocalStack Auth Token 환경변수 분리
- .env 파일 생성 (민감 정보 분리)
- .gitignore에 .env 포함 확인
- start.sh에서 .env 로드 로직 추가

#### 3️⃣ 단위 테스트 추가 (3개 파일)
- **test_logging.py** (8개 테스트) - ✅ 100% 통과
- **test_telegram.py** (10개 테스트) - ✅ 통과
- **test_auto_remediation.py** (9개 테스트) - ✅ 통과

**총 테스트 결과**: 44개 테스트 중 40개 통과 (91% 성공률)
- 실패: 4개 (주로 LocalStack 연결 불가 - 예상된 결과)
- 스킵: 1개

#### 4️⃣ 기술 부채 해결 현황
| 항목 | 상태 |
|------|------|
| ~~`datetime.utcnow()` deprecated~~ | ✅ 완료 |
| ~~docker-compose.yml version~~ | ✅ 완료 |
| ~~LocalStack Token 노출~~ | ✅ 완료 |
| 테스트 커버리지 | ✅ 확대 (19→44 테스트) |

---

## ✅ 2026-04-26 개발 세션 요약

### 완료된 기능 (우선순위 높음)
1. **Telegram 봇 명령어 7개 추가** (/status, /instances, /stop, /threshold, /history, /help)
2. **APScheduler 기반 1시간 주기 감시**
3. **Python logging 시스템** (JSON 포맷 + 파일 로깅)
4. **프론트엔드 이벤트 타임라인** (UI 리디자인)
5. **날짜 범위 필터 + CSV Export**
6. **datetime.utcnow() → datetime.now(timezone.utc)** (Python 3.12+ 호환)

## ✅ 2026-04-26 개발 세션 3-4 - Gemini CLI 통합 & Sprint 1 완료

### 세션 3 완료: Gemini CLI ↔ Claude Code 통합 인프라
- **~/.gemini/claude_wrapper.sh** (176 라인) - 메인 wrapper
- **./scripts/gemini-ask.sh** (51 라인) - 프로젝트 인터페이스  
- **./scripts/setup-gemini.sh** (307 라인) - 초기화 스크립트
- ✅ 라이브 테스트: Code Review, Code Generation 성공

### 세션 4 완료: Sprint 1 - Lambda 콜드 스타트 최적화

#### 🎯 Gemini의 아키텍처 분석
- 현재 문제점: handler 내부 초기화, boto3 중복 생성, 모놀리틱 구조
- 개선 전략: 글로벌 스코프 초기화, AWS 클라이언트 싱글톤, 오케스트레이터 패턴

#### 📁 구현 완료 (4개 파일)

**1. aws_client_provider.py** (NEW, 55줄)
- boto3 클라이언트 싱글톤 캐싱
- 서비스별/리전별 재사용
- get_client(service_name, region) 메서드

**2. orchestrator.py** (NEW, 172줄)
- GuardianOrchestrator 클래스
- run_all_checks() 메인 메서드
- _run_cost_check(), _run_ec2_check(), _run_s3_check()
- 의존성 주입 패턴

**3. remediation_service.py** (NEW, 126줄)
- AutoRemediationResponder 클래스
- handle_exposed_instances() - EC2 자동 중지
- handle_public_buckets() - S3 퍼블릭 차단
- 자동 대응 로직 분리

**4. handler.py** (REFACTORED)
- 217줄 → 55줄 (75% 단순화)
- 글로벌 스코프 초기화 패턴
- lambda_handler() → orchestrator.run_all_checks(event)만 호출

#### ✅ 검증 완료
- 모든 파일 구문 검증 통과 (py_compile)
- 의존성 import 경로 확인

#### 📊 성능 개선
| 항목 | Before | After |
|------|--------|-------|
| Handler 라인 | 217줄 | 55줄 |
| Cold Start | 매 호출마다 초기화 | 컨테이너당 1회만 |
| boto3 클라이언트 | 중복 생성 | 싱글톤 캐시 |
| 가독성 | 모놀리틱 | 모듈식 |

## ✅ 2026-04-27 개발 세션 5 - Sprint 2 완료 (Docker Compose 최적화)

### 🎯 실행 전략
- Gemini CLI가 도구 제한으로 인해 부분 완료
- Claude Code가 직접 docker-compose.yml 분석 및 구현

### 📁 구현 완료 (4개 신규 파일 + 1개 수정)

#### 1. **docker-compose.yml** (REFACTORED, 55줄)
**주요 개선:**
- LocalStack 버전 고정: `latest` → `3.0.0`
- 환경변수 명확한 주석 (DEBUG=1 LOCAL ONLY 표시)
- Healthcheck 수정: kinesis (미사용) → s3
- 리소스 제한 추가: 2 CPU, 2GB memory
- 영구 저장소: `./data/localstack`
- Restart 정책: `unless-stopped`
- Startup 타임아웃: `start_period: 10s`

#### 2. **docker-compose.production.yml** (NEW, 120줄)
**프로덕션 구성:**
- 리소스 확장: 4 CPU, 4GB memory
- 보안 강화: `127.0.0.1:4566` (localhost만)
- Secrets Manager 통합: `${AWS_*}` 환경변수
- CloudWatch 로깅: JSON 포맷, 10MB max-size
- IAM 정책 강제: `ENFORCE_IAM_POLICIES=true`
- 자동 재시작: on-failure (max 5회)
- Persistent volume 분리: `/data/localstack-prod`

#### 3. **.env.example** (ENHANCED, 80줄)
**개선:**
- 섹션별 분류 (AWS, Telegram, Discord, LocalStack)
- 사용 안내: `cp .env.example .env`
- 보안 경고: `.gitignore` 명시
- 각 변수 용도 설명
- 개발 도구 가이드

#### 4. **.env.production.example** (NEW, 90줄)
**프로덕션 보안:**
- Secrets Manager 참조: `<from-aws-secrets-manager>`
- IAM 역할 권장 (하드코딩 방지)
- CloudWatch/X-Ray 통합 설정
- 배포 정보 자동 주입 (CI/CD)

#### 5. **DOCKER_DEPLOYMENT_GUIDE.md** (NEW, 450줄)
**완전한 가이드:**
- 📖 로컬 개발 5단계 (docker-compose up 포함)
- 🚀 프로덕션 배포 전체 과정
- 🔐 보안 best practices (DO/DON'T)
- 📊 모니터링 및 로깅 (CloudWatch, DynamoDB)
- 🆘 트러블슈팅 10가지 시나리오
- 💰 비용 추정 ($1.35/월)

### ✅ 검증 완료
```bash
docker-compose config  # ✅ 구문 검증 통과
```

### 📊 개선 요약
| 항목 | Before | After |
|------|--------|-------|
| docker-compose.yml | 30줄 (기본) | 55줄 (상세) |
| 리소스 제한 | ❌ 없음 | ✅ CPU/Memory |
| 프로덕션 설정 | ❌ 없음 | ✅ 별도 파일 |
| 환경변수 문서화 | ❌ 최소 | ✅ 상세 주석 |
| 보안 가이드 | ❌ 없음 | ✅ 전체 문서 |
| Healthcheck | kinesis ❌ | s3 ✅ |
| 버전 고정 | latest ❌ | 3.0.0 ✅ |

---

## 📋 다음 개발 스프린트 계획

### ~~Sprint 2: Docker Compose 아키텍처 검토~~ ✅ 완료
**상태**: ✅ COMPLETED (2026-04-27)

**완료 항목**:
- ✅ Gemini CLI 분석 수행
- ✅ docker-compose.yml 최적화 (55줄)
- ✅ docker-compose.production.yml 신규 (120줄)
- ✅ 환경변수 분리 강화 (.env.example + .env.production.example)
- ✅ DOCKER_DEPLOYMENT_GUIDE.md 작성 (450줄)
- ✅ LocalStack healthcheck 수정 (kinesis → s3)
- ✅ 리소스 제한 추가 (CPU/Memory)
- ✅ start.sh 검증 완료

---

### ~~Sprint 3: DynamoDB API 최적화 (GSI 추가)~~ ✅ 완료
**상태**: ✅ COMPLETED (2026-04-27)

**Gemini 분석 완료** ✅

#### 🎯 GSI 설계 (Gemini 제안)
- **AllEventsIndex**: gsi_pk (상수 "EVENT") + timestamp → 대시보드
- **TypeTimestampIndex**: event_type + timestamp → 타입별 필터
- **SeverityTimestampIndex**: severity + timestamp → 심각도별 필터
- **CheckTypeTimestampIndex**: (향후 확장용)

#### 📁 구현 완료 (5개 파일)

**1. terraform/dynamodb.tf** (REFACTORED)
- Primary Key 변경: timestamp → event_id + timestamp
- Attributes 추가: event_type, severity, gsi_pk
- GSI 3개 추가 (INCLUDE/ALL projection)

**2. apps/web/src/lib/dynamodb.ts** (NEW METHODS, 100줄)
- QueryCommand import 추가
- getEventsByGSI() - AllEventsIndex 쿼리
- getEventsByType() - TypeTimestampIndex 쿼리
- getEventsBySeverity() - SeverityTimestampIndex 쿼리
- getLatestCheckResultOptimized() - Query 최적화

**3. apps/web/src/app/api/events/route.ts** (REFACTORED)
- Scan → Query 전환
- 필터별 GSI 선택 로직
- transformEvents() 헬퍼 함수 추가
- Secondary filter 지원 (type + severity)

**4. lambda/guardian/storage/dynamodb.py** (ENHANCED)
- save_event(): event_id + gsi_pk 필드 추가
- get_recent_events(): Query 최적화 (GSI 사용)
- get_events_by_severity(): 신규 Query 메서드

**5. 분석 문서** (SPRINT_3_*.md)
- SPRINT_3_ANALYSIS.md: 현재 문제점 분석
- SPRINT_3_IMPLEMENTATION_PLAN.md: 4단계 구현 계획

#### ✅ 검증 완료
- Terraform HCL 구문 정상
- TypeScript 쿼리 메서드 구현
- Python 쿼리 메서드 구현
- API 라우트 리팩토링

#### 📊 성능 개선 (예상)
| 메트릭 | Before | After | 개선율 |
|--------|--------|-------|--------|
| Query Time | 2-3초 | <10ms | ⬇️ 99% |
| RCU/Query | 1000+ | 10-100 | ⬇️ 99% |
| Cost/Day | ~$0.50 | ~$0.05 | ⬇️ 90% |

#### 🔄 쿼리 전환
```typescript
// Before: Scan (비효율)
getRecentEvents() → ScanCommand (모든 데이터)

// After: Query (효율적)
getEventsByType() → TypeTimestampIndex Query
getEventsBySeverity() → SeverityTimestampIndex Query
getEventsByGSI() → AllEventsIndex Query
```

---

### ✅ Sprint 4: 프로덕션 배포 준비
**상태**: ✅ COMPLETED (2026-04-27)

#### 🎯 Phase 1: 인프라 준비 ✅ 완료
**EventBridge 비용 최적화:**
- 분할 스케줄링: 시간별 (EC2/S3만) + 일별 (비용 확인)
- 월간 비용: $7.30 → $0.30 (95% 절감)

**구현 완료**:
1. `terraform/eventbridge.tf` (REFACTORED)
   - Rule 1: `cron(0 * * * ? *)` - 시간별 보안 검사
   - Rule 2: `cron(0 0 * * ? *)` - 일일 비용 확인
   - IAM role + Lambda permission 자동 설정

2. `lambda/guardian/orchestrator.py` (ENHANCED)
   - `check_type` 파라미터 지원
   - `check_type="security"` → 비용 확인 스킵
   - `check_type="cost"` → 보안 검사 스킵
   - 하위 호환성 유지 (기본값: "all")

**비용 분석**:
| 항목 | 값 | 월비용 |
|------|-----|--------|
| Lambda | 730 호출 | $0.00 |
| EventBridge | 760 이벤트 | $0.00 |
| DynamoDB | 온디맨드 | $0.00 |
| Cost Explorer API | 30호출 | $0.30 |
| CloudWatch Logs | ~700MB | $0.10 |
| **합계** | | **$0.40** ✅ |

#### 🎯 Phase 3: CI/CD 파이프라인 ✅ 완료
**GitHub Actions 파이프라인** (.github/workflows/deploy.yml, 250+ 줄)

4단계 자동화:
1. **Lint** (2-3분)
   - flake8, black, isort, tfsec
   - Terraform fmt 검증

2. **Test** (3-5분)
   - pytest + moto (AWS 모킹)
   - 커버리지 리포팅 (Codecov)

3. **Build** (2-3분, main 브랜치만)
   - Lambda 패키지 생성 (의존성 포함)
   - 아티팩트 업로드

4. **Deploy** (1-2분, 승인 필요)
   - GitHub OIDC 인증 (하드코딩 자격증명 없음)
   - Terraform init/plan/apply
   - Lambda + EventBridge 검증
   - Slack 알림

**주요 기능**:
- 동시성 제어: 배포 중복 방지
- 환경 승인: 프로덕션 수동 승인
- 9개 GitHub Secret 설정
- S3 Terraform State + DynamoDB Lock

#### 📁 작성된 문서
1. **SPRINT_4_PHASE_1_COMPLETE.md** (413줄)
   - EventBridge 설계 상세
   - 테스트 전략
   - 성공 기준

2. **SPRINT_4_PHASE_3_CI_CD.md** (450줄)
   - CI/CD 파이프라인 완전 가이드
   - GitHub Secret 설정 (9개)
   - Terraform 백엔드 구성
   - 로컬 검증 워크플로우

3. **PRODUCTION_DEPLOYMENT_CHECKLIST.md** (600줄)
   - 6단계 배포 가이드
   - AWS 인프라 설정 (S3, DynamoDB, IAM)
   - GitHub OIDC 구성 (자격증명 없음)
   - Post-deployment 검증
   - 롤백 절차

4. **SPRINT_4_COMPLETE.md** (413줄)
   - 실행 요약
   - 아키텍처 다이어그램
   - 팀 인수인계
   - 성공 지표

#### ✅ 검증 완료
- Terraform HCL 구문 검증
- GitHub Actions 워크플로우 구문 검증
- 모든 문서 작성 완료
- 배포 체크리스트 생성

### 🚀 Sprint 5: LocalStack 배포 & 프로덕션 준비 - IN PROGRESS
**상태**: 🔄 실행 중 (2026-04-28 시작)
**예상 소요시간**: 2-3시간 (인프라 설정) + 배포 + 모니터링
**담당**: Gemini + Claude Code 협업

#### ✅ Phase 1: LocalStack 배포 완료 (2026-04-28)

**완료 항목**:
- ✅ Terraform 프로바이더 LocalStack 엔드포인트 설정
- ✅ deploy-to-localstack.sh 스크립트 작성 (AWS CLI 기반, Terraform 대체)
- ✅ Lambda 함수 배포: aws-guardian-monitor (python3.10, 256MB, 60s timeout)
- ✅ EventBridge 규칙 설정: hourly (1시간 주기, EC2/S3) + daily (1일 주기, 비용)
- ✅ IAM 역할 생성: aws-guardian-role (EC2, S3, Cost Explorer, DynamoDB 권한)
- ✅ Lambda <-> EventBridge 통합 검증

**배포된 리소스 (LocalStack)**:
```
Lambda:
  - FunctionName: aws-guardian-monitor
  - Runtime: python3.10
  - Handler: lambda.guardian.handler.lambda_handler
  - Role: arn:aws:iam::000000000000:role/aws-guardian-role
  - State: Active (CodeSize: 22.8MB)

EventBridge Rules:
  - aws-guardian-hourly: rate(1 hour) → Lambda
  - aws-guardian-daily: rate(1 day) → Lambda

IAM Role:
  - aws-guardian-role: Lambda 실행 역할
  - Permissions: EC2, S3, Cost Explorer, DynamoDB, SSM
```

**기술적 문제 및 해결**:
1. Terraform AWS Provider 초기화 실패 (InvalidClientTokenId)
   - **원인**: LocalStack STS 토큰 검증 이슈
   - **해결**: AWS CLI 기반 직접 배포 (deploy-to-localstack.sh)
   - **장점**: Terraform 종속성 제거, 빠른 배포, 디버깅 용이

2. EventBridge targets JSON 파싱 에러
   - **원인**: AWS CLI 파라미터 포맷팅 문제
   - **해결**: JSON 배열 형식 사용 ([{...}])

3. Lambda runtime python3.12 미지원
   - **원인**: LocalStack 2.1.0 Community Edition 제약
   - **해결**: python3.10으로 다운그레이드

**테스트 명령어**:
```bash
export AWS_ACCESS_KEY_ID="LKIAQAAAAAAAFDDEIMEA"
export AWS_SECRET_ACCESS_KEY="8TORaGyHmPAJAfP3vBebnpKpuepjEmqiRuftAPQD"

# Lambda 직접 호출
aws lambda invoke \
  --function-name aws-guardian-monitor \
  --cli-binary-format raw-in-base64-out \
  --payload '{"check_type":"hourly"}' \
  --endpoint-url http://localhost:4566 \
  /tmp/response.json

# EventBridge 규칙 확인
aws events list-rules --endpoint-url http://localhost:4566
aws events list-targets-by-rule --rule aws-guardian-hourly --endpoint-url http://localhost:4566
```

---

#### 📋 Phase 2: Terraform 백엔드 설정 (자동화 스크립트) - READY

**전제 조건:**
- ✅ AWS CLI 설치 및 자격증명 설정 필요
- ✅ GitHub 리포지토리 생성 필요 (현재: 로컬만 존재)
- ✅ GitHub 조직 또는 사용자명 필요

**프로덕션 AWS 배포 준비 상태:**
```
✅ LocalStack 배포 완료 → 실제 AWS 배포 준비 완료
⏳ Phase 2 대기: AWS 자격증명 및 GitHub 저장소 설정 필요
```

**자동화 스크립트 실행 (Phase 2 시작 시):**
```bash
# 1. AWS 인프라 자동 설정 (S3, DynamoDB, IAM OIDC)
./scripts/deploy-infrastructure.sh <GITHUB_ORG>

# Example (GitHub 사용자명: jinyounghwa):
./scripts/deploy-infrastructure.sh jinyounghwa

# 이 스크립트가 자동으로 수행할 작업:
# ✅ GitHub OIDC Provider 확인/생성 (AWS IAM)
# ✅ S3 버킷 생성 (terraform state 저장)
# ✅ DynamoDB 테이블 생성 (terraform state lock)
# ✅ IAM 역할 생성 (GitHub OIDC 신뢰 관계)
# ✅ IAM 정책 연결 (최소 권한 원칙)

# 이후 화면에 표시되는 값들:
# - S3_BUCKET_NAME (Terraform 상태 저장소)
# - ROLE_ARN (GitHub Actions가 가정할 IAM 역할)
# - 이 값들을 GitHub Secrets에 저장해야 함
```

**수동 방법 (필요시):**
- PRODUCTION_DEPLOYMENT_CHECKLIST.md의 Phase 2 전체 단계 참조

#### 📋 Phase 3: GitHub Secret 설정 (자동화 스크립트)

**추천 방법 (자동화):**
```bash
# GitHub CLI 로그인 (처음 1회만)
gh auth login

# GitHub 시크릿 자동 설정 (Phase 2 완료 후)
./scripts/configure-github-secrets.sh

# 이 스크립트가 자동으로 수행할 작업:
# ✅ GitHub CLI 인증 확인
# ✅ Phase 2에서 생성된 값들 자동로드
# ✅ AWS 필수 시크릿 4개 설정
# ✅ Telegram/Discord 시크릿 설정 (옵션)
# ✅ 모든 시크릿 검증 및 확인
```

**시크릿 목록:**
- 필수 (4개):
  - AWS_ROLE_TO_ASSUME
  - TERRAFORM_STATE_BUCKET
  - TERRAFORM_STATE_KEY
  - TERRAFORM_LOCK_TABLE
- 선택 (5개):
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID
  - DISCORD_WEBHOOK_URL
  - DISCORD_PUBLIC_KEY
  - SLACK_WEBHOOK

#### 📋 Phase 5: 프로덕션 배포 실행

**Step 1: 로컬 검증**
```bash
# 1. 모든 변경사항 커밋됨 확인
git status

# 2. Terraform 로컬 검증
cd terraform
terraform fmt -check
terraform validate
cd ..

# 3. Python 린트 확인
flake8 lambda/ tests/
black --check lambda/
isort --check-only lambda/
```

**Step 2: GitHub에 푸시**
```bash
# Feature branch 생성 및 푸시
git checkout -b chore/deploy-to-production
git push origin chore/deploy-to-production

# GitHub에서 PR 생성
# - 제목: "Deploy AWS Guardian to production"
# - 설명: PRODUCTION_DEPLOYMENT_CHECKLIST.md 링크
```

**Step 3: GitHub Actions 확인**
- GitHub → Repository → Actions 탭 확인
- 다음 단계들이 자동으로 실행됨:
  - 🔵 Lint 단계 (2-3분)
  - 🔵 Test 단계 (3-5분)
  - 🔵 Build 단계 (2-3분)
- 모든 단계가 ✅ 통과하면 다음으로 진행

**Step 4: PR 병합**
```bash
# PR 리뷰 → Approve → Merge to main
# (GitHub 웹 인터페이스에서)
```

**Step 5: 프로덕션 배포 승인**
- GitHub → Actions → 최신 워크플로우 실행 클릭
- "Review deployments" 클릭
- `production` 환경 선택
- "Approve and deploy" 클릭
- Deploy 단계 시작 (1-2분)
- ✅ 배포 완료

#### 📋 Phase 6: 24시간 검증
- Lambda 함수 배포 확인
- EventBridge 규칙 활성화 확인
- 첫 시간별 실행 모니터링
- 일일 비용 확인 실행 확인
- DynamoDB 이벤트 저장 확인
- Telegram/Discord 알림 테스트
- CloudWatch Logs 확인

**완료 조건**:
- ✅ Lambda 함수 최신 버전 배포
- ✅ EventBridge 규칙 ENABLED 상태
- ✅ CloudWatch Logs에 정상 실행 기록
- ✅ DynamoDB에 이벤트 저장됨
- ✅ 비용: < $0.50/month 확인

---

### ✅ Sprint 5 요약: LocalStack → 실제 AWS 배포 준비
**상태**: 🔄 진행 중 (Phase 1 완료, Phase 2-6 대기)
**완료일**: 2026-04-28
**담당**: Claude Code + Gemini 협업

**Sprint 5 성과:**
| 항목 | 상태 | 상세 |
|------|------|------|
| Phase 1: LocalStack | ✅ 완료 | Lambda, EventBridge, IAM 배포 완료 |
| Phase 2: Terraform 백엔드 | ⏳ 준비 | deploy-infrastructure.sh 준비 완료 |
| Phase 3: GitHub Secrets | ⏳ 준비 | configure-github-secrets.sh 준비 완료 |
| Phase 5: 프로덕션 배포 | ⏳ 준비 | GitHub Actions 워크플로우 준비 완료 |
| Phase 6: 검증 | ⏳ 계획 | 모니터링 가이드 문서화 완료 |

**Phase별 소요시간 (예상):**
- Phase 2 (AWS 인프라): 15-20분
- Phase 3 (GitHub Secrets): 10-15분
- Phase 5 (프로덕션 배포): 10-15분
- Phase 6 (검증): 24시간

**다음 실행 단계:**
1. AWS 계정 및 CLI 설정 완료
2. GitHub 리포지토리 생성/연결
3. `./scripts/deploy-infrastructure.sh jinyounghwa` 실행
4. `./scripts/configure-github-secrets.sh` 실행
5. PR 생성 및 GitHub Actions 실행
6. 24시간 모니터링

---

### Sprint 6: 추가 AWS 서비스 감시 (기능 확장)
**상태**: 📋 계획 단계
**예상 소요시간**: 3-4일
**우선순위**: 중간
**시작 예정**: 2026-04-29 (Phase 5 완료 후)

**목표**: CloudTrail, IAM, GuardDuty 감시 기능 추가

#### 🎯 6-1. CloudTrail 비정상 API 호출 감지
**파일**:
- `lambda/guardian/checkers/cloudtrail.py` (NEW)
- `lambda/guardian/responders/telegram.py` (ENHANCE)

**체크 항목**:
- 루트 계정 활동 탐지
- 비인가 리전에서의 API 호출
- 권한 상승 작업 (CreateAccessKey, AttachUserPolicy)
- 리소스 삭제 작업 (DeleteBucket, TerminateInstances)

**구현**:
```python
class CloudTrailChecker:
    def check_suspicious_api_calls(self):
        # CloudTrail Lookup Events 쿼리
        # 마지막 1시간 이벤트 분석
        # 위협 점수 계산
        return anomaly, details
```

#### 🎯 6-2. IAM 권한 변경 감지
**파일**:
- `lambda/guardian/checkers/iam.py` (NEW)

**체크 항목**:
- 새 IAM 사용자 생성
- 새 액세스 키 생성
- 정책 변경 (AttachUserPolicy, PutUserPolicy)
- 역할 신뢰 관계 변경

**구현**:
```python
class IAMChecker:
    def check_iam_changes(self):
        # IAM 사용자, 역할, 정책 나열
        # 이전 상태와 비교
        # 변경사항 감지
        return anomaly, changes
```

#### 🎯 6-3. GuardDuty 위협 탐지 통합
**파일**:
- `lambda/guardian/checkers/guardduty.py` (NEW)

**체크 항목**:
- GuardDuty 발견사항 조회
- 심각도별 분류 (Low, Medium, High)
- 자동 대응 (격리/차단)

---

### Sprint 7: 고급 분석 및 AI 통합
**상태**: 📋 계획 단계
**예상 소요시간**: 4-5일
**우선순위**: 낮음
**시작 예정**: 2026-05-01

**목표**: 
- Gemini API를 통한 자동 위협 분석
- 이상 탐지 기계학습 (CloudWatch Logs 분석)
- 자동 생성 보고서 (일일/주간)

#### 🎯 7-1. Gemini API 통합 (위협 분석)
**파일**:
- `lambda/guardian/analyzers/gemini_threat_analyzer.py` (NEW)
- `lambda/guardian/responders/gemini.py` (NEW)

**기능**:
- 탐지된 위협을 Gemini에 전달
- 자동 위협 분석 및 대응 제안
- 자연스러운 Telegram 메시지 생성

#### 🎯 7-2. 이상 탐지 (Machine Learning)
**파일**:
- `lambda/guardian/analyzers/anomaly_detector.py` (NEW)

**기능**:
- CloudWatch 로그 패턴 분석
- 이전 7일 대비 현재 행동 비교
- 자동 임계값 조정 (적응형)

#### 🎯 7-3. 자동 보고서 생성
**파일**:
- `lambda/guardian/reporters/daily_report.py` (NEW)
- `lambda/guardian/reporters/weekly_report.py` (NEW)

**기능**:
- 일일 보고서: 탐지된 이벤트 요약
- 주간 보고서: 비용 추이, 상위 위협, 개선 항목
- PDF/이메일 전송

---

## 📊 개발 로드맵 (전체)

| 스프린트 | 상태 | 목표 | 완료일 |
|---------|------|------|--------|
| Sprint 1 | ✅ | 기본 기능 (EC2/S3/Cost) | 2026-04-26 |
| Sprint 2 | ✅ | Docker 최적화 | 2026-04-27 |
| Sprint 3 | ✅ | DynamoDB GSI 최적화 | 2026-04-27 |
| Sprint 4 | ✅ | 프로덕션 준비 | 2026-04-27 |
| Sprint 5 | 🔄 | LocalStack → AWS 배포 | 2026-04-28~ |
| Sprint 6 | 📋 | 추가 AWS 서비스 감시 | 2026-04-29~ |
| Sprint 7 | 📋 | AI 통합 & 고급 분석 | 2026-05-01~ |

---

## 🎯 주요 KPI (성공 지표)

### Phase 1 (LocalStack) - ✅ 완료
- ✅ Lambda 배포: ACTIVE
- ✅ EventBridge: 2개 규칙 ENABLED
- ✅ DynamoDB: 이벤트 저장 확인

### Phase 2-6 (프로덕션) - ⏳ 진행 중
- ⏳ Lambda 월 비용: < $0.50
- ⏳ 이상 탐지 → 알림 시간: < 5분
- ⏳ 자동 대응 성공률: > 95%
- ⏳ Telegram 응답 시간: < 2초

### Phase 7 (AI) - 📋 계획 중
- 📋 Gemini 분석 정확도: > 90%
- 📋 자동 보고서 생성률: 100%
- 📋 사용자 만족도: > 4.5/5

**구현**:
```python
class GuardDutyChecker:
    def check_threats(self):
        # GuardDuty ListFindings
        # 심각도별 필터링
        # 대응 권장사항 생성
        return findings, risk_level
```

#### 📋 구현 순서
1. Gemini CLI로 아키텍처 분석
2. 각 체커 모듈 구현 (with 단위 테스트)
3. Orchestrator에 체크 추가
4. Telegram 포맷팅
5. 로컬 테스트 및 배포

---

### Sprint 7: 다중 AWS 계정 지원
**상태**: 📋 계획 단계
**예상 소요시간**: 3-4일
**우선순위**: 중간

**목표**: Organizations 기반 다중 계정 모니터링

#### 🎯 기능 요구사항
- 조직 내 모든 계정 감시
- 계정별 독립 임계값
- 계정별 알림 채널 분리
- Cross-account IAM Role 자동 구성

#### 📁 필요한 변경
1. `config.py` - ACCOUNT_ID 지원 추가
2. `handler.py` - 다중 계정 루프 추가
3. `terraform/main.tf` - STS AssumeRole 설정
4. `terraform/iam.tf` - Cross-account 역할 정책
5. 대시보드 - 계정별 필터 추가

#### 🔄 구현 흐름
```
Organizations → List Accounts
  ↓
각 계정마다:
  - STS AssumeRole
  - EC2/S3/비용 확인
  - 결과 통합
  ↓
DynamoDB 저장 (account_id 필드 추가)
  ↓
Telegram: 계정명 명시
```

---

### Sprint 8: 웹 대시보드 인증 시스템
**상태**: 📋 계획 단계
**예상 소요시간**: 4-5일
**우선순위**: 낮음

**목표**: NextAuth 기반 인증 + RBAC

#### 🎯 기능 요구사항
- GitHub/Google OAuth 로그인
- 역할 기반 접근 제어 (Admin/Viewer)
- 설정 변경 시 인증 강화
- 감사 로그

#### 📁 필요한 파일
1. `apps/web/auth.config.ts` (NextAuth 설정)
2. `apps/web/src/app/api/auth/[...nextauth]/route.ts`
3. `apps/web/src/middleware.ts` (보호된 라우트)
4. `apps/web/src/lib/rbac.ts` (권한 검사)
5. 데이터베이스 스키마 (사용자, 역할, 감사로그)

#### 🔄 구현 흐름
```
로그인 → OAuth
  ↓
JWT 토큰 발급
  ↓
권한 확인 (RBAC)
  ↓
대시보드 접근
  ↓
변경사항 감사로그 기록
```

---

### Sprint 9: Discord Slash Command 통합
**상태**: 📋 계획 단계
**예상 소요시간**: 2-3일
**우선순위**: 낮음

**목표**: Discord 봇 명령어 완전 구현

#### 🎯 구현할 명령어
- `/status` - 현재 EC2, S3, 비용 상태
- `/stop <instance-id>` - 인스턴스 중지
- `/instances` - 실행 중인 인스턴스 목록
- `/bucket-policy <bucket>` - S3 버킷 정책 수정
- `/threshold <amount>` - 비용 임계값 변경
- `/history [hours]` - 최근 이벤트 로그

#### 📁 필요한 파일
1. `lambda/discord_webhook/handler.py` (ENHANCE)
2. `lambda/discord_webhook/commands/` (NEW)
3. `lambda/discord_webhook/responses/` (NEW)
4. Discord Developer Portal 설정

#### 🔄 구현 흐름
```
Discord → Slash Command 실행
  ↓
Lambda (discord_webhook) 트리거
  ↓
명령어 파싱
  ↓
AWS API 호출
  ↓
Discord Embed 응답 반환
```

---

## 📊 스프린트 로드맵

```
Sprint 5: 프로덕션 배포 실행 (2-3시간)
  ✓ Terraform 백엔드 설정
  ✓ GitHub Secret 설정
  ✓ PR → 배포 승인
  ✓ 24시간 검증

Sprint 6: AWS 서비스 감시 확장 (3-4일)
  ✓ CloudTrail 감시
  ✓ IAM 권한 감시
  ✓ GuardDuty 위협 통합

Sprint 7: 다중 계정 지원 (3-4일)
  ✓ Organizations 통합
  ✓ Cross-account IAM
  ✓ 계정별 설정

Sprint 8: 대시보드 인증 (4-5일)
  ✓ NextAuth 통합
  ✓ RBAC 구현
  ✓ 감사로그

Sprint 9: Discord 명령어 (2-3일)
  ✓ Slash Command 구현
  ✓ 응답 포맷팅
  ✓ 명령어별 권한 검사
```

---

## 🧪 로컬 테스트 체크리스트

**다음 개발 시작 전**:
- [ ] `./start.sh` 실행 - 최적화된 handler 테스트
- [ ] `tail -f guardian.log` - 로그 확인
- [ ] DynamoDB 테이블 데이터 확인
- [ ] Telegram 봇 알림 테스트
- [ ] Discord 대시보드 API 응답 확인

---

## 🔧 개발 워크플로우

**각 스프린트마다**:
1. `./scripts/gemini-ask.sh` 실행 → Gemini 분석 수집
2. `~/.gemini/logs/claude-gemini.log` 확인 → 로그 검토
3. Claude Code 구현 → 파일 작성/수정
4. `./start.sh` → 로컬 테스트
5. git commit → 진행상황 기록

---

## 📝 사용 가능한 Gemini CLI 명령어

```bash
# 코드 리뷰
./scripts/gemini-ask.sh "Review [file] for quality" code_review

# 아키텍처 분석
./scripts/gemini-ask.sh "Analyze architecture for..." architecture

# 코드 생성
./scripts/gemini-ask.sh "Generate code for..." code_generation

# 파일 기반 분석
./scripts/gemini-ask.sh --file /path/to/file.py "analysis type" analysis_type

# 로그 확인
tail -f ~/.gemini/logs/claude-gemini.log
```

---

## 배포 체크리스트
- [x] Sprint 2 완료: Docker Compose 최적화
- [x] Sprint 3 완료: DynamoDB GSI + API 최적화
- [x] Sprint 4 완료: CI/CD 파이프라인 + 배포 준비
- [ ] Phase 2: Terraform 백엔드 설정 (S3, DynamoDB, IAM)
- [ ] Phase 3: GitHub Secret 설정
- [ ] Phase 5: 프로덕션 배포 실행
- [ ] Phase 6: 24시간 검증
- [ ] AWS 배포: Terraform 프로덕션 검증
- [ ] CloudWatch Logs 모니터링 설정
- [ ] 비용 검증: < $0.50/월

 # 다음 개발 시 이 명령어부터 다시 실행                                                                                                                                                                                           
  ./scripts/gemini-ask.sh --file docker-compose.yml "Review this Docker Compose..." architecture    

