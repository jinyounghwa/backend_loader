# AWS Guardian - v2.10

> **"잠자는 동안에도 AWS를 지킨다"**

**여러 AWS 계정**을 자동으로 감시하고 위협 탐지 시 텔레그램 알림, 자동 대응, 디스코드 대시보드 제어를 제공하는 서버리스 보안 및 비용 감시 시스템입니다.

**상태:** 🛠️ **개발 진행 중** | **테스트:** ✅ **2,372 통과 / 61 스킵 / 0 실패 (2,433 수집)** | **버전:** 개발 버전

> ⚠️ **범위 안내:** **모바일 앱(iOS/Android)** 과 **쿠버네티스/컨테이너 보안**은 **진행하지 않기로 결정된 비범위 항목**입니다. 관련 잔존 코드/스캐폴드는 평가·완성도 산정에서 제외합니다. 자세한 내용은 [스프린트 문서 종합 평가](docs/SPRINT_DOCS_COMPREHENSIVE_REVIEW.md)를 참고하세요.

## 빠른 시작

로컬 개발 환경에서 LocalStack을 사용하여 즉시 시작할 수 있습니다.

```bash
# 1. 저장소 클론 및 이동
cd backend_loader

# 2. 원클릭 시작 스크립트 실행 (Docker 필요)
chmod +x start.sh
./start.sh
```

스크립트는 LocalStack 컨테이너 실행, 리소스 초기화, 프론트엔드 대시보드 기동을 자동으로 처리합니다.

## 사전 요구사항

- Docker 및 Docker Compose
- Python 3.9 이상
- 텔레그램 봇 (선택 사항, 알림 수신용)
- AWS CLI (배포용)

## 아키텍처

```
[LocalStack / AWS 허브 계정]
       ↓
[EventBridge (1시간 주기)]
       ↓
[Guardian Lambda] ── sts:AssumeRole ──→ [멤버 계정 A, B, ...]
    ├── Cost Checker (계정별)
    ├── EC2 Checker (계정별)
    └── S3 Checker (계정별)
       ↓
[Telegram / Discord Webhook (계정 표기)]
       ↓
[Next.js Dashboard (apps/web)]
```

멀티 계정 구성은 [멀티 계정 감시 가이드](docs/MULTI_ACCOUNT_GUIDE.md)를 참고하세요.
`GUARDIAN_ACCOUNTS` 환경변수로 수동 등록하거나 AWS Organizations 자동 탐색을 사용할 수 있으며,
멤버 계정에는 동봉된 [CloudFormation 역할 템플릿](docs/templates/guardian-member-role.yaml) 하나만 배포하면 됩니다.

## 🎯 핵심 기능 (70+)

### 보안 & 탐지
✅ CloudTrail 분석 | ✅ IAM 이상 탐지 | ✅ GuardDuty 통합  
✅ EC2/S3 위협 모니터링 | ✅ 실시간 경고 | ✅ RDS 보안 감사  
✅ **멀티 계정 감시** (수동 등록 / Organizations 자동 탐색, ExternalId 지원)

### 지능형 분석
✅ 고급 위협 프로파일링 | ✅ ML 이상 탐지 (5+ 알고리즘)  
✅ 비용 예측 (ARIMA + Prophet) | ✅ 위협 사냥 (행동 분석)  
✅ 패턴 인식 & 공격 체인 | ✅ 실시간 이벤트 상관관계

### 자동화된 대응
✅ 인시던트 플레이북 (5+ 템플릿) | ✅ 조건부 응답 실행  
✅ 병렬 워크플로우 오케스트레이션 | ✅ 피드백 기반 최적화 | ✅ 롤백 지원

### 시각화 & 보고
✅ 실시간 대시보드 | ✅ 다중 시리즈 차팅  
✅ 커스텀 보고서 빌더 (50+ 템플릿) | ✅ 다중 형식 내보내기 (PDF, Excel, JSON)  
✅ 예약 보고서

### 엔터프라이즈
✅ 규정 준수 검증 (SOC2/PCI-DSS/HIPAA) | ✅ 디지털 서명 & 감사 추적  
✅ 고급 필터링 & 검색 | ✅ 성능 메트릭 & KPI 추적 | ✅ 추세 분석 & 예측

## 📊 프로젝트 통계

| 항목 | 수치 | 상태 |
|------|------|------|
| **테스트** | 2,372 통과 / 61 스킵 / 0 실패 (2,433 수집) | ✅ PASS |
| **스프린트** | Sprint 1~79 완료 (메인 시리즈) | ✅ DONE |
| **기능** | 70+ | ✅ IMPLEMENTED |
| **모듈** | 40+ | ✅ BUILT |
| **코드량** | ~64,700 LOC | ✅ CLEAN |
| **버전** | 개발 버전 | 🛠️ DEVELOPMENT |
| **비범위(제외)** | 모바일(iOS/Android), 쿠버네티스 | 🚫 OUT OF SCOPE |

## 기술 스택

| 구분 | 기술 |
|------|------|
| 실행 환경 | AWS Lambda (Python 3.12) |
| 로컬 환경 | LocalStack |
| 인프라 관리 | Terraform / SAM |
| 프론트엔드 | Next.js (apps/web) |
| 데이터베이스 | DynamoDB |
| 설정 관리 | SSM Parameter Store |
| 알림 채널 | Telegram, Discord |
| ML/AI | ARIMA, Prophet, Isolation Forest, LOF |
| 실시간 | WebSocket Streaming |

## 로컬 테스트

