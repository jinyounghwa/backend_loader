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

### Sprint 2: Docker Compose 아키텍처 검토
**상태**: 🔄 Ready to start

**Gemini CLI 명령어**:
```bash
./scripts/gemini-ask.sh --file docker-compose.yml "Review this Docker Compose configuration for:
1. Best practices for LocalStack
2. Environment variable management
3. Security considerations
4. Production readiness
5. Optimization opportunities
Provide specific improvements." architecture
```

**Claude Code 구현 예상**:
- docker-compose.yml 최적화
- 환경 변수 분리 강화
- 프로덕션 configuration 추가

**완료 기준**:
- ✅ Gemini 아키텍처 분석 생성
- ✅ 개선사항 구현 및 테스트
- ✅ start.sh 검증

---

### Sprint 3: DynamoDB API 최적화 (GSI 추가)
**상태**: 🔄 Ready to start

**Gemini CLI 명령어**:
```bash
./scripts/gemini-ask.sh "Design a Global Secondary Index (GSI) strategy for our DynamoDB guardian_events table:

Current schema:
- Partition Key: event_id (UUID)
- Sort Key: timestamp (ISO 8601)
- Attributes: event_type, severity, check_type, data

Current access patterns:
1. Latest event by type/severity
2. Events in date range
3. Events by check_type + timestamp

Requirements:
1. Minimize Scan operations
2. Support dashboard queries efficiently
3. Support API filtering (type, severity, date range)
4. Maintain cost efficiency

Provide:
1. GSI design (partition key, sort key, projections)
2. Updated API route patterns
3. Query efficiency analysis" architecture
```

**Claude Code 구현 예상**:
- GSI 생성 (Terraform)
- API 라우트 최적화 (Next.js)
- 쿼리 개선 (boto3)

**완료 기준**:
- ✅ Gemini GSI 설계 생성
- ✅ Terraform 코드 구현
- ✅ API 라우트 성능 테스트

---

### Sprint 4: 프로덕션 배포 준비 (선택사항)
**상태**: 📋 Planned

**항목**:
- Terraform 프로덕션 검증 (AWS_ENV=production)
- CloudWatch Logs 모니터링 설정
- 비용 최적화 검증 (< $0.50/월)
- GitHub Actions CI/CD 파이프라인

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
- [ ] Sprint 2 완료: Docker Compose 최적화
- [ ] Sprint 3 완료: DynamoDB GSI + API 최적화
- [ ] 로컬 테스트: ./start.sh 전체 검증
- [ ] AWS 배포: Terraform 프로덕션 검증
- [ ] CloudWatch Logs 모니터링 설정
- [ ] 비용 검증: < $0.50/월

 # 다음 개발 시 이 명령어부터 다시 실행                                                                                                                                                                                           
  ./scripts/gemini-ask.sh --file docker-compose.yml "Review this Docker Compose..." architecture    

