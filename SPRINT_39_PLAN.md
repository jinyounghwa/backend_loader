# Sprint 39: 비용 최적화 및 다중계정 확장

## 현황

**완료된 Sprints:**
- Sprint 32: WebSocket 로그 수집 + 멀티 계정 (76 테스트)
- Sprint 33: 규칙 정의/저장/검증 (22 테스트)
- Sprint 34: 이상탐지/알림/UI (55 테스트)
- Sprint 35: 규칙 테스트 및 배포 (22 테스트)
- Sprint 36: 응답 감사 및 롤백 (25 테스트)
- Sprint 37: AWS 자동 대응 (30 테스트)
- Sprint 38: 규칙 성능 최적화 + 비용 관리 (47 테스트)

**누적 테스트:** 313 PASS ✅

---

## Sprint 39 목표

비용 관리 시스템을 확장하고 다중계정 감시를 강화합니다.

**4개 Phase로 구성:**
1. **Phase 1**: 비용 절감 자동 제안 (10 테스트)
2. **Phase 2**: 리소스 낭비 탐지 (12 테스트)
3. **Phase 3**: 예산 알림 및 제어 (10 테스트)
4. **Phase 4**: 다중계정 비용 통합 (12 테스트)

**총 44 테스트**

---

## Phase 1: 비용 절감 자동 제안 (10 테스트)

### 1.1 CostOptimizer 클래스
```python
class CostOptimizer:
    def analyze_cost_patterns(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        비용 패턴 분석 후 절감 제안 반환
        반환: [
            {
                'type': 'unused_instance',
                'description': 'EC2 인스턴스 i-xxx가 7일 동안 미사용',
                'monthly_savings': 150.0,
                'priority': 'high'
            },
            ...
        ]
        """
    
    def recommend_instance_downsizing(self, account_id: str) -> List[Dict]:
        """
        사용률 낮은 인스턴스의 다운사이징 제안
        반환: 다운사이징 제안 목록
        """
    
    def detect_overprovisioned_databases(self, account_id: str) -> List[Dict]:
        """
        과도하게 프로비저닝된 RDS 인스턴스 탐지
        """
    
    def analyze_storage_costs(self, account_id: str) -> List[Dict]:
        """
        S3/EBS 스토리지 최적화 제안
        """
```

### 1.2 테스트 그룹
- Cost Optimizer Basics (2 테스트)
- Instance Downsizing Detection (2 테스트)
- Database Analysis (2 테스트)
- Storage Cost Optimization (2 테스트)
- Combined Recommendations (1 테스트)
- Priority Scoring (1 테스트)

---

## Phase 2: 리소스 낭비 탐지 (12 테스트)

### 2.1 WasteDetector 클래스
```python
class WasteDetector:
    def detect_idle_resources(self, account_id: str) -> List[Dict]:
        """
        유휴 EC2, RDS, 탄력적 IP 탐지
        """
    
    def detect_unattached_volumes(self, account_id: str) -> List[Dict]:
        """
        연결되지 않은 EBS 볼륨 탐지
        """
    
    def detect_unallocated_elastic_ips(self, account_id: str) -> List[Dict]:
        """
        미사용 탄력적 IP 탐지
        """
    
    def detect_snapshot_waste(self, account_id: str) -> List[Dict]:
        """
        오래된 스냅샷 중 불필요한 것 탐지
        """
    
    def calculate_waste_score(self, resource_type: str, idle_days: int) -> float:
        """
        리소스 낭비도 점수화 (0-100)
        """
    
    def get_removal_candidates(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        안전하게 제거 가능한 리소스 목록
        """
```

### 2.2 테스트 그룹
- Idle Resource Detection (2 테스트)
- Unattached Volume Detection (2 테스트)
- Elastic IP Detection (2 테스트)
- Snapshot Analysis (2 테스트)
- Waste Scoring (2 테스트)
- Safe Removal Candidates (2 테스트)

---

## Phase 3: 예산 알림 및 제어 (10 테스트)

### 3.1 BudgetController 클래스
```python
class BudgetController:
    def set_monthly_budget(self, account_id: str, amount: float) -> None:
        """
        월간 예산 설정
        """
    
    def get_remaining_budget(self, account_id: str) -> Dict:
        """
        남은 예산 조회
        반환: {
            'budget': 1000.0,
            'spent': 650.0,
            'remaining': 350.0,
            'burn_rate': 21.67,  # $/day
            'days_until_limit': 16.1
        }
        """
    
    def check_budget_alert(self, account_id: str, percentage: float = 80) -> bool:
        """
        예산 80% 이상 사용 시 True 반환
        """
    
    def set_alert_thresholds(self, account_id: str, thresholds: Dict) -> None:
        """
        알림 임계값 설정: {50: 'warning', 80: 'critical', 100: 'stop'}
        """
    
    def forecast_month_end(self, account_id: str) -> Dict:
        """
        현재 추세로 월말 예상 지출 계산
        """
    
    def set_auto_remediation(self, account_id: str, enabled: bool) -> None:
        """
        예산 초과 시 자동 리소스 종료 활성화
        """
```

