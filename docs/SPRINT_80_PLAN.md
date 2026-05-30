# Sprint 80: Kubernetes & Container Security

**목표:** AWS Guardian v3.0 - K8s 위협 탐지 + 컨테이너 보안  
**기간:** 2026-05-30 ~  
**누적 테스트 목표:** 427 + 60 = 487 (60 tests per 4 phases)

---

## 📋 Context

**현황:**
- Sprint 79 완료: 64 테스트 PASS
- 누적 테스트: 427/362 (118%)
- AWS Guardian v2.9: 모든 시각화 기능 완성
- v3.0 목표: K8s + 컨테이너 보안 통합

---

## 📋 Phase 1: Kubernetes Threat Detection (15 tests)

### 기능
- **K8sMonitor**: K8s API 감시 및 위협 탐지
- **APIServerAnalyzer**: API 서버 비정상 감지
- **RBACValidator**: RBAC 권한 이상 감지
- **NetworkPolicyChecker**: 네트워크 정책 검증

### 구현 파일 (2개)
- `lambda/guardian/k8s/k8s_threat_detection.py` (350 lines)
- `tests/backend/test_k8s_threats.py` (15 tests)

---

## 📋 Phase 2: Container Scanning & Analysis (15 tests)

### 기능
- **ImageScanner**: 컨테이너 이미지 취약점 스캔
- **VulnerabilityAnalyzer**: 취약점 분석 및 심각도 평가
- **BaselineValidator**: 베이스 이미지 검증
- **RegistryIntegration**: Docker Registry 통합

### 구현 파일 (2개)
- `lambda/guardian/k8s/container_scanning.py` (350 lines)
- `tests/backend/test_container_scanning.py` (15 tests)

---

## 📋 Phase 3: Pod Anomaly Detection (15 tests)

### 기능
- **PodMonitor**: Pod 활동 모니터링
- **BehaviorAnalyzer**: 비정상 Pod 동작 감지
- **ResourceMonitor**: 리소스 사용량 이상 감지
- **PrivilegeDetector**: 권한 에스컬레이션 감지

### 구현 파일 (2개)
- `lambda/guardian/k8s/pod_anomaly_detection.py` (350 lines)
- `tests/backend/test_pod_anomaly.py` (15 tests)

---

## 📋 Phase 4: Helm Chart Validation (15 tests)

### 기능
- **HelmValidator**: Helm 차트 보안 검증
- **ManifestAnalyzer**: K8s 매니페스트 분석
- **ComplianceChecker**: 정책 준수 검증
- **DeploymentAdvisor**: 배포 보안 추천

### 구현 파일 (2개)
- `lambda/guardian/k8s/helm_validation.py` (350 lines)
- `tests/backend/test_helm_validation.py` (15 tests)

---

## 📊 Sprint 80 Test Summary

| Phase | 제목 | 테스트 |
|-------|------|--------|
| 1️⃣ | K8s Threat Detection | 15 |
| 2️⃣ | Container Scanning | 15 |
| 3️⃣ | Pod Anomaly Detection | 15 |
| 4️⃣ | Helm Chart Validation | 15 |
| **합계** | **Sprint 80** | **60** |

**Cumulative:** 427 + 60 = **487 tests (134% of 362 target)** ✅

---

## ✅ Success Criteria

- 60 tests PASS
- K8s 클러스터 위협 탐지 기능 구현
- 컨테이너 이미지 스캔 기능 구현
- Pod 이상 감지 기능 구현
- Helm 검증 기능 구현

> **Note**: 위 수치는 목표이며, 실제 달성 여부는 구현 후 측정 필요

---

## 🛠️ Technical Approach

### K8s Integration
- Kubernetes Python client
- API Server event monitoring
- RBAC policy analysis
- Network policy validation

### Container Security
- Image vulnerability scanning
- CVE database integration
- Layer-by-layer analysis
- Registry integration

### Pod Monitoring
- Resource usage tracking
- Process monitoring
- Network connection analysis
- Privilege escalation detection

### Helm Validation
- Chart structure validation
- Security best practices
- Compliance policy checks
- Deployment safety analysis

---

## 📅 Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1 | 2-3일 | ⏳ Ready |
| 2 | 2-3일 | ⏳ Ready |
| 3 | 2-3일 | ⏳ Ready |
| 4 | 2-3일 | ⏳ Ready |
| **Total** | **~12일** | ⏳ |

---

**Sprint 80 상태:** ⏳ **IN PROGRESS** (Phase 1: K8s Threat Detection 구현됨, Phase 2-4 미구현)

---

**목표:** AWS Guardian v3.0 - Kubernetes & Container Security
