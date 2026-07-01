---
module: checkers
path: 02-Checkers
keywords: practice, quiz, checkers
---

# 연습문제 — Checkers 모듈

#module-checkers

## 문제 1 (개념) BaseChecker 실행 모델

`BaseChecker`는 두 가지 실행 패턴을 지원합니다. 각 패턴의 특징과 언제 사용하는지 설명하세요.

> [!answer]- 정답 보기
> **Sync-first 패턴**: `check()` 메서드를 구현합니다. `check_async()`는 내부에서 자동으로 `loop.run_in_executor(None, self.check)`를 호출하여 비동기 래핑합니다. boto3 동기 API를 직접 쓸 때 적합합니다.
>
> **Async-first 패턴**: `check_async()`를 구현합니다. `check()`는 `_run_sync(self.check_async())`로 자동 제공됩니다. `asyncio`와 `aiohttp` 등 네이티브 비동기 라이브러리 사용 시 적합합니다.
>
> 두 패턴 모두 `check()`와 `check_async()` 양쪽으로 호출 가능합니다.

---

## 문제 2 (응용) 새 체커 추가

`RDSChecker`를 신규 추가할 때 최소한 구현해야 할 내용을 나열하세요.

> [!answer]- 정답 보기
> 1. `BaseChecker` 상속 클래스 생성
> 2. `__init__`에서 `boto3.client("rds")` 초기화 (의존성 주입 지원 포함)
> 3. `check()` 메서드 구현 → `CheckResult` 반환
> 4. `try/except ClientError`, `try/except Exception` 에러 처리
> 5. `_log_check_start("RDS")` / `_log_check_end()` 호출
> 6. `GuardianOrchestrator`에 `rds_checker` 파라미터 추가
> 7. `tests/test_rds.py` 작성 (mock clients 주입)

---

## 문제 3 (분석) CheckResult 심각도 설계

왜 `CheckResult.error()`는 `HIGH` 심각도를 반환할까요? `CRITICAL`이 아닌 이유는?

> [!answer]- 정답 보기
> 체커 실행 **오류**는 실제 보안 위협이 아닙니다. AWS API 호출 실패, 권한 부족 등의 시스템 오류입니다.
>
> `CRITICAL`은 실제 보안 사고(퍼블릭 S3, 무단 EC2 등)에 사용합니다. 오류와 위협의 심각도를 구분하면 운영자가 알림을 우선순위에 따라 처리할 수 있습니다.
>
> `HIGH`는 "즉각 조사 필요하지만 시스템이 다운되진 않음"을 의미합니다.

---

## 문제 4 (응용) 비용 임계값 변경

운영 중에 비용 임계값을 코드 재배포 없이 $10 → $20으로 바꾸려면 어떻게 해야 하나요? 두 가지 방법을 설명하세요.

> [!answer]- 정답 보기
> **방법 1 (Lambda 환경변수)**:
> AWS Lambda 콘솔 → 함수 → 구성 → 환경변수 → `COST_THRESHOLD=20.0` 수정
> 즉시 적용 (Lambda 재시작 없이도 가능)
>
> **방법 2 (SSM Parameter Store)**:
> ```bash
> aws ssm put-parameter \
>   --name /aws-guardian/cost-threshold \
>   --value "20.0" \
>   --overwrite
> ```
> `CostChecker`가 SSM에서 threshold를 읽으므로 다음 실행 시 자동 반영됩니다.
> SSM은 버전 관리와 감사 로그가 자동 생성됩니다.

---

## 문제 5 (분석) EC2 병렬 리전 스캔

`EC2Checker`가 ThreadPoolExecutor를 사용하는 이유를 설명하고, `max_workers=5`로 설정된 이유를 추론하세요.

> [!answer]- 정답 보기
> **이유**: EC2 API는 리전별로 독립적입니다. 20개 리전을 직렬로 스캔하면 20배 시간이 걸립니다. 병렬 처리로 가장 느린 리전의 응답 시간만큼만 기다립니다.
>
> **max_workers=5**: AWS Lambda의 네트워크 스택과 boto3 연결 풀 한계를 고려한 값입니다. 너무 많으면 연결 경쟁(connection contention)이 발생하고, 너무 적으면 병렬화 효과가 줄어듭니다. 실제 운영 리전 수(보통 3-5개)에도 적합합니다.

---

## 문제 6 (분석) S3 퍼블릭 탐지 3가지 방법 비교

S3 퍼블릭 버킷을 탐지하는 세 가지 방법(ACL, Policy, Public Access Block)의 차이를 설명하세요.

> [!answer]- 정답 보기
> **ACL (Access Control List)**: 버킷/객체 수준 권한. `AllUsers` 또는 `AuthenticatedUsers` URI가 있으면 퍼블릭.
> 레거시 방식으로 새 버킷에는 기본 비활성화.
>
> **Bucket Policy**: JSON 정책으로 `Principal: "*"`이면 전체 공개.
> 세밀한 제어 가능하지만 실수로 공개 정책 설정 위험.
>
> **Public Access Block**: 계정/버킷 수준에서 위 두 가지를 강제로 차단하는 보호막.
> `BlockPublicAcls=False`이면 ACL로 퍼블릭 설정 가능.
>
> 세 가지를 모두 확인해야 완전한 탐지가 가능합니다.

---

## 문제 7 (응용) LocalStack 테스트

`CostChecker`를 LocalStack에서 테스트할 때 mock 데이터(`MOCK_DAILY_COST_DEFAULT=5.50`)가 반환되는 이유는 무엇이며, 임계값을 $3.00으로 설정하면 어떤 결과가 나오나요?

> [!answer]- 정답 보기
> **이유**: LocalStack은 Cost Explorer API를 지원하지 않습니다. `Config.is_localstack()` 반환값이 True면 실제 API 호출 대신 하드코딩된 mock 값을 반환합니다.
>
> **임계값 $3.00**: mock daily_cost($5.50) > threshold($3.00) → 이상 감지 → `CheckResult(severity="HIGH", ...)`가 반환됩니다.
> 실제 테스트: `CostChecker(config={"cost_threshold": 3.0}).check()`

---

## 문제 8 (설계) CloudTrail 감지 간격

CloudTrail 이벤트는 최대 15분 지연될 수 있습니다. Guardian은 1시간마다 실행됩니다. 이 설계의 보안 취약점은 무엇이고 어떻게 개선할 수 있을까요?

> [!answer]- 정답 보기
> **취약점**: 공격이 발생하고 최대 1시간 15분 후에야 감지됩니다. 그 사이 공격자가 많은 작업을 수행할 수 있습니다.
>
> **개선 방안**:
> 1. EventBridge Rule을 실시간 CloudTrail → S3 → Lambda로 구성 (실시간 스트리밍)
> 2. `cloudtrail_stream_handler.py` 모듈이 이미 구현됨 (v2 기능)
> 3. GuardDuty 통합 → 이미 `guardduty.py` 체커 존재
> 4. EventBridge 간격을 15분으로 단축 (비용 증가)

## Related Concepts

- [[Checkers 개요]]
- [[CostChecker]]
- [[EC2Checker]]
- [[S3Checker]]
- [[CloudTrailChecker]]
