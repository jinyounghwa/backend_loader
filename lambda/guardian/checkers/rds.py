"""RDS security checker for AWS Guardian."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class RDSChecker(BaseChecker):
    """Detect RDS security anomalies: public accessibility, encryption, backups."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients or {}, config or {}, account_id, credentials)
        self.rds_client = self.clients.get("rds")
        if self.rds_client is None:
            import boto3

            self.rds_client = boto3.client("rds", **Config.get_boto3_kwargs())

    def check(self) -> CheckResult:
        """Check all RDS instances for security anomalies."""
        self._log_check_start("RDS")
        try:
            instances = self._get_rds_instances()
            return self._analyze_instances(instances)
        except ClientError as e:
            return self._handle_client_error("RDS", e)
        except Exception as e:
            return self._handle_generic_error("RDS", e)

    def _get_rds_instances(self) -> List[Dict[str, Any]]:
        """Fetch all RDS instances."""
        instances = []
        try:
            paginator = self.rds_client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                instances.extend(page.get("DBInstances", []))
        except ClientError as e:
            logger.error("ClientError fetching RDS instances: %s", e)
        except Exception as e:
            logger.error("Error fetching RDS instances: %s", e)
        return instances

    def _analyze_instances(self, instances: List[Dict[str, Any]]) -> CheckResult:
        """Analyze RDS instances for security issues."""
        anomalies: List[str] = []
        details: Dict[str, Any] = {
            "is_anomaly": False,
            "publicly_accessible": [],
            "unencrypted": [],
            "backup_disabled": [],
            "iam_auth_disabled": [],
            "cloudwatch_logs_disabled": [],
            "instance_count": len(instances),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for instance in instances:
            db_id = instance.get("DBInstanceIdentifier", "unknown")
            instance_type = instance.get("Engine", "unknown")

            # Check 1: Public accessibility
            if instance.get("PubliclyAccessible", False):
                anomalies.append(
                    f"RDS instance {db_id} ({instance_type}) is publicly accessible"
                )
                details["publicly_accessible"].append(db_id)
                details["is_anomaly"] = True

            # Check 2: Storage encryption
            if not instance.get("StorageEncrypted", False):
                anomalies.append(
                    f"RDS instance {db_id} ({instance_type}) has encryption disabled"
                )
                details["unencrypted"].append(db_id)
                details["is_anomaly"] = True

            # Check 3: Backup retention
            backup_retention = instance.get("BackupRetentionPeriod", 0)
            if backup_retention < 7:
                anomalies.append(
                    f"RDS instance {db_id} ({instance_type}) backup retention ({backup_retention}d) < 7 days"
                )
                details["backup_disabled"].append(db_id)

            # Check 4: IAM authentication
            if not instance.get("IAMDatabaseAuthenticationEnabled", False):
                anomalies.append(
                    f"RDS instance {db_id} ({instance_type}) has IAM auth disabled"
                )
                details["iam_auth_disabled"].append(db_id)

            # Check 5: CloudWatch Logs
            enabled_logs = instance.get("EnabledCloudwatchLogsExports", [])
            if not enabled_logs:
                anomalies.append(
                    f"RDS instance {db_id} ({instance_type}) has no CloudWatch logs enabled"
                )
                details["cloudwatch_logs_disabled"].append(db_id)

        if not anomalies:
            return CheckResult(
                severity="INFO",
                title="RDS Security Check",
                message=f"All {len(instances)} RDS instances are secure",
                details=details,
            )

        # Determine overall severity
        critical_count = len(details["publicly_accessible"])
        high_count = (
            len(details["unencrypted"]) + len(details["iam_auth_disabled"])
        )
        low_count = len(details["backup_disabled"]) + len(
            details["cloudwatch_logs_disabled"]
        )

        if critical_count > 0:
            severity = "HIGH"
        elif high_count > 0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        message = f"Found {len(anomalies)} security issues in {len(instances)} RDS instances"
        return CheckResult(
            severity=severity,
            title="RDS Security Issues Detected",
            message=message,
            details=details,
            suggested_action="Review and remediate RDS security configurations",
        )
