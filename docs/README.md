# AWS Guardian Documentation

> 완전한 AWS 감시 및 보안 시스템 문서

---

## 📚 Documentation Index

### 🚀 Getting Started
- **[CLAUDE.md](../CLAUDE.md)** - 프로젝트 지침 및 구조
- **[NEXT_SESSION_GUIDE](NEXT_SESSION_GUIDE.md)** - 다음 세션 가이드

### 📖 Guides

#### Deployment & Infrastructure
- **[Basic Deployment](guides/BASIC_DEPLOYMENT.md)** - 기본 배포 가이드
- **[Docker Deployment](guides/DOCKER_DEPLOYMENT.md)** - Docker Compose 설정 및 배포
- **[Production Deployment](guides/PRODUCTION_DEPLOYMENT.md)** - 프로덕션 배포 체크리스트

#### Development
- **[Local Development](guides/LOCAL_DEVELOPMENT.md)** - 로컬 개발 환경 설정
- **[CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md)** - CloudWatch 메트릭 및 대시보드

### 🏗️ Architecture & Design
- **[System Architecture](ARCHITECTURE.md)** - 전체 시스템 아키텍처
- **[Checker Catalog](CHECKER_CATALOG.md)** - 8개 보안/비용 체커 전체 참조
- **[Performance Guide](PERFORMANCE.md)** - 성능 최적화 및 벤치마크
- **[Contributing](CONTRIBUTING.md)** - 기여 가이드

### 📝 Sprint Documentation
- **[Sprint 계획 및 완료 보고서](sprints/)** - Sprint 3 ~ Sprint 80
- **[docs/ 루트의 Sprint 문서들](.)** - Sprint 47 ~ Sprint 80 계획/완료 보고서

---

## 🎯 Quick Links

### By Task
| 작업 | 문서 |
|------|------|
| 새로운 개발자 온보딩 | [Local Development](guides/LOCAL_DEVELOPMENT.md) |
| 프로덕션 배포 | [Production Deployment](guides/PRODUCTION_DEPLOYMENT.md) |
| CloudWatch 모니터링 설정 | [CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md) |
| Docker 배포 | [Docker Deployment](guides/DOCKER_DEPLOYMENT.md) |
| 새 체커 추가 | [Contributing](CONTRIBUTING.md) |
| 체커별 상세 정보 | [Checker Catalog](CHECKER_CATALOG.md) |

---

## 📊 Project Overview

| 항목 | 내용 |
|------|------|
| 🎯 목표 | AWS 계정을 자동으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응 |
| 🔨 기술 스택 | Python 3.12 (Lambda), AWS Lambda, DynamoDB, EventBridge, Terraform/SAM |
| 📍 배포 | AWS Lambda (서버리스) + LocalStack (로컬 개발/테스트) |
| 🧪 테스트 | **2392 수집, 2327 통과, 4 실패, 61 스킵, 2 수집 에러** (2026-05-30 기준) |
| 📁 소스 코드 | lambda/guardian/ 내 274개 Python 파일 (약 64,700줄) |
| 📁 테스트 코드 | tests/ 내 199개 테스트 파일 (약 52,600줄) |
| 💰 비용 | 설계 목표 < $0.50/월 (AWS 무료 티어 활용, 실제 배포 시 검증 필요) |

---

## ⚠️ 프로젝트 상태 (정직한 평가)

**현재 상태**: 개발 진행 중 (Sprint 80 진행)

### 완료된 것
- ✅ 8개 AWS 보안/비용 체커 (EC2, S3, Cost, IAM, CloudTrail, GuardDuty, RDS, IAMPolicyAnalyzer)
- ✅ Lambda 핸들러 + 오케스트레이터 (순차/병렬)
- ✅ Telegram/Discord/Slack 알림
- ✅ DynamoDB 저장
- ✅ Terraform + SAM 인프라 코드
- ✅ LocalStack 로컬 개발 환경
- ✅ 2392개 테스트 (2327 통과)
- ✅ 다양한 ML/분석/자동화 모듈
- ✅ K8s 위협 탐지 모듈 (Phase 1)

### 미해결/주의 사항
- ⚠️ **4개 테스트 실패** 중 (CI 파이프라인, 멀티 어카운트 매니저)
- ⚠️ **2개 테스트 수집 에러** (AWS 통합, Cost Optimizer 모듈 누락)
- ⚠️ **프로덕션 배포 검증 없음** - LocalStack 환경에서만 테스트됨
- ⚠️ **ML 정확도 92%** - 근거 불명확 (검증된 벤치마크 없음)
- ⚠️ **성능 개선 수치** (3배, 10배 등) - 실 AWS 환경에서 검증되지 않음
- ⚠️ 웹 대시보드 (apps/web) - 코드는 존재하나 독립 실행 검증 필요

---

## 🔗 Related Files

- **Main Project Instructions**: [CLAUDE.md](../CLAUDE.md)
- **Lambda Source**: `/lambda/guardian/`
- **Web Dashboard**: `/apps/web/`
- **Infrastructure**: `/terraform/`, `/sam.yaml`
- **Tests**: `/tests/`

---

## 🆘 How to Use This Documentation

1. **처음 시작하는 경우**: [Local Development](guides/LOCAL_DEPLOYMENT.md) → [CLAUDE.md](../CLAUDE.md)
2. **프로덕션 배포 필요**: [Production Deployment](guides/PRODUCTION_DEPLOYMENT.md) 참조
3. **모니터링 설정**: [CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md) 참조
4. **아키텍처 이해**: [ARCHITECTURE.md](ARCHITECTURE.md) 참조
5. **체커 상세 정보**: [CHECKER_CATALOG.md](CHECKER_CATALOG.md) 참조
6. **기여 방법**: [CONTRIBUTING.md](CONTRIBUTING.md) 참조

---

**Last Updated**: 2026-05-30
