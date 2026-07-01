---
module: config
path: 04-Storage-Config
keywords: config, ssm, environment-variables, boto3, localstack
---

# Config 모듈 — 중앙 설정 관리

#module-config #config-env #config-ssm

## 목적

모든 환경 변수와 SSM Parameter Store 값을 중앙에서 관리하고 캐싱합니다.

## 주요 파일

`lambda/guardian/config.py`

## 설계 특징

```python
class Config:
    _boto3_kwargs: Optional[Dict] = None   # 클래스 변수로 캐싱
    _is_localstack: Optional[bool] = None
    _ssm_cache: Dict[str, str] = {}
```

> [!tip] 클래스 변수 캐싱
> `Config._boto3_kwargs`는 인스턴스가 아닌 **클래스**에 저장됩니다.
> Lambda 워커가 재사용될 때 동일한 캐시를 씁니다.
> 매 호출마다 SSM/boto3 초기화 비용을 줄입니다.

## LocalStack vs 프로덕션 분기

```python
@classmethod
def get_boto3_kwargs(cls) -> Dict:
    is_local = cls._env("AWS_ENV", "localstack") == "localstack"

    if is_local:
        kwargs = {
            "aws_access_key_id": "test",       # LocalStack 테스트 자격증명
            "aws_secret_access_key": "test",
            "endpoint_url": "http://localhost:4566",
        }
    else:
        kwargs = {}  # IAM 역할 사용 (프로덕션)
```

## SSM Parameter Store 조회

```python
@classmethod
def _get_ssm_value(cls, param_name: str) -> str:
    if param_name in cls._ssm_cache:
        return cls._ssm_cache[param_name]   # 캐시 히트

    ssm = boto3.client("ssm", ...)
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    value = response["Parameter"]["Value"]
    cls._ssm_cache[param_name] = value      # 캐시 저장
    return value
```

## 비밀값 로딩 우선순위

```
프로덕션 권장 순서:
1. SSM Parameter Store (SSM_TELEGRAM_BOT_TOKEN_PATH 환경변수로 SSM 경로 지정)
2. 환경변수 직접 설정 (하위 호환성 / 로컬 개발)
3. 기본값 또는 빈 문자열 반환

예시:
  SSM_TELEGRAM_BOT_TOKEN_PATH = "/prod/guardian/telegram/token"
      │
      ▼
  ssm.get_parameter("/prod/guardian/telegram/token", WithDecryption=True)
      │
      ▼
  실제 토큰 값 (암호화 해제됨)
```

## 캐시 초기화

```python
@classmethod
def reset_cache(cls) -> None:
    cls._boto3_kwargs = None
    cls._is_localstack = None
    cls._ssm_cache = {}
```

> [!warning] 테스트에서 반드시 reset_cache() 호출
> 테스트 간 Config 캐시가 공유되면 한 테스트의 설정이 다른 테스트에 영향을 줍니다.
> 각 테스트 setUp/tearDown에서 `Config.reset_cache()`를 호출하세요.

## 주요 메서드 정리

| 메서드 | 반환값 | 설명 |
|--------|--------|------|
| `get_boto3_kwargs()` | dict | boto3 클라이언트 생성 인자 |
| `is_localstack()` | bool | LocalStack 환경 여부 |
| `get_cost_threshold()` | float | 비용 임계값 ($) |
| `get_telegram_config()` | dict | bot_token, chat_id |
| `get_discord_config()` | dict | webhook_url, public_key |
| `get_dynamodb_table_name()` | str | DynamoDB 테이블명 |
| `get_authorized_regions()` | list | 허용 EC2 리전 목록 |
| `is_organizations_enabled()` | bool | 다중 계정 활성화 여부 |

## Related Notes

- [[Guardian Handler]]
- [[DynamoDB Storage]]
- [[DevOps & 배포]]
