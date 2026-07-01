---
module: checkers
path: 02-Checkers
keywords: ec2, security-group, unauthorized-region, instance
---

# EC2Checker — EC2 보안 감시

#module-checkers #api-aws

## 목적

EC2 인스턴스와 보안 그룹을 검사하여 보안 이상을 탐지합니다.

## 주요 파일

`lambda/guardian/checkers/ec2.py`

## 탐지 항목

| 항목 | 기준 | 심각도 |
|------|------|--------|
| 비인가 리전 EC2 | `AUTHORIZED_REGIONS` 외 리전에 인스턴스 존재 | CRITICAL |
| 보안그룹 전체 오픈 | 인바운드 규칙에 `0.0.0.0/0` 또는 `::/0` | HIGH |
| 신규 인스턴스 | 최근 24시간 내 생성된 인스턴스 | MEDIUM |

## 설정

```bash
# 허용할 리전 목록 (쉼표 구분)
AUTHORIZED_REGIONS=us-east-1,ap-northeast-2

# 미설정 시: 모든 리전 허용 (비인가 리전 감지 비활성화)
```

## 리전별 클라이언트 캐싱

```python
def _get_regional_client(self, region: str) -> Any:
    if region not in self._client_cache:
        self._client_cache[region] = AWSClientProvider.get_client("ec2", region=region)
    return self._client_cache[region]
```

> [!tip] 왜 리전별 클라이언트가 필요한가?
> EC2 API는 리전마다 별도로 호출해야 합니다. 
> 모든 리전의 인스턴스를 확인하려면 각 리전에 별도 클라이언트를 만들어야 합니다.
> 캐싱으로 동일 리전 재호출 시 클라이언트 생성 비용을 절감합니다.

## ThreadPoolExecutor 병렬 처리

```python
# 여러 리전을 병렬로 조회
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(self._check_region, region): region
               for region in regions}
```

> [!important] 성능 최적화
> 직렬 처리 시 N개 리전 × API 응답 시간 → N배 지연
> 병렬 처리로 전체 시간을 단일 리전 응답 시간 수준으로 단축합니다.

## CheckResult 예시

```python
# 보안그룹 전체 오픈 감지
CheckResult(
    severity="HIGH",
    title="EC2 보안그룹 위험",
    message="sg-abc123: 포트 22 전체 허용 (0.0.0.0/0)",
    details={
        "is_anomaly": True,
        "open_security_groups": [
            {"group_id": "sg-abc123", "port": 22, "protocol": "tcp"}
        ]
    },
    suggested_action="해당 보안그룹에서 0.0.0.0/0 규칙을 제거하세요"
)
```

## 자동 대응

비인가 리전 또는 위험 인스턴스 감지 시:
→ `AutoRemediationResponder` → EC2 인스턴스 자동 Stop

## Related Notes

- [[Checkers 개요]]
- [[Responders 개요]]
- [[Config 모듈]]
