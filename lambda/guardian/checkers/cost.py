"""AWS Cost Explorer checker for AWS Guardian"""
import boto3
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import Config

class CostChecker:
    def __init__(self, cost_threshold: float = 10.0):
        boto3_kwargs = Config.get_boto3_kwargs()
        self.threshold = cost_threshold
        self.ssm_client = boto3.client('ssm', **boto3_kwargs)
        self.is_localstack = Config.is_localstack()

        if not self.is_localstack:
            self.ce_client = boto3.client('ce', **boto3_kwargs)
        else:
            self.ce_client = None

    def get_daily_cost(self, date: str = None) -> float:
        """Get cost for a specific day (YYYY-MM-DD format)"""
        if not date:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        try:
            # LocalStack doesn't support Cost Explorer, return mock data
            if self.is_localstack:
                mock_cost = float(os.getenv('MOCK_DAILY_COST', '5.50'))
                print(f"[LocalStack] Returning mock daily cost for {date}: ${mock_cost}")
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
            print(f"Error getting daily cost: {e}")
            # Return mock data in LocalStack
            if self.is_localstack:
                return float(os.getenv('MOCK_DAILY_COST', '5.50'))
            return 0.0

    def get_monthly_cost(self, year: int = None, month: int = None) -> float:
        """Get cost for a specific month"""
        if not year:
            year = datetime.now(timezone.utc).year
        if not month:
            month = datetime.now(timezone.utc).month

        start_date = f"{year}-{month:02d}-01"

        # Calculate end date
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        try:
            # LocalStack doesn't support Cost Explorer, return mock data
            if self.is_localstack:
                mock_cost = float(os.getenv('MOCK_MONTHLY_COST', '150.50'))
                print(f"[LocalStack] Returning mock monthly cost for {year}-{month:02d}: ${mock_cost}")
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
            print(f"Error getting monthly cost: {e}")
            # Return mock data in LocalStack
            if self.is_localstack:
                return 150.50
            return 0.0

    def check_cost_anomaly(self) -> Tuple[bool, Dict[str, Any]]:
        """Check if today's cost exceeds threshold"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        daily_cost = self.get_daily_cost(today)

        # Get yesterday's cost for comparison
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_cost = self.get_daily_cost(yesterday)

        # Get monthly cost
        monthly_cost = self.get_monthly_cost()

        is_anomaly = daily_cost > self.threshold

        result = {
            'is_anomaly': is_anomaly,
            'today_cost': daily_cost,
            'yesterday_cost': yesterday_cost,
            'monthly_cost': monthly_cost,
            'threshold': self.threshold,
            'date': today,
            'increase_percent': round((daily_cost - yesterday_cost) / yesterday_cost * 100 if yesterday_cost > 0 else 0, 2)
        }

        return is_anomaly, result

    def set_threshold(self, amount: float) -> None:
        """Set cost threshold in Parameter Store"""
        try:
            self.ssm_client.put_parameter(
                Name='/guardian/cost-threshold',
                Value=str(amount),
                Type='String',
                Overwrite=True
            )
            self.threshold = amount
        except Exception as e:
            print(f"Error setting threshold: {e}")

    def get_threshold(self) -> float:
        """Get cost threshold from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/guardian/cost-threshold'
            )
            self.threshold = float(response['Parameter']['Value'])
            return self.threshold
        except:
            return self.threshold
