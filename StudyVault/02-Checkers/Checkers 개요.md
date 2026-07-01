---
module: checkers
path: 02-Checkers
keywords: checker, base-class, check-result, anomaly-detection
---

# Checkers 개요

#module-checkers #pattern-base-class

## 역할

Checkers는 AWS 리소스의 이상 상태를 탐지하는 모듈입니다.
각 체커는 `BaseChecker`를 상속하고 `check()` 메서드를 구현합니다.

## 체커 목록

| 체커 | 파일 | 탐지 대상 |
|------|------|----------|
| `CostChecker` | `checkers/cost.py` | 일일 비용 임계값 초과 |
| `EC2Checker` | `checkers/ec2.py` | 비인가 리전, 오픈 보안그룹, 신규 인스턴스 |
| `S3Checker` | `checkers/s3.py` | 퍼블릭 버킷 (ACL/Policy), 신규 버킷 |
| `CloudTrailChecker` | `checkers/cloudtrail.py` | 의심스러운 API 호출 |
| `IAMChecker` | `checkers/iam.py` | IAM 권한 변경, 사용자 이상 행동 |
| `GuardDutyChecker` | `checkers/guardduty.py` | GuardDuty 위협 알림 |
| `RDSChecker` | `checkers/rds.py` | RDS 보안 설정 이상 |

## BaseChecker 추상 클래스

```python
class BaseChecker(ABC):
    def __init__(self, clients, config, account_id=None, credentials=None):
        self.clients = clients      # boto3 클라이언트 dict (테스트용 주입)
        self.config = config        # 설정 dict
        self.account_id = account_id
        self.credentials = credentials

    @abstractmethod
    def check(self) -> CheckResult: ...      # 동기 실행
    async def check_async(self) -> CheckResult: ...  # 비동기 실행 (기본: check() 래핑)
```

> [!important] 실행 모델 2가지
> - **sync-first**: `check()` 구현 → `check_async()`가 자동으로 executor에서 래핑
> - **async-first**: `check_async()` 구현 → `check()`가 `_run_sync()`로 자동 호출
> 두 방향 모두 호환됩니다.

## CheckResult 표준 결과 형식

```python
class CheckResult:
    SEVERITY_LEVELS = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

    severity: str           # 심각도
    title: str              # 제목
    message: str            # 상세 메시지
    details: dict           # 추가 정보 (체커별 커스텀)
    suggested_action: str   # 권장 조치
```

### 팩토리 메서드

| 메서드 | severity | 용도 |
|--------|----------|------|
| `CheckResult.info(title, msg)` | `INFO` | 정상 상태 |
| `CheckResult.error(title, msg)` | `HIGH` | 체커 실행 오류 |
| `CheckResult(severity, ...)` | 직접 지정 | 이상 감지 |

## 의존성 주입 패턴 (테스트 용이성)

```python
# 테스트에서 boto3 클라이언트를 목(mock)으로 주입
checker = CostChecker(
    clients={"ce": mock_ce_client, "ssm": mock_ssm_client},
    config={"cost_threshold": 5.0}
)

# 프로덕션에서는 클라이언트 없이 생성 → 내부에서 boto3.client() 호출
checker = CostChecker()
```

> [!tip] 왜 clients dict를 받나?
> Lambda 환경에서는 실제 AWS 연결이 필요하지만, 테스트에서는 비용이 드는 실제 API 대신
> mock 객체를 주입해서 빠르고 격리된 테스트를 실행할 수 있습니다.

## 에러 처리 공통 패턴

```python
def check(self) -> CheckResult:
    try:
        # ... 체커 로직
    except ClientError as e:
        return self._handle_client_error("EC2", e)  # HIGH severity
    except Exception as e:
        return self._handle_generic_error("EC2", e)  # HIGH severity
```

## Related Notes

- [[CostChecker]]
- [[EC2Checker]]
- [[S3Checker]]
- [[CloudTrailChecker]]
- [[IAMChecker]]
- [[요청 흐름 (Request Flow)]]
