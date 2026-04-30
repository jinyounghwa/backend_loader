"""AWS Guardian configuration module"""
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration with caching for AWS Guardian."""

    _boto3_kwargs: Optional[Dict] = None
    _is_localstack: Optional[bool] = None

    @classmethod
    def get_endpoint_url(cls) -> str:
        return os.getenv('LOCALSTACK_ENDPOINT', 'http://localhost:4566')

    @classmethod
    def get_boto3_kwargs(cls) -> dict:
        """Cached boto3 kwargs — computed once, reused across all callers."""
        if cls._boto3_kwargs is None:
            cls._boto3_kwargs = {
                'region_name': os.getenv('AWS_REGION', 'us-east-1'),
                'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            }
            endpoint = cls.get_endpoint_url()
            if endpoint:
                cls._boto3_kwargs['endpoint_url'] = endpoint
        return cls._boto3_kwargs.copy()

    @classmethod
    def is_localstack(cls) -> bool:
        """Cached LocalStack detection."""
        if cls._is_localstack is None:
            cls._is_localstack = os.getenv('AWS_ENV', 'localstack') == 'localstack'
        return cls._is_localstack

    @staticmethod
    def get_cost_threshold() -> float:
        try:
            return float(os.getenv('COST_THRESHOLD', '10.0'))
        except ValueError:
            return 10.0

    @staticmethod
    def get_authorized_regions() -> List[str]:
        regions_str = os.getenv('AUTHORIZED_REGIONS', '')
        if regions_str:
            return [r.strip() for r in regions_str.split(',')]
        return []

    @staticmethod
    def get_telegram_config() -> Dict[str, str]:
        return {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
        }

    @staticmethod
    def get_discord_config() -> Dict[str, str]:
        return {
            'webhook_url': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'public_key': os.getenv('DISCORD_PUBLIC_KEY', '')
        }

    @staticmethod
    def get_dynamodb_table_name() -> str:
        return os.getenv('DYNAMODB_TABLE_NAME', 'aws-guardian-events')

    @staticmethod
    def is_organizations_enabled() -> bool:
        """Check if multi-account monitoring is enabled via Organizations."""
        return os.getenv('ORGANIZATIONS_ENABLED', 'false').lower() == 'true'

    @staticmethod
    def get_organization_arn() -> str:
        """Get the Organizations root account ARN for cross-account role assumption."""
        return os.getenv('ORGANIZATION_ARN', '')

    @staticmethod
    def get_cross_account_role_name() -> str:
        """Get the cross-account role name for STS AssumeRole."""
        return os.getenv('CROSS_ACCOUNT_ROLE_NAME', 'aws-guardian-cross-account-role')

    @classmethod
    def reset_cache(cls) -> None:
        """Reset cached values (useful for testing)."""
        cls._boto3_kwargs = None
        cls._is_localstack = None
