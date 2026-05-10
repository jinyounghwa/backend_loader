"""AWS Guardian configuration module"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "LOCALSTACK_ENDPOINT": "http://localhost:4566",
    "AWS_REGION": "us-east-1",
    "COST_THRESHOLD": 10.0,
    "DYNAMODB_TABLE_NAME": "aws-guardian-events",
    "CROSS_ACCOUNT_ROLE_NAME": "aws-guardian-cross-account-role",
}


class Config:
    """Centralized configuration with caching for AWS Guardian."""

    _boto3_kwargs: Optional[Dict] = None
    _is_localstack: Optional[bool] = None

    @classmethod
    def _env(cls, key: str, default: str = "") -> str:
        return os.getenv(key, default)

    @classmethod
    def get_endpoint_url(cls) -> str:
        return cls._env("LOCALSTACK_ENDPOINT", _DEFAULTS["LOCALSTACK_ENDPOINT"])

    @classmethod
    def get_boto3_kwargs(cls) -> Dict:
        if cls._boto3_kwargs is None:
            is_local = cls._env("AWS_ENV", "localstack") == "localstack"
            kwargs = {
                "region_name": cls._env("AWS_REGION", _DEFAULTS["AWS_REGION"]),
            }

            # In LocalStack mode, use test credentials; otherwise require real env vars
            if is_local:
                kwargs["aws_access_key_id"] = cls._env("AWS_ACCESS_KEY_ID", "test")
                kwargs["aws_secret_access_key"] = cls._env("AWS_SECRET_ACCESS_KEY", "test")
            else:
                access_key = cls._env("AWS_ACCESS_KEY_ID")
                secret_key = cls._env("AWS_SECRET_ACCESS_KEY")
                if access_key:
                    kwargs["aws_access_key_id"] = access_key
                if secret_key:
                    kwargs["aws_secret_access_key"] = secret_key
                # When neither key is provided, boto3 falls back to
                # IAM role / instance profile (the expected production path)

            endpoint = cls.get_endpoint_url() if is_local else ""
            if endpoint:
                kwargs["endpoint_url"] = endpoint
            cls._boto3_kwargs = kwargs
        return cls._boto3_kwargs.copy()

    @classmethod
    def is_localstack(cls) -> bool:
        if cls._is_localstack is None:
            cls._is_localstack = cls._env("AWS_ENV", "localstack") == "localstack"
        return cls._is_localstack

    @classmethod
    def get_cost_threshold(cls) -> float:
        try:
            return float(cls._env("COST_THRESHOLD", str(_DEFAULTS["COST_THRESHOLD"])))
        except ValueError:
            return _DEFAULTS["COST_THRESHOLD"]

    @classmethod
    def get_authorized_regions(cls) -> List[str]:
        regions_str = cls._env("AUTHORIZED_REGIONS", "")
        if regions_str:
            return [r.strip() for r in regions_str.split(",")]
        return []

    @classmethod
    def get_telegram_config(cls) -> Dict[str, str]:
        return {
            "bot_token": cls._env("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": cls._env("TELEGRAM_CHAT_ID", ""),
        }

    @classmethod
    def get_discord_config(cls) -> Dict[str, str]:
        return {
            "webhook_url": cls._env("DISCORD_WEBHOOK_URL", ""),
            "public_key": cls._env("DISCORD_PUBLIC_KEY", ""),
        }

    @classmethod
    def get_dynamodb_table_name(cls) -> str:
        return cls._env("DYNAMODB_TABLE_NAME", _DEFAULTS["DYNAMODB_TABLE_NAME"])

    @classmethod
    def is_organizations_enabled(cls) -> bool:
        return cls._env("ORGANIZATIONS_ENABLED", "false").lower() == "true"

    @classmethod
    def get_organization_arn(cls) -> str:
        return cls._env("ORGANIZATION_ARN", "")

    @classmethod
    def get_cross_account_role_name(cls) -> str:
        return cls._env("CROSS_ACCOUNT_ROLE_NAME", _DEFAULTS["CROSS_ACCOUNT_ROLE_NAME"])

    @classmethod
    def reset_cache(cls) -> None:
        """Reset all cached configuration values.

        Creates new empty containers so that concurrent readers never
        observe a half-reset state.
        """
        cls._boto3_kwargs = None
        cls._is_localstack = None
