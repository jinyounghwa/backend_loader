# Sprint 6 상세 구현 계획

> CloudTrail, IAM, GuardDuty 감시 기능 추가  
> 예상 소요시간: 2-3일  
> 상태: 📋 계획 수립 완료 (Gemini 아키텍처 검증 완료)

---

## 1. Gemini 피드백 반영사항

### ✅ 아키텍처 개선
- [x] `BaseChecker` 추상 클래스 도입 (ABC 패턴)
- [x] Orchestrator 레지스트리 패턴 적용
- [x] 각 체커 메서드 표준화 (`check()` → 공통 반환 포맷)

### ✅ 성능 최적화
- [x] CloudTrail: `ReadOnly=False` 필터 + 페이지네이션
- [x] IAM: Global 서비스, `us-east-1`에서만 실행
- [x] GuardDuty: Severity 매핑 (7.0+ = Critical, 4.0-6.9 = Warning)
- [x] 병렬 처리: `concurrent.futures` 멀티리전 지원

### ✅ 운영성 개선
- [x] Telegram: 사용자 컨텍스트 포함 + 아이콘 구분
- [x] IAM 권한: Lambda role에 `cloudtrail:LookupEvents`, `iam:List*`, `guardduty:ListFindings` 추가
- [x] 테스트: Moto/LocalStack 기반 단위 테스트

---

## 2. 구현 파일 목록

### Phase 1: 기본 구조 (Day 1)

#### `lambda/guardian/checkers/base.py` (NEW)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseChecker(ABC):
    """모든 체커의 기본 인터페이스"""
    
    def __init__(self, clients: Dict, config: Dict):
        self.clients = clients
        self.config = config
    
    @abstractmethod
    def check(self) -> Dict[str, Any]:
        """
        Returns:
        {
            'severity': 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO',
            'title': 'Check Name',
            'message': 'Human-readable message',
            'details': {...},
            'suggested_action': 'Recommended action or None'
        }
        """
        pass
```

#### `lambda/guardian/checkers/cloudtrail.py` (NEW)
```python
from base import BaseChecker

class CloudTrailChecker(BaseChecker):
    """
    CloudTrail 의심스러운 API 호출 감지
    
    감시:
    - 루트 계정 활동
    - ReadOnly=False (리소스 변경) API만 감지
    - 권한 상승 (CreateAccessKey, AttachUserPolicy)
    - 리소스 삭제
    
    최적화:
    - EventName 필터로 민감한 API만 수집
    - 페이지네이션 지원 (NextToken)
    - 최근 1시간 이벤트만 조회
    """
    pass
```

#### `lambda/guardian/checkers/iam.py` (NEW)
```python
class IAMChecker(BaseChecker):
    """
    IAM 권한 변경 감지
    
    감시:
    - 새 사용자 생성
    - 새 액세스 키 생성
    - 정책 변경
    - MFA 비활성화
    
    최적화:
    - Global 서비스: us-east-1에서만 실행
    - 기준 상태(baseline) 저장 (DynamoDB)
    - 증분식 변경 감지
    """
    pass
```

#### `lambda/guardian/checkers/guardduty.py` (NEW)
```python
class GuardDutyChecker(BaseChecker):
    """
    GuardDuty 위협 탐지 통합
    
    감시:
    - 모든 활성 Findings 조회
    - Severity 매핑: 7.0+ = Critical, 4.0-6.9 = Warning
    - 자동 대응 제안
    
    최적화:
    - 심각도 상위 findings 우선
    - 중복 제거 (같은 리소스의 반복 탐지)
    """
    pass
```

### Phase 2: Orchestrator 통합 (Day 1)

#### `lambda/guardian/orchestrator.py` (MODIFY)
```python
# 기존 코드:
def run_all_checks(self, event):
    ec2_result = self.ec2_checker.check()
    s3_result = self.s3_checker.check()
    # ...

# 개선 후 (레지스트리 패턴):
def run_all_checks(self, event):
    results = {}
    for name, checker in self.checkers.items():
        try:
            results[name] = checker.check()
        except Exception as e:
            results[name] = {
                'severity': 'ERROR',
                'title': f'{name} failed',
                'message': str(e)
            }
    return results
```

### Phase 3: Telegram 포맷팅 (Day 1-2)

#### `lambda/guardian/responders/telegram.py` (MODIFY)
```python
# 새로운 아이콘 및 포맷

ICON_MAP = {
    'cloudtrail': '🔍',  # 조사
    'iam': '🆔',         # 신원
    'guardduty': '🛡️',   # 보안
    'ec2': '💻',
    's3': '📦',
    'cost': '💰'
}

# CloudTrail 예시
"🔍 CloudTrail: 루트 계정 활동 감지\n"
"👤 사용자: root\n"
"🕐 시간: 2026-04-28 10:30:00\n"
"📍 위치: 203.0.113.45\n"
"⚠️ 조치: 즉시 MFA 검증 필요"

