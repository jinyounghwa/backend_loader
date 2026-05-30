# AWS Guardian - 프로젝트 현재 상태

**기준일:** 2026-05-30  
**상태:** 개발 진행 중 (Sprint 80)

---

## 📊 실제 측정 통계 (2026-05-30 기준)

### 테스트
| 항목 | 값 |
|------|-----|
| 수집된 테스트 | 2,414 |
| 통과 | 2,353 |
| 실패 | 0 |
| 스킵 | 61 |
| 수집 에러 | 0 |
| 테스트 파일 수 | 199 |
| 테스트 코드 줄 수 | ~52,600 |

### 소스 코드
| 항목 | 값 |
|------|-----|
| lambda/guardian Python 파일 | 274개 |
| lambda/guardian 코드 줄 수 | ~64,700 |
| 주요 모듈 디렉토리 | 40+ (checkers, responders, storage, ml, analytics, engines, handlers 등) |

### 인프라
| 항목 | 값 |
|------|-----|
| 배포 도구 | Terraform + SAM |
| 로컬 개발 | LocalStack (docker-compose) |
| Lambda 핸들러 | guardian/handler.py (lazy init 패턴) |
| 체커 | 8개 (EC2, S3, Cost, IAM, CloudTrail, GuardDuty, RDS, IAMPolicyAnalyzer) |

### 프론트엔드
| 항목 | 값 |
|------|-----|
| 프레임워크 | Next.js 16.2.4 + React 19.2.4 |
| UI | Tailwind CSS, Lucide Icons, Recharts |
| 상태 | 코드 존재, 독립 실행 검증 필요 |

---

## 🏗️ 실제 아키텍처

```
AWS EventBridge (hourly)
    ↓
Lambda: guardian/handler.lambda_handler()
    ↓ (_LazyOrchestrator 패턴)
┌─────────────────────────────────────────┐
│  Orchestrator (Sequential or Parallel)  │
├─────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐     │
│ │ EC2Checker   │  │ S3Checker    │     │
│ ├──────────────┤  ├──────────────┤     │
│ │ CostChecker  │  │ IAMChecker   │     │
│ ├──────────────┤  ├──────────────┤     │
│ │ CloudTrail   │  │ GuardDuty    │     │
│ ├──────────────┤  ├──────────────┤     │
│ │ RDSChecker   │  │ IAMPolicy    │     │
│ └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────┘
    ↓
┌──────────────┐  ┌──────────────┐
│ Responders   │  │ Remediation  │
├──────────────┤  ├──────────────┤
│ Telegram     │  │ EC2 Stop     │
│ Discord      │  │ S3 Block     │
│ Slack        │  │ Auto-remed.  │
└──────────────┘  └──────────────┘
    ↓
DynamoDB: Audit Log + Remediation Metrics
```

---

## ⚠️ 정직한 평가

### 잘 된 것
- ✅ 모듈식 체커 아키텍처 (BaseChecker 패턴)
- ✅ 8개 AWS 서비스 모니터링
- ✅ 순차 + 병렬 오케스트레이터
- ✅ 다양한 알림 채널 (Telegram, Discord, Slack, Teams)
- ✅ LocalStack 기반 로컬 개발 환경
- ✅ 방대한 테스트 스위트 (2,392 테스트)
- ✅ ML/분석/자동화 모듈 다수 구현
- ✅ Terraform + SAM 인프라 코드

### 미해결 문제
- ✅ **테스트 실패 해결**: 모든 유닛 테스트가 성공적으로 통과함 (0개 실패)
- ✅ **수집 에러 해결**: `test_aws_integration.py` 및 `test_cost_optimizer.py`에서 누락되었던 클래스들을 익스포트 및 복원하여 수집 오류를 해결함
- ⚠️ **프로덕션 배포 미검증**: LocalStack 환경에서만 테스트, 실제 AWS 배포 및 실행 기록 없음
- ⚠️ **성능 수치 미검증**: 문서에 기재된 "3배 개선", "10배 개선", "92% ML 정확도" 등은 실 AWS 환경에서 검증되지 않음
- ⚠️ **과도한 모듈 생성**: 일부 모듈은 실질적으로 비슷한 기능을 중복 구현 (예: cost_analyzer.py가 analyzers/와 analytics/에 각각 존재)
- ⚠️ **문서 불일치**: 여러 문서에서 버전(v1.0, v1.4, v2.9, v3.0)과 스프린트 번호가 충돌

### 검증되지 않은 주장들
아래 주장들은 코드가 존재하나, 실제 프로덕션 환경에서 검증되지 않았습니다:
- "ML 정확도 92%" → 검증된 벤치마크 데이터셋 없음
- "비용 < $0.50/월" → 실제 AWS 청구 데이터 없음
- "Lambda 실행 0.43초" → 실 AWS 환경 측정 기록 없음
- "PRODUCTION READY" → 프로덕션 배포 이력 없음
- "AWS Marketplace 등록 가능" → 등록 절차 진행 없음

---

## 📋 Sprint 이력

| Sprint 범위 | 위치 | 비고 |
|-------------|------|------|
| Sprint 3-46 | docs/sprints/ | 초기 ~ 중기 개발 |
| Sprint 47-80 | docs/ (루트) | 후기 개발 |

> **참고**: Sprint 번호가 불연속적입니다. 일부 Sprint는 계획만 있고 완료 보고서가 없습니다.

---

## 🚀 다음 단계 (권장)

1. **실패하는 테스트 수정** (4개 실패 + 2개 수집 에러)
2. **중복 모듈 정리** (동일 기능의 여러 구현 통합)
3. **실 AWS 환경 배포 테스트**
4. **성능 벤치마크** (실 AWS API 호출 기반)
5. **문서 일관성 정리** (버전 번호, 스프린트 번호 통일)

---

**Last Updated**: 2026-05-30
