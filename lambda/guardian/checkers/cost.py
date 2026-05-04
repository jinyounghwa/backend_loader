"""AWS Cost Explorer checker for AWS Guardian"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)

MOCK_DAILY_COST_DEFAULT = 5.50
MOCK_MONTHLY_COST_DEFAULT = 150.50


class CostChecker(BaseChecker):
    """Detect cost anomalies by comparing daily spend against a threshold."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        effective_config = config or {}
        effective_config.setdefault('cost_threshold', 10.0)
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.threshold = self.config['cost_threshold']
        self.is_localstack = Config.is_localstack()
        self.ssm_client = AWSClientProvider.get_client('ssm')

        if not self.is_localstack:
            self.ce_client = AWSClientProvider.get_client('ce')
        else:
            self.ce_client = None

    def check(self) -> CheckResult:
        """Run cost anomaly check and return unified CheckResult."""
        self._log_check_start('Cost')

        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            daily_cost = self._get_daily_cost(today)

            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
            yesterday_cost = self._get_daily_cost(yesterday)

            monthly_cost = self._get_monthly_cost()

            is_anomaly = daily_cost > self.threshold
            increase_percent = round(
                (daily_cost - yesterday_cost) / yesterday_cost * 100 if yesterday_cost > 0 else 0, 2
            )

            details = {
                'is_anomaly': is_anomaly,
                'today_cost': daily_cost,
                'yesterday_cost': yesterday_cost,
                'monthly_cost': monthly_cost,
                'threshold': self.threshold,
                'date': today,
                'increase_percent': increase_percent,
            }

            if is_anomaly:
                self._log_check_end('Cost', 'HIGH')
                return CheckResult(
                    severity='HIGH',
                    title='Cost Anomaly Detected',
                    message=f"Daily cost ${daily_cost:.2f} exceeds threshold ${self.threshold:.2f}",
                    details=details,
                    suggested_action='Review top-cost services and consider scaling down resources',
                )

            self._log_check_end('Cost', 'INFO')
            return CheckResult(
                severity='INFO',
                title='Cost Check',
                message=f"Daily cost ${daily_cost:.2f} is within threshold ${self.threshold:.2f}",
                details=details,
            )

        except Exception as e:
            self._log_error('Cost', e)
            return CheckResult.error(
                'Cost Check Failed',
                f'Failed to check costs: {str(e)}',
            )

    def _get_daily_cost(self, date: str) -> float:
        if self.is_localstack:
            return float(os.getenv('MOCK_DAILY_COST', str(MOCK_DAILY_COST_DEFAULT)))

        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': date, 'End': date},
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            if response['ResultsByTime']:
                return float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            return 0.0
        except Exception as e:
            logger.error("Error getting daily cost: %s", e)
            return 0.0

    def _get_monthly_cost(self, year: int = None, month: int = None) -> float:
        if not year:
            year = datetime.now(timezone.utc).year
        if not month:
            month = datetime.now(timezone.utc).month

        if self.is_localstack:
            return float(os.getenv('MOCK_MONTHLY_COST', str(MOCK_MONTHLY_COST_DEFAULT)))

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            if response['ResultsByTime']:
                return float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            return 0.0
        except Exception as e:
            logger.error("Error getting monthly cost: %s", e)
            return 0.0

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
            response = self.ssm_client.get_parameter(Name='/guardian/cost-threshold')
            self.threshold = float(response['Parameter']['Value'])
            return self.threshold
        except self.ssm_client.exceptions.ParameterNotFound:
            return self.threshold
        except Exception as e:
            logger.warning("Error getting threshold from SSM: %s", e)
            return self.threshold

    def check_cost_anomaly(self):
        """Backward-compatible entry point returning (is_anomaly, data) tuple."""
        result = self.check()
        return (result.severity != 'INFO', result.details)