# IAM 예시
"🆔 IAM: 새 액세스 키 생성\n"
"👤 사용자: dev-user\n"
"📝 키: AKIA...XXXX\n"
"⚠️ 조치: 승인 확인 필요"

# GuardDuty 예시
"🛡️ GuardDuty: 비정상 네트워크 활동\n"
"🎯 대상: i-0123456789abcdef0\n"
"📊 심각도: HIGH (8.2/10)\n"
"⚠️ 조치: 보안그룹 검토 필요"
```

### Phase 4: IAM 권한 업데이트 (Day 2)

#### `terraform/iam.tf` (MODIFY)
```hcl
# Lambda 실행 역할에 추가 권한
"cloudtrail:LookupEvents"
"iam:ListUsers"
"iam:ListAccessKeys"
"iam:ListPolicies"
"iam:GetPolicy"
"iam:GetPolicyVersion"
"guardduty:ListDetectors"
"guardduty:ListFindings"
"guardduty:GetFindings"
```

### Phase 5: 테스트 (Day 2-3)

#### `tests/test_cloudtrail.py` (NEW)
```python
import pytest
from moto import mock_cloudtrail, mock_iam

@mock_cloudtrail
@mock_iam
def test_cloudtrail_detects_root_activity():
    """루트 계정 활동 감지"""
    pass

@mock_cloudtrail
def test_cloudtrail_with_pagination():
    """페이지네이션 처리"""
    pass

@mock_cloudtrail
def test_cloudtrail_filters_readonly_events():
    """ReadOnly 이벤트 필터링"""
    pass
```

#### `tests/test_iam.py` (NEW)
```python
@mock_iam
def test_iam_detects_new_user():
    """새 사용자 생성 감지"""
    pass

@mock_iam
def test_iam_detects_new_access_key():
    """새 액세스 키 생성 감지"""
    pass
```

#### `tests/test_guardduty.py` (NEW)
```python
def test_guardduty_severity_mapping():
    """Severity 매핑 검증"""
    pass
```

---

## 3. 일정 및 마일스톤

| 날짜 | 마일스톤 | 작업 |
|------|---------|------|
| Day 1 오전 | Phase 1 | BaseChecker, 3개 체커 클래스 구현 |
| Day 1 오후 | Phase 2 | Orchestrator 레지스트리 통합 |
| Day 2 오전 | Phase 3 | Telegram 포맷팅 + 테스트 |
| Day 2 오후 | Phase 4 | IAM 권한 업데이트, LocalStack 배포 |
| Day 3 | Phase 5 | 단위 테스트, 통합 테스트, 문서화 |

---

## 4. 검증 체크리스트

### LocalStack 테스트
- [ ] CloudTrail: 의심스러운 API 호출 감지 확인
- [ ] IAM: 권한 변경 감지 확인
- [ ] GuardDuty: 위협 탐지 포맷 검증
- [ ] Telegram 알림 메시지 포맷 확인

### 코드 품질
- [ ] 모든 체커 BaseChecker 상속
- [ ] 에러 처리 (timeout, permission denied)
- [ ] 로깅 (INFO, WARNING, ERROR)
- [ ] 타입 힌팅 (type hints)

### 성능
- [ ] CloudTrail: 페이지네이션 동작
- [ ] 병렬 처리: 다중 리전 조회 (향후)
- [ ] Lambda 타임아웃 내 완료 (60초)

### 문서
- [ ] 각 체커 docstring 작성
- [ ] Telegram 메시지 샘플 문서화
- [ ] 테스트 케이스 주석

---

## 5. 리스크 및 완화 전략

| 리스크 | 영향 | 완화 전략 |
|--------|------|---------|
| CloudTrail API 호출 비용 | 월 $0.30 추가 | Lookup 범위 제한 (1시간) |
| IAM global service 중복 감지 | 불필요한 호출 | Region 체크 후 `us-east-1`만 실행 |
| GuardDuty 미활성화 리전 | 체크 실패 | try-except로 graceful 처리 |
| Lambda 타임아웃 (60초) | 검사 불완전 | 병렬 처리 도입 (Day 3+) |

---

## 6. 다음 스프린트 (Sprint 7)

### Sprint 7: AI 통합 및 고급 분석
- Gemini API 자동 위협 분석
- 머신러닝 이상 탐지
- 자동 보고서 생성

**Sprint 6 완료 후 기반:**
- 3개 체커에서 생성된 이벤트 데이터
- Telegram 알림 시스템
- DynamoDB 이벤트 저장소

---

## 진행 상태

**아키텍처**: ✅ Gemini 검증 완료  
**구현**: 📋 시작 준비 중  
**테스트**: 📋 계획 수립 중  
**배포**: 📋 향후 예정  

**다음 단계**: Day 1 오전 BaseChecker + CloudTrailChecker 구현 시작
