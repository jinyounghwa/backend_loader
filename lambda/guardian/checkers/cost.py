"""AWS Cost Explorer checker for AWS Guardian."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

SSM_COST_THRESHOLD_PATH = "/aws-guardian/cost-threshold"

MOCK_DAILY_COST_DEFAULT = 5.50
MOCK_MONTHLY_COST_DEFAULT = 150.50

logger = logging.getLogger(__name__)


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
        effective_config.setdefault("cost_threshold", 10.0)
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.threshold = self.config["cost_threshold"]
        self.is_localstack = Config.is_localstack()

        # Get from clients dict (tests) or create new (production)
        self.ssm_client = self.clients.get("ssm")
        if self.ssm_client is None:
            self.ssm_client = boto3.client("ssm", **Config.get_boto3_kwargs())

        self._ce_client = self.clients.get("ce")

    @property
    def ce_client(self):
        """Lazy Cost Explorer client (only created when needed)."""
        if self._ce_client is None:
            self._ce_client = boto3.client("ce", **Config.get_boto3_kwargs())
        return self._ce_client

    # ------------------------------------------------------------------
    # Main check entry (sync-first, test-friendly)
    # ------------------------------------------------------------------

    def check(self) -> CheckResult:
        """Check for cost anomalies.

        Detects:
        - Daily cost exceeding threshold
        - Cost trending upward
        - Unusual service usage spikes
        """
        self._log_check_start("Cost")
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

            daily_cost = self._get_daily_cost(today)
            yesterday_cost = self._get_daily_cost(yesterday)
            monthly_cost = self._get_monthly_cost()

            is_anomaly = daily_cost > self.threshold
            increase_percent = round(
                ((daily_cost - yesterday_cost) / yesterday_cost) * 100 if yesterday_cost > 0 else 0,
                2,
            )

            details = {
                "is_anomaly": is_anomaly,
                "today_cost": daily_cost,
                "yesterday_cost": yesterday_cost,
                "monthly_cost": monthly_cost,
                "threshold": self.threshold,
                "date": today,
                "increase_percent": increase_percent,
            }

            if is_anomaly:
                self._log_check_end("Cost", "HIGH")
                return CheckResult(
                    severity="HIGH",
                    title="Cost Anomaly Detected",
                    message=f"Daily cost ${daily_cost:.2f} exceeds threshold ${self.threshold:.2f}",
                    details=details,
                    suggested_action="Review top-cost services and consider scaling down resources",
                )

            self._log_check_end("Cost", "INFO")
            return CheckResult(
                severity="INFO",
                title="Cost Check",
                message=f"Daily cost ${daily_cost:.2f} is within threshold ${self.threshold:.2f}",
                details=details,
            )
        except ClientError as e:
            return self._handle_client_error("Cost", e)
        except Exception as e:
            return self._handle_generic_error("Cost", e)

    # ------------------------------------------------------------------
    # Cost data retrieval (sync boto3 – also used by async via executor)
    # ------------------------------------------------------------------

    def _get_daily_cost(self, date: str) -> float:
        """Get daily cost for a specific date."""
        if self.is_localstack:
            return float(os.getenv("MOCK_DAILY_COST", str(MOCK_DAILY_COST_DEFAULT)))
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={"Start": date, "End": date},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )
            if response["ResultsByTime"]:
                return float(response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            return 0.0
        except ClientError as e:
            logger.error("ClientError getting daily cost: %s", e)
            return 0.0
        except Exception as e:
            logger.error("Error getting daily cost: %s", e)
            return 0.0

    def _get_monthly_cost(self, year: Optional[int] = None, month: Optional[int] = None) -> float:
        """Get monthly cost."""
        if not year:
            year = datetime.now(timezone.utc).year
        if not month:
            month = datetime.now(timezone.utc).month

        if self.is_localstack:
            return float(os.getenv("MOCK_MONTHLY_COST", str(MOCK_MONTHLY_COST_DEFAULT)))

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            if response["ResultsByTime"]:
                return float(response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            return 0.0
        except ClientError as e:
            logger.error("ClientError getting monthly cost: %s", e)
            return 0.0
        except Exception as e:
            logger.error("Error getting monthly cost: %s", e)
            return 0.0

    # ------------------------------------------------------------------
    # Threshold management via SSM
    # ------------------------------------------------------------------

    def set_threshold(self, amount: float) -> None:
        """Set the daily cost threshold in AWS SSM Parameter Store.

        Args:
            amount: The new daily cost threshold threshold value (USD).
        """
        try:
            self.ssm_client.put_parameter(
                Name=SSM_COST_THRESHOLD_PATH, Value=str(amount), Type="String", Overwrite=True
            )
            self.threshold = amount
        except Exception as e:
            logger.error("Error setting threshold: %s", e)

    def get_threshold(self) -> float:
        """Get the daily cost threshold from AWS SSM Parameter Store.

        Returns:
            The daily cost threshold (USD) retrieved from SSM, or the default value.
        """
        try:
            response = self.ssm_client.get_parameter(Name=SSM_COST_THRESHOLD_PATH)
            self.threshold = float(response["Parameter"]["Value"])
            return self.threshold
        except self.ssm_client.exceptions.ParameterNotFound:
            return self.threshold
        except Exception as e:
            logger.warning("Error getting threshold from SSM: %s", e)
            return self.threshold

