---
module: checkers
path: 02-Checkers
keywords: cost, cost-explorer, threshold, anomaly
---

# CostChecker — 비용 이상 감지

#module-checkers #api-aws

## 목적

AWS Cost Explorer API를 통해 당일/전일 비용을 조회하고,
설정된 임계값(`COST_THRESHOLD`) 초과 시 이상 감지를 반환합니다.

## 주요 파일

`lambda/guardian/checkers/cost.py`

## 탐지 항목

| 항목 | 기준 | 심각도 |
|------|------|--------|
| 일일 비용 초과 | `daily_cost > threshold` | HIGH |
| 월 누적 비용 추이 | 참고용 | INFO |

## 설정

```python
# 기본 임계값: $10/일
CostChecker(config={"cost_threshold": 10.0})

# 환경변수로도 설정 가능
COST_THRESHOLD=15.0
```

## SSM 연동

```
SSM Parameter Store: /aws-guardian/cost-threshold
    │
    ▼
CostChecker 초기화 시 조회 → threshold 설정
```

> [!tip] SSM vs 환경변수 우선순위
> SSM에 값이 있으면 SSM 값 사용 (프로덕션 권장)
> SSM 조회 실패 시 환경변수 `COST_THRESHOLD` 폴백

## LocalStack 동작

```python
if self.is_localstack:
    # Cost Explorer API 미지원 → 목 데이터 반환
    daily_cost = MOCK_DAILY_COST_DEFAULT   # 5.50
    monthly_cost = MOCK_MONTHLY_COST_DEFAULT  # 150.50
```

> [!warning] LocalStack 제한
> Cost Explorer API는 LocalStack에서 지원되지 않습니다.
> 로컬 테스트 시 mock 값이 반환됩니다. 실제 비용 확인은 프로덕션에서만 가능합니다.

## Lazy boto3 클라이언트

```python
@property
def ce_client(self):
    if self._ce_client is None:
        self._ce_client = boto3.client("ce", **Config.get_boto3_kwargs())
    return self._ce_client
```

Cost Explorer는 항상 `us-east-1` 리전에서만 사용 가능하다는 점에 주의합니다.

## CheckResult 예시

```python
# 이상 감지 시
CheckResult(
    severity="HIGH",
    title="비용 임계값 초과",
    message="오늘 비용: $15.30 (임계값: $10.00)",
    details={"daily_cost": 15.30, "threshold": 10.0, "monthly_cost": 450.0},
    suggested_action="AWS 콘솔에서 비용 원인을 확인하세요"
)

# 정상 시
CheckResult.info("비용 정상", "오늘 비용: $5.50 (임계값: $10.00)")
```

## 관련 연습문제

→ [[온보딩 연습문제]] 연습 2번: "임계값을 $5로 낮추면 어떻게 되나?"

## Related Notes

- [[Checkers 개요]]
- [[Config 모듈]]
- [[DynamoDB Storage]]
