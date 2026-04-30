"""AWS Cost Explorer checker for AWS Guardian"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)

MOCK_DAILY_COST_DEFAULT = 5.50
MOCK_MONTHLY_COST_DEFAULT = 150.50


class CostChecker:
    def __init__(self, cost_threshold: float = 10.0):
        self.threshold = cost_threshold
        self.is_localstack = Config.is_localstack()
        self.ssm_client = AWSClientProvider.get_client('ssm')

        if not self.is_localstack:
            self.ce_client = AWSClientProvider.get_client('ce')
        else:
            self.ce_client = None

    def get_daily_cost(self, date: str = None) -> float:
        if not date:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        try:
            if self.is_localstack:
                mock_cost = float(os.getenv('MOCK_DAILY_COST', str(MOCK_DAILY_COST_DEFAULT)))
                logger.info("[LocalStack] Returning mock daily cost for %s: $%.2f", date, mock_cost)
                return mock_cost

            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': date, 'End': date},
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )

            if response['ResultsByTime']:
                cost_str = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
                return float(cost_str)
            return 0.0
        except Exception as e:
            logger.error("Error getting daily cost: %s", e)
            if self.is_localstack:
                return float(os.getenv('MOCK_DAILY_COST', str(MOCK_DAILY_COST_DEFAULT)))
            return 0.0

    def get_monthly_cost(self, year: int = None, month: int = None) -> float:
        if not year:
            year = datetime.now(timezone.utc).year
        if not month:
            month = datetime.now(timezone.utc).month

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        try:
            if self.is_localstack:
                mock_cost = float(os.getenv('MOCK_MONTHLY_COST', str(MOCK_MONTHLY_COST_DEFAULT)))
                logger.info("[LocalStack] Returning mock monthly cost for %d-%02d: $%.2f", year, month, mock_cost)
                return mock_cost

            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )

            if response['ResultsByTime']:
                cost_str = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
                return float(cost_str)
            return 0.0
        except Exception as e:
            logger.error("Error getting monthly cost: %s", e)
            if self.is_localstack:
                return MOCK_MONTHLY_COST_DEFAULT
            return 0.0

    def check_cost_anomaly(self) -> Tuple[bool, Dict[str, Any]]:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        daily_cost = self.get_daily_cost(today)

        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_cost = self.get_daily_cost(yesterday)

        monthly_cost = self.get_monthly_cost()

        is_anomaly = daily_cost > self.threshold
        increase_percent = round(
            (daily_cost - yesterday_cost) / yesterday_cost * 100 if yesterday_cost > 0 else 0, 2
        )

        result = {
            'is_anomaly': is_anomaly,
            'today_cost': daily_cost,
            'yesterday_cost': yesterday_cost,
            'monthly_cost': monthly_cost,
            'threshold': self.threshold,
            'date': today,
            'increase_percent': increase_percent
        }

        return is_anomaly, result

    def set_threshold(self, amount: float) -> None:
        try:
            self.ssm_client.put_parameter(
                Name='/guardian/cost-threshold',
                Value=str(amount),
                Type='String',
                Overwrite=True
            )
            self.threshold = amount
        except Exception as e:
            logger.error("Error setting threshold: %s", e)

    def get_threshold(self) -> float:
        try:
            response = self.ssm_client.get_parameter(
                Name='/guardian/cost-threshold'
            )
            self.threshold = float(response['Parameter']['Value'])
            return self.threshold
        except self.ssm_client.exceptions.ParameterNotFound:
            return self.threshold
        except Exception as e:
            logger.warning("Error getting threshold from SSM: %s", e)
            return self.threshold
