"""AWS Cost Explorer checker for AWS Guardian"""
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

class CostChecker:
    def __init__(self, cost_threshold: float = 10.0):
        """Initialize cost checker with optional threshold in USD"""
        self.ce_client = boto3.client('ce')
        self.threshold = cost_threshold
        self.ssm_client = boto3.client('ssm')

    def get_daily_cost(self, date: str = None) -> float:
        """Get cost for a specific day (YYYY-MM-DD format)"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        try:
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
            return 0.0

    def get_monthly_cost(self, year: int = None, month: int = None) -> float:
        """Get cost for a specific month"""
        if not year:
            year = datetime.utcnow().year
        if not month:
            month = datetime.utcnow().month

        start_date = f"{year}-{month:02d}-01"

        # Calculate end date
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        try:
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
            return 0.0

    def check_cost_anomaly(self) -> Tuple[bool, Dict[str, Any]]:
        """Check if today's cost exceeds threshold"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        daily_cost = self.get_daily_cost(today)

        # Get yesterday's cost for comparison
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
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
                Name='/aws-guardian/cost-threshold',
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
                Name='/aws-guardian/cost-threshold'
            )
            self.threshold = float(response['Parameter']['Value'])
            return self.threshold
        except:
            return self.threshold
