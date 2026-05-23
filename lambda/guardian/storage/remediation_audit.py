"""Remediation Audit Log Repository (Sprint 36 Phase 2)

Tracks all automatic remediation actions for compliance and auditing.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import boto3
import uuid
from botocore.exceptions import ClientError


@dataclass
class RemediationLog:
    """Represents a recorded remediation action"""
    remediation_id: str
    threat_id: str
    rule_id: str
    action_type: str  # EC2_STOP, S3_BLOCK_PUBLIC, SG_RESTRICT, etc.
    target: str  # Instance ID, bucket name, security group ID, etc.
    success: bool
    message: str
    timestamp: str  # ISO format
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class RemediationAuditRepository:
    """Repository for managing remediation audit logs"""

    def __init__(self, table_name: str):
        """
        Initialize remediation audit repository
        Args:
            table_name: DynamoDB table name for remediation logs
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def log_remediation(
        self,
        threat_id: str,
        rule_id: str,
        action_type: str,
        target: str,
        success: bool,
        message: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> RemediationLog:
        """
        Log a remediation action
        Args:
            threat_id: ID of the detected threat
            rule_id: ID of the rule that triggered remediation
            action_type: Type of remediation (EC2_STOP, S3_BLOCK_PUBLIC, etc.)
            target: Target of remediation (instance ID, bucket name, etc.)
            success: Whether remediation succeeded
            message: Status message
            parameters: Additional parameters used for remediation
        Returns:
            Created RemediationLog object
        """
        try:
            remediation_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            log = RemediationLog(
                remediation_id=remediation_id,
                threat_id=threat_id,
                rule_id=rule_id,
                action_type=action_type,
                target=target,
                success=success,
                message=message,
                timestamp=timestamp,
                parameters=parameters
            )

            self.table.put_item(Item=log.to_dict())
            return log

        except ClientError as e:
            print(f"Error logging remediation: {e}")
            raise

    def get_remediation_log(self, remediation_id: str) -> Optional[RemediationLog]:
        """
        Get a specific remediation log entry
        Args:
            remediation_id: Remediation log ID
        Returns:
            RemediationLog object or None if not found
        """
        try:
            response = self.table.get_item(Key={"remediation_id": remediation_id})

            if "Item" not in response:
                return None

            item = response["Item"]
            return RemediationLog(
                remediation_id=item["remediation_id"],
                threat_id=item["threat_id"],
                rule_id=item["rule_id"],
                action_type=item["action_type"],
                target=item["target"],
                success=item["success"],
                message=item["message"],
                timestamp=item["timestamp"],
                parameters=item.get("parameters")
            )

        except ClientError as e:
            print(f"Error getting remediation log: {e}")
            return None

    def list_remediation_logs(
        self,
        threat_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        limit: int = 20,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[RemediationLog]:
        """
        Get remediation logs with optional filtering
        Args:
            threat_id: Filter by threat ID
            rule_id: Filter by rule ID
            limit: Maximum number of logs to return
            start_time: ISO format start time (optional)
            end_time: ISO format end time (optional)
        Returns:
            List of RemediationLog objects
        """
        try:
            # Use scan with filter expressions since we may filter by multiple fields
            filter_expressions = []
            expression_values = {}
            expression_names = {}

            if threat_id:
                filter_expressions.append("threat_id = :tid")
                expression_values[":tid"] = threat_id

            if rule_id:
                filter_expressions.append("rule_id = :rid")
                expression_values[":rid"] = rule_id

            if start_time:
                filter_expressions.append("#ts >= :start")
                expression_values[":start"] = start_time
                expression_names["#ts"] = "timestamp"

            if end_time:
                filter_expressions.append("#ts <= :end")
                expression_values[":end"] = end_time
                expression_names["#ts"] = "timestamp"

            scan_kwargs = {"Limit": limit}

            if filter_expressions:
                scan_kwargs["FilterExpression"] = " AND ".join(filter_expressions)
                if expression_values:
                    scan_kwargs["ExpressionAttributeValues"] = expression_values
                if expression_names:
                    scan_kwargs["ExpressionAttributeNames"] = expression_names

            response = self.table.scan(**scan_kwargs)

            logs = []
            for item in response.get("Items", []):
                log = RemediationLog(
                    remediation_id=item["remediation_id"],
                    threat_id=item["threat_id"],
                    rule_id=item["rule_id"],
                    action_type=item["action_type"],
                    target=item["target"],
                    success=item["success"],
                    message=item["message"],
                    timestamp=item["timestamp"],
                    parameters=item.get("parameters")
                )
                logs.append(log)

            return logs

        except ClientError as e:
            print(f"Error listing remediation logs: {e}")
            return []

    def get_remediation_summary(self, rule_id: str) -> Dict[str, Any]:
        """
        Get remediation summary for a rule
        Args:
            rule_id: Rule ID
        Returns:
            Dictionary with remediation statistics
        """
        try:
            logs = self.list_remediation_logs(rule_id=rule_id, limit=100)

            success_count = sum(1 for log in logs if log.success)
            failure_count = sum(1 for log in logs if not log.success)

            action_counts: Dict[str, int] = {}
            target_counts: Dict[str, int] = {}

            for log in logs:
                action_counts[log.action_type] = action_counts.get(log.action_type, 0) + 1
                target_counts[log.target] = target_counts.get(log.target, 0) + 1

            return {
                "rule_id": rule_id,
                "total_remediations": len(logs),
                "successful": success_count,
                "failed": failure_count,
                "success_rate": success_count / len(logs) if logs else 0,
                "action_counts": action_counts,
                "target_counts": target_counts
            }

        except Exception as e:
            print(f"Error getting remediation summary: {e}")
            return {
                "rule_id": rule_id,
                "total_remediations": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0,
                "action_counts": {},
                "target_counts": {}
            }

    def count_successful_remediations(self, rule_id: str) -> int:
        """
        Count successful remediations for a rule
        Args:
            rule_id: Rule ID
        Returns:
            Count of successful remediations
        """
        try:
            logs = self.list_remediation_logs(rule_id=rule_id, limit=100)
            return sum(1 for log in logs if log.success)

        except Exception as e:
            print(f"Error counting remediations: {e}")
            return 0