LocalStack 모드에서는 실제 AWS 비용이 발생하지 않습니다.

```bash
# 환경 변수 설정 (기본값: localstack)
export AWS_ENV=localstack

# 테스트 실행
python3 -m pytest tests/
```

## 상용 AWS 배포

상용 환경에 배포하려면 `AWS_ENV`를 `production`으로 설정해야 합니다.

```bash
# 환경 변수 변경
export AWS_ENV=production

# Terraform 배포
cd terraform
terraform init
terraform apply
```

상세한 배포 방법은 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)를,
여러 계정을 한 번에 감시하는 구성은 [멀티 계정 감시 가이드](docs/MULTI_ACCOUNT_GUIDE.md)를 참고하세요.

## 📚 문서

| 문서 | 설명 |
|------|------|
| [MULTI_ACCOUNT_GUIDE.md](docs/MULTI_ACCOUNT_GUIDE.md) | **🏢 멀티 계정 감시 가이드 (등록부터 사용까지)** |
| [SPRINT_DOCS_COMPREHENSIVE_REVIEW.md](docs/SPRINT_DOCS_COMPREHENSIVE_REVIEW.md) | **🧭 스프린트 문서 종합 평가 (범위·제외 항목 포함)** |
| [SECURITY_REVIEW_2026-06-01.md](docs/SECURITY_REVIEW_2026-06-01.md) | **🔒 보안 검토 및 리팩토링 보고서** |
| [FINAL_COMPLETION.md](docs/FINAL_COMPLETION.md) | 📋 프로젝트 현재 상태 |
| [SPRINT_*_PLAN/COMPLETION.md](docs) | Sprint 계획서·완료 문서 모음 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | AWS 배포 가이드 |
| [CLAUDE.md](CLAUDE.md) | 프로젝트 지침 및 아키텍처 |

## 🚀 배포 현황

### Sprint 진행 현황

| Sprint | 포커스 | 테스트 | 누적 | 상태 |
|--------|--------|--------|------|------|
| 73 | 기초 구축 | 72 | 72 | ✅ |
| 74 | 다중 서비스 | 69 | 141 | ✅ |
| 75 | 실시간 & ML | 83 | 224 | ✅ |
| 76 | 고급 분석 | 60 | 284 | ✅ |
| 77 | AI & 오케스트레이션 | 63 | 347 | ✅ |
| 78 | 최종 앙상블 | 16 | 363 | ✅ |
| 79 | 대시보드 & 시각화 | 64 | 427 | ✅ |

> Sprint 80(쿠버네티스/컨테이너)은 **진행하지 않기로 결정**되어 메인 진행 현황에서 제외합니다.

### 버전 히스토리

- **v1.0** - 기본 감시 시스템
- **v1.1** - Lambda 테스트 하네스
- **v1.2** - SAM CLI 통합
- **v2.0** - 고급 위협 탐지 & 자동 대응
- **v2.5** - 실시간 대시보드 & ML 앙상블
- **v2.7** - AI 위협 사냥 & 응답 오케스트레이션
- **v2.8** - 최종 앙상블 & 실시간 업데이트
- **v2.9** - 고급 대시보드 & 시각화
- **v2.10** - 보안/유지보수 리팩토링 & 멀티 계정 감시 ✅ **CURRENT**

> 모바일(iOS/Android)과 쿠버네티스(v3.0 프리뷰)는 진행하지 않기로 결정되어 로드맵에서 제외되었습니다.

## 📈 성능 메트릭

- ✅ **테스트:** 2,372 통과 / 61 스킵 / 0 실패 (2,433 수집)
- ✅ **코드 품질:** `guardian.*` 단일 import 규약, sys.path 핵 제거, 일관된 패턴
- ✅ **보안:** HTML 인젝션 방어, SSM 시크릿 관리, 서명·권한 검증, 최소권한 IAM(terraform·SAM 일치) ([보안 보고서](docs/SECURITY_REVIEW_2026-06-01.md))
- ✅ **성능:** WebSocket 실시간 스트리밍, <3초 응답 시간

## 🛠️ 개발 환경 설정

### 전제 조건
```bash
# Python 3.9+ 필요
python3 --version

# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
pytest tests/backend -v
```

### 디렉토리 구조

```
backend_loader/
├── lambda/guardian/           # Lambda 함수 코드
│   ├── checkers/              # 위협 탐지 모듈
│   ├── responders/            # 자동 대응 모듈
│   ├── ml/                    # ML/AI 엔진
│   ├── hunting/               # 위협 사냥 엔진
│   ├── dashboards/            # 대시보드 모듈
│   ├── visualization/         # 시각화 엔진
│   └── ...
├── tests/                     # 테스트 스위트 (2,417 수집)
├── terraform/                 # 인프라 코드
├── docs/                      # 문서
│   ├── FINAL_COMPLETION.md    # 최종 완료 현황
│   └── SPRINT_*_PLAN.md       # Sprint 계획서
└── README.md                  # 이 파일
```

## 📞 문의 및 지원

프로덕션 배포, 커스터마이제이션, 또는 추가 기능에 대한 질문:
- 📧 Email: timotolkie@gmail.com
- 📖 Docs: 전체 문서는 `/docs` 디렉토리 참고

## 라이선스

MIT License

---

**최종 갱신:** 2026-07-04  
**상태:** 🛠️ 개발 진행 중 · 2,372 테스트 통과 · 보안 리팩토링 & 멀티 계정 감시 추가  
**범위:** 서버리스 보안/비용 감시 백엔드 + 웹 대시보드 (모바일·쿠버네티스 제외)
