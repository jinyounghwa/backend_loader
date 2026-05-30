# AWS Guardian: 프로젝트 현황 보고서

**기준일:** 2026-05-30  
**상태:** 개발 진행 중

---

## 📊 프로젝트 개요

AWS 계정을 자동으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응으로 제어하는 **서버리스 보안/비용 감시 시스템**

### 슬로건
> "잠자는 동안에도 AWS를 지킨다"

---

## 🎯 구현된 기능

### 핵심 감시 (v1.0 범위)
- ✅ EC2 인스턴스 보안 감시
- ✅ S3 버킷 공개 접근 감지
- ✅ 비용 이상 탐지
- ✅ IAM 권한 분석
- ✅ CloudTrail 로깅 상태 확인
- ✅ GuardDuty 활성화 상태 확인
- ✅ RDS 보안 설정 감사
- ✅ IAM 인라인 정책 위험 분석

### 알림 및 대응
- ✅ Telegram Bot 알림
- ✅ Discord Webhook 알림
- ✅ Slack Webhook 알림
- ✅ Teams 알림
- ✅ EC2 자동 중지
- ✅ S3 퍼블릭 차단
- ✅ 자동 치료 (Auto-remediation)

### 인프라
- ✅ Terraform 인프라 코드 (LocalStack 지원)
- ✅ SAM 템플릿 (sam.yaml)
- ✅ Docker Compose (로컬 개발)
- ✅ EventBridge 스케줄 트리거
- ✅ DynamoDB 상태 저장

### 확장 기능
- ✅ ML 기반 이상 탐지 모듈들
- ✅ 비용 예측/분석 모듈들
- ✅ 위협 상관관계 분석
- ✅ 인시던트 플레이북
- ✅ 다중 계정 관리
- ✅ 실시간 WebSocket 알림
- ✅ K8s 위협 탐지 (Phase 1)
- ✅ Next.js 웹 대시보드 (코드 존재)

---

## 📈 실제 코드 통계 (2026-05-30 기준)

| 항목 | 수치 | 비고 |
|------|------|------|
| lambda/guardian Python 파일 | 274개 | __init__.py 제외 |
| lambda/guardian 코드 줄 수 | ~64,700 | |
| 테스트 파일 수 | 199개 | |
| 테스트 코드 줄 수 | ~52,600 | |
| 수집된 테스트 | 2,392개 | |
| 통과한 테스트 | 2,327개 | |
| 실패한 테스트 | 4개 | |
| 스킵된 테스트 | 61개 | |
| 수집 에러 | 2개 | |
| 주요 모듈 디렉토리 | 40+ | |

---

## 🏗️ 실제 아키텍처