### 3.2 테스트 그룹
- Budget Setup and Retrieval (2 테스트)
- Budget Alerts (2 테스트)
- Alert Threshold Configuration (2 테스트)
- Month-End Forecasting (2 테스트)
- Auto-Remediation (2 테스트)

---

## Phase 4: 다중계정 비용 통합 (12 테스트)

### 4.1 MultiAccountCostAggregator 클래스
```python
class MultiAccountCostAggregator:
    def aggregate_costs(self, account_ids: List[str], date_range: Tuple[str, str]) -> Dict:
        """
        여러 계정의 비용을 통합하여 반환
        반환: {
            'accounts': {
                'acc-1': {'total': 500.0, 'services': {...}},
                'acc-2': {'total': 750.0, 'services': {...}}
            },
            'total': 1250.0,
            'by_service': {'EC2': 600.0, 'RDS': 400.0, ...}
        }
        """
    
    def get_cost_breakdown_by_account(self, date: str) -> Dict:
        """
        특정 날짜 계정별 비용 분석
        """
    
    def compare_account_costs(self, account_id1: str, account_id2: str, days: int = 30) -> Dict:
        """
        두 계정의 비용 비교 분석
        """
    
    def identify_cost_outliers(self, account_ids: List[str]) -> List[Dict]:
        """
        평균에서 벗어난 계정 탐지
        """
    
    def get_organization_trends(self, days: int = 90) -> List[Dict]:
        """
        조직 전체 비용 추이
        """
    
    def export_cost_report(self, account_ids: List[str], format: str = 'csv') -> bytes:
        """
        비용 보고서 생성 및 내보내기
        """
```

### 4.2 테스트 그룹
- Multi-Account Aggregation (2 테스트)
- Cost Breakdown by Account (2 테스트)
- Account Comparison (2 테스트)
- Outlier Detection (2 테스트)
- Organization Trends (2 테스트)
- Report Export (2 테스트)

---

## 구현 파일

### Phase 1
| 파일 | 설명 |
|------|------|
| `lambda/guardian/optimizers/cost_optimizer.py` | CostOptimizer 클래스 |
| `tests/backend/test_cost_optimizer.py` | 10개 테스트 |

### Phase 2
| 파일 | 설명 |
|------|------|
| `lambda/guardian/detectors/waste_detector.py` | WasteDetector 클래스 |
| `tests/backend/test_waste_detection.py` | 12개 테스트 |

### Phase 3
| 파일 | 설명 |
|------|------|
| `lambda/guardian/controllers/budget_controller.py` | BudgetController 클래스 |
| `tests/backend/test_budget_control.py` | 10개 테스트 |

### Phase 4
| 파일 | 설명 |
|------|------|
| `lambda/guardian/aggregators/multi_account_cost_aggregator.py` | MultiAccountCostAggregator 클래스 |
| `tests/backend/test_multi_account_costs.py` | 12개 테스트 |

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 비용 분석 | AWS Cost Explorer API + Custom Logic |
| 리소스 감시 | AWS CloudWatch Metrics |
| 데이터 저장 | DynamoDB (Budget, Waste, Aggregation) |
| 백엔드 | Python Lambda |
| 테스트 | pytest (44개) |

---

## 성공 지표

- [ ] Phase 1: 비용 절감 제안 정확도 > 90%
- [ ] Phase 2: 낭비 리소스 탐지율 > 85%
- [ ] Phase 3: 예산 제어 정확도 100%
- [ ] Phase 4: 다중계정 집계 성능 < 5초
- [ ] 모든 44개 테스트 PASS
- [ ] 누적 테스트: 313 + 44 = 357 PASS

---

## 일정

| Phase | 예상 시간 | 상태 |
|-------|---------|------|
| Phase 1 | 2시간 | ❌ 예정 |
| Phase 2 | 2시간 | ❌ 예정 |
| Phase 3 | 1.5시간 | ❌ 예정 |
| Phase 4 | 2시간 | ❌ 예정 |
| **총** | **7.5시간** | **❌ 예정** |

---

## 다음 단계 (Sprint 40+)

**향후 개선:**
- 머신러닝 기반 비용 예측
- RI(Reserved Instance) 최적화 제안
- Savings Plans 분석
- 크로스리전 비용 최적화
- 실시간 비용 대시보드 (웹 UI)

---

## 검증 체크리스트

**Phase 1** ✅
- [x] CostOptimizer 구현
- [x] 10개 테스트 PASS

**Phase 2** ✅
- [x] WasteDetector 구현
- [x] 12개 테스트 PASS

**Phase 3** ✅
- [x] BudgetController 구현
- [x] 10개 테스트 PASS

**Phase 4** ✅
- [x] MultiAccountCostAggregator 구현
- [x] 12개 테스트 PASS

**최종** ✅
- [x] 누적 44개 테스트 PASS
- [x] 전체 테스트: 357 PASS
- [x] Git 커밋: "feat: Sprint 39 - Cost Optimization and Multi-Account Support"

---

**작성자:** Claude Code  
**작성일:** 2026-05-24  
**완료일:** 2026-05-24  
**상태:** ✅ 완료
