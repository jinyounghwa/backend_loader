# AWS Guardian Documentation

> 완전한 AWS 감시 및 보안 시스템 문서

---

## 📚 Documentation Index

### 🚀 Getting Started
- **[README](../README.md)** - 프로젝트 개요
- **[CLAUDE.md](../CLAUDE.md)** - 프로젝트 지침 및 구조
- **[NEXT_STEPS.md](../NEXT_STEPS.md)** - 진행상황 및 로드맵 (⭐ 최신)

### 📖 Guides

#### Deployment & Infrastructure
- **[Basic Deployment](guides/BASIC_DEPLOYMENT.md)** - 기본 배포 가이드
- **[Docker Deployment](guides/DOCKER_DEPLOYMENT.md)** - Docker Compose 설정 및 배포
- **[Production Deployment](guides/PRODUCTION_DEPLOYMENT.md)** - 프로덕션 배포 체크리스트

#### Development
- **[Local Development](guides/LOCAL_DEVELOPMENT.md)** - 로컬 개발 환경 설정
- **[CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md)** - CloudWatch 메트릭 및 대시보드
- **[Agentic Workflow](guides/AGENTIC_WORKFLOW.md)** - Gemini 협업 워크플로우

### 🏗️ Architecture
- **[Gemini Collaboration](architecture/GEMINI_COLLABORATION.md)** - Gemini AI 통합 구조
- **[System Architecture](../CLAUDE.md)** - 전체 시스템 구조 (CLAUDE.md 참조)

### 📝 Sprint Documentation
각 스프린트의 완료 현황을 **[NEXT_STEPS.md](../NEXT_STEPS.md)**에서 확인할 수 있습니다.

---

## 🎯 Quick Links

### By Task
| 작업 | 문서 |
|------|------|
| 새로운 개발자 온보딩 | [Local Development](guides/LOCAL_DEVELOPMENT.md) |
| 프로덕션 배포 | [Production Deployment](guides/PRODUCTION_DEPLOYMENT.md) |
| CloudWatch 모니터링 설정 | [CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md) |
| Gemini AI 협업 | [Agentic Workflow](guides/AGENTIC_WORKFLOW.md) |
| Docker 배포 | [Docker Deployment](guides/DOCKER_DEPLOYMENT.md) |

### By Sprint Status
```
✅ Sprint 1-10: 완료 (83% 진도)
🔄 Sprint 10 Phase 2: 완료 (CloudWatch 모니터링)
📋 Sprint 11: 계획 중 (프론트엔드 개선)
```

See **[NEXT_STEPS.md](../NEXT_STEPS.md)** for detailed progress.

---

## 📊 Project Overview

| 항목 | 내용 |
|------|------|
| 🎯 목표 | AWS 계정을 자동으로 감시하고, 위협 탐지 시 Telegram 알림 + 자동 대응 |
| 🔨 기술 스택 | Python 3.12, AWS Lambda, DynamoDB, EventBridge, Next.js, React 19 |
| 📍 배포 | AWS Lambda (서버리스) |
| 🧪 테스트 | 112/116 통과 (3개 LocalStack 인프라 문제는 사전 알려진 상태) |
| 💰 비용 | < $0.50/월 (AWS 무료 티어 활용) |

---

## 🔗 Related Files

- **Main Project Instructions**: [CLAUDE.md](../CLAUDE.md)
- **Progress Tracking**: [NEXT_STEPS.md](../NEXT_STEPS.md) (최신 업데이트 2026-05-03)
- **Code Repository**: `/lambda` (메인 감시 로직), `/apps/web` (대시보드)

---

## 🆘 How to Use This Documentation

1. **처음 시작하는 경우**: [Local Development](guides/LOCAL_DEVELOPMENT.md) 시작
2. **프로덕션 배포 필요**: [Production Deployment](guides/PRODUCTION_DEPLOYMENT.md) 참조
3. **모니터링 설정**: [CloudWatch Monitoring](guides/CLOUDWATCH_MONITORING.md) 참조
4. **Gemini 협업**: [Agentic Workflow](guides/AGENTIC_WORKFLOW.md) 참조
5. **전체 상황 파악**: [NEXT_STEPS.md](../NEXT_STEPS.md) (스프린트별 상세)

---

**Last Updated**: 2026-05-03 (Sprint 10 Phase 2 완료)
