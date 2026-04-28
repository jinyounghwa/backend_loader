"""AWS Guardian configuration module"""
import os
from typing import Optional

class Config:

    @staticmethod
    def get_endpoint_url() -> str:
        return os.getenv('LOCALSTACK_ENDPOINT', 'http://localhost:4566')

    @staticmethod
    def get_boto3_kwargs() -> dict:
        kwargs = {
            'region_name': os.getenv('AWS_REGION', 'us-east-1'),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        }

        endpoint = Config.get_endpoint_url()
        if endpoint:
            kwargs['endpoint_url'] = endpoint

        return kwargs

    @staticmethod
    def is_localstack() -> bool:
        return os.getenv('AWS_ENV', 'localstack') == 'localstack'

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
