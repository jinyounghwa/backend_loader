"""CloudWatch metrics helper for AWS Guardian performance monitoring"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class CloudWatchMetrics:
    """Emit custom metrics to CloudWatch for Lambda performance monitoring"""

    NAMESPACE = "aws-guardian"

    # Metric names
    METRICS = {
        "Duration": "Milliseconds",
        "ColdStartDuration": "Milliseconds",
        "DynamoDBQueryTime": "Milliseconds",
        "GeminiAPILatency": "Milliseconds",
        "MemoryUsed": "Megabytes",
        "EventsProcessed": "Count",
        "ErrorCount": "Count",
    }

    @classmethod
    def emit_metric(
        cls,
        metric_name: str,
        value: float,
        unit: Optional[str] = None,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Emit a single metric to CloudWatch

        Args:
            metric_name: Name of the metric
            value: Numeric value
            unit: Unit of measurement (default from METRICS dict)
            dimensions: Optional dimensions (e.g., {"CheckType": "EC2"})
        """
        if metric_name not in cls.METRICS:
            logger.warning("Unknown metric: %s", metric_name)
            return

        try:
            cloudwatch = AWSClientProvider.get_client("cloudwatch")

            metric_data = {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit or cls.METRICS[metric_name],
                "Timestamp": datetime.now(timezone.utc),
            }

            if dimensions:
                metric_data["Dimensions"] = [{"Name": k, "Value": v} for k, v in dimensions.items()]

            cloudwatch.put_metric_data(Namespace=cls.NAMESPACE, MetricData=[metric_data])

            logger.debug("Emitted metric: %s=%s %s", metric_name, value, metric_data["Unit"])
        except Exception as e:
            logger.error("Failed to emit metric %s: %s", metric_name, e)

    @classmethod
    def emit_batch(cls, metrics: Dict[str, Any]) -> None:
        """
        Emit multiple metrics in one call

        Args:
            metrics: Dict of {metric_name: value}
        """
        if not metrics:
            return

        try:
            cloudwatch = AWSClientProvider.get_client("cloudwatch")

            metric_data = []
            for metric_name, value in metrics.items():
                if metric_name not in cls.METRICS:
                    logger.warning("Unknown metric: %s", metric_name)
                    continue

                metric_data.append(
                    {
                        "MetricName": metric_name,
                        "Value": value,
                        "Unit": cls.METRICS[metric_name],
                        "Timestamp": datetime.now(timezone.utc),
                    }
                )

            if metric_data:
                cloudwatch.put_metric_data(Namespace=cls.NAMESPACE, MetricData=metric_data)
                logger.debug("Emitted %d metrics", len(metric_data))
        except Exception as e:
            logger.error("Failed to emit batch metrics: %s", e)

    @staticmethod
    @contextmanager
    def timer(metric_name: str, dimensions: Optional[Dict[str, str]] = None):
        """
        Context manager to measure execution time

        Usage:
            with CloudWatchMetrics.timer("DynamoDBQueryTime"):
                response = dynamodb.query(...)
        """
        start_time = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            CloudWatchMetrics.emit_metric(metric_name, elapsed_ms, dimensions=dimensions)
