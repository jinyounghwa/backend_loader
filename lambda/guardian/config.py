"""AWS Guardian configuration module"""
import os
from typing import Optional

class Config:
    """Configuration for AWS Guardian"""

    @staticmethod
    def get_boto3_kwargs() -> dict:
        """Get boto3 client kwargs based on environment"""
        kwargs = {
            'region_name': os.getenv('AWS_REGION', 'us-east-1'),
        }

        # Use LocalStack endpoint if available
        localstack_endpoint = os.getenv('LOCALSTACK_ENDPOINT')
        if localstack_endpoint:
            kwargs['endpoint_url'] = localstack_endpoint

        return kwargs

    @staticmethod
    def is_localstack() -> bool:
        """Check if running in LocalStack mode"""
        return os.getenv('LOCALSTACK_ENDPOINT') is not None

    @staticmethod
    def get_cost_threshold() -> float:
        """Get cost threshold from environment"""
        try:
            return float(os.getenv('COST_THRESHOLD', '10.0'))
        except ValueError:
            return 10.0

    @staticmethod
    def get_authorized_regions() -> list:
        """Get authorized regions from environment"""
        regions_str = os.getenv('AUTHORIZED_REGIONS', '')
        if regions_str:
            return [r.strip() for r in regions_str.split(',')]
        return []

    @staticmethod
    def get_telegram_config() -> dict:
        """Get Telegram configuration"""
        return {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
        }

    @staticmethod
    def get_discord_config() -> dict:
        """Get Discord configuration"""
        return {
            'webhook_url': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'public_key': os.getenv('DISCORD_PUBLIC_KEY', '')
        }

    @staticmethod
    def get_dynamodb_table_name() -> str:
        """Get DynamoDB table name"""
        return os.getenv('DYNAMODB_TABLE_NAME', 'aws-guardian-events')