```
┌─────────────────────────────────────────────────┐
│         AWS Guardian System                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  Compute Layer:                                 │
│  ├─ AWS Lambda (Python 3.12)                   │
│  │  ├─ guardian/handler.py (LazyOrchestrator)  │
│  │  ├─ 8개 체커 (BaseChecker 상속)             │
│  │  ├─ 병렬/순차 오케스트레이터               │
│  │  └─ 다수의 ML/분석 모듈                     │
│  │                                              │
│  Frontend Layer:                                │
│  ├─ Next.js 16 + React 19 웹 대시보드          │
│  │  ├─ /apps/web (코드 존재)                   │
│  │  └─ Tailwind CSS, Recharts                  │
│  │                                              │
│  Data Layer:                                    │
│  ├─ DynamoDB (상태/감사 로그)                   │
│  ├─ Redis (선택적 분산 캐시)                    │
│  └─ S3 (보관)                                   │
│                                                 │
│  Infrastructure:                                │
│  ├─ Terraform (main.tf, lambda.tf 등)          │
│  ├─ SAM (sam.yaml)                             │
│  └─ Docker Compose + LocalStack                │
│                                                 │
│  Notification:                                  │
│  ├─ Telegram Bot                               │
│  ├─ Discord Webhook                            │
│  ├─ Slack Webhook                              │
│  └─ Teams Webhook                              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 📦 실제 구현 컴포넌트

### Lambda Core (lambda/guardian/)
- `handler.py`: Lambda 엔트리포인트 (lazy initialization)
- `orchestrator.py`: 순차 오케스트레이터
- `parallel_orchestrator.py`: 병렬 오케스트레이터
- `config.py`: 설정 관리

### 8개 체커 (lambda/guardian/checkers/)
- `ec2.py`: EC2 인스턴스 보안
- `s3.py`: S3 버킷 권한
- `cost.py`: 비용 이상 탐지
- `iam.py`: IAM 사용자 분석
- `cloudtrail.py`: CloudTrail 상태
- `guardduty.py`: GuardDuty 활성화
- `rds.py`: RDS 보안 설정
- `iam_policy_analyzer.py`: IAM 정책 위험 분석

### 응답기 (lambda/guardian/responders/)
- `telegram.py`: Telegram 알림
- `discord.py`: Discord 알림
- `slack_responder.py`: Slack 알림
- `teams_responder.py`: Teams 알림
- `auto_remediation.py`: 자동 치료
- `remediation_service.py`: 치료 서비스

### 저장소 (lambda/guardian/storage/)
- `dynamodb.py`: DynamoDB 저장
- `redis.py`: Redis 캐시 (선택)
- `memory.py`: 인메모리 캐시

### ML/분석 모듈
- `ml/`: 이상 탐지, 앙상블, 예측 모델 등
- `analytics/`: 비용 분석, 트렌드 분석 등
- `detectors/`: 이상 감지, 공격 체인 탐지 등
- `engines/`: 위협 상관, 스마트 치료 엔진 등

---

## 🛠️ 기술 스택

| 레이어 | 기술 |
|--------|------|
| **런타임** | Python 3.12 (Lambda) |
| **프레임워크** | SAM, Terraform |
| **프론트엔드** | Next.js 16, React 19, Tailwind CSS |
| **데이터베이스** | DynamoDB, Redis (선택) |
| **로컬 개발** | LocalStack, Docker Compose |
| **알림** | Telegram, Discord, Slack, Teams |

---

## ⚠️ 알려진 제한사항

1. **프로덕션 미검증**: 모든 테스트가 LocalStack/mock 기반. 실제 AWS 환경에서 종합 테스트 필요
2. **테스트 실패**: 4개 테스트 실패 + 2개 수집 에러 존재
3. **중복 모듈**: 일부 기능이 여러 위치에 중복 구현됨 (예: cost_analyzer.py)
4. **ML 정확도 미검증**: "92% 정확도" 주장에 대한 객관적 벤치마크 없음
5. **성능 수치 미검증**: "3배 개선", "10배 개선" 등은 mock 환경 기준, 실 AWS에서 검증 필요
6. **비용 추정 미검증**: "$0.50/월" 등의 비용 추정은 실 청구 데이터 기반이 아님

---

## 📚 문서

- ✅ [CLAUDE.md](../CLAUDE.md) - 프로젝트 지침
- ✅ [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처
- ✅ [CHECKER_CATALOG.md](CHECKER_CATALOG.md) - 체커 카탈로그
- ✅ [PERFORMANCE.md](PERFORMANCE.md) - 성능 가이드
- ✅ [CONTRIBUTING.md](CONTRIBUTING.md) - 기여 가이드
- ✅ Sprint 계획/완료 보고서 (Sprint 3 ~ 80)

---

## 🔮 향후 권장 사항

### 필수 (프로덕션 전)
1. 실패 테스트 수정
2. 수집 에러 해결 (누락 모듈)
3. 실 AWS 환경 배포 및 E2E 테스트
4. 중복 모듈 정리
5. 문서 버전/스프린트 번호 일관성 확보

### 권장
1. 실 AWS 환경에서 성능 벤치마크 수행
2. ML 모델 정확도 객관적 검증
3. 비용 추정을 실제 청구 데이터로 검증
4. E2E 테스트 자동화
5. CI/CD 파이프라인 구축

---

**기준일**: 2026-05-30  
**프로젝트 상태**: 개발 진행 중
