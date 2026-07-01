---
module: checkers
path: 02-Checkers
keywords: s3, public-bucket, acl, bucket-policy
---

# S3Checker — S3 보안 감시

#module-checkers #api-aws

## 목적

S3 버킷의 공개 접근 여부를 탐지하고, 신규 버킷 생성을 모니터링합니다.

## 주요 파일

`lambda/guardian/checkers/s3.py`

## 탐지 항목

| 항목 | 탐지 방법 | 심각도 |
|------|----------|--------|
| 퍼블릭 버킷 (ACL) | `get_bucket_acl()` → AllUsers 또는 AuthenticatedUsers 권한 | CRITICAL |
| 퍼블릭 버킷 (Policy) | `get_bucket_policy()` → Principal: "*" | CRITICAL |
| Public Access Block 비활성화 | `get_public_access_block()` → BlockPublicAcls=False | HIGH |
| 신규 버킷 | 생성 시각 기준 24시간 이내 | MEDIUM |

## 퍼블릭 버킷 탐지 로직

```python
def _get_public_buckets(self) -> list:
    buckets = self.s3_client.list_buckets()["Buckets"]
    public = []

    for bucket in buckets:
        name = bucket["Name"]
        # 방법 1: ACL 확인
        acl = self.s3_client.get_bucket_acl(Bucket=name)
        for grant in acl["Grants"]:
            if grant["Grantee"].get("URI", "").endswith("AllUsers"):
                public.append({"bucket_name": name, "reason": "public_acl"})

        # 방법 2: Bucket Policy 확인
        try:
            policy = json.loads(
                self.s3_client.get_bucket_policy(Bucket=name)["Policy"]
            )
            # Principal: "*" 여부 확인
        except self.s3_client.exceptions.NoSuchBucketPolicy:
            pass  # 정책 없음 = 퍼블릭 아님

    return public
```

## 자동 대응

퍼블릭 버킷 감지 시:
→ `AutoRemediationResponder` → `put_public_access_block()` 자동 적용

```python
s3_client.put_public_access_block(
    Bucket=bucket_name,
    PublicAccessBlockConfiguration={
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }
)
```

## ThreadPoolExecutor 병렬 처리

```python
# 여러 버킷을 병렬로 검사
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(self._check_bucket, bucket)
               for bucket in buckets]
```

## CheckResult 예시

```python
CheckResult(
    severity="CRITICAL",
    title="S3 퍼블릭 버킷 감지",
    message="public-bucket-123: ACL을 통한 공개 접근 가능",
    details={
        "is_anomaly": True,
        "public_buckets": [
            {"bucket_name": "public-bucket-123", "reason": "public_acl"}
        ],
        "new_buckets": []
    },
    suggested_action="S3 퍼블릭 액세스 차단을 즉시 적용하세요"
)
```

## Related Notes

- [[Checkers 개요]]
- [[Responders 개요]]
