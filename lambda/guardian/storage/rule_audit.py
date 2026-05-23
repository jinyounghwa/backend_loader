"""Rule Audit Log Repository for Sprint 35 Phase 4

Manages audit logging for all rule changes.
Tracks CREATE, UPDATE, DELETE, DEPLOY, ROLLBACK actions with complete audit trail.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import boto3
import uuid
from botocore.exceptions import ClientError


@dataclass
class AuditLog:
    """Represents an audit log entry"""
    rule_id: str
    audit_id: str
    action: str  # CREATE, UPDATE, DELETE, DEPLOY, ROLLBACK
    timestamp: str  # ISO format
    user_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: str = "SUCCESS"  # SUCCESS, FAILURE
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class RuleAuditRepository:
    """Repository for managing rule audit logs"""

    def __init__(self, table_name: str):
        """
        Initialize audit repository
        Args:
            table_name: DynamoDB table name for audit logs
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def log_action(
        self,
        rule_id: str,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log a rule action
        Args:
            rule_id: ID of the rule being audited
            action: Action type (CREATE, UPDATE, DELETE, DEPLOY, ROLLBACK)
            user_id: User performing the action
            details: Additional details about the action
            status: SUCCESS or FAILURE
            error_message: Error message if status is FAILURE
        Returns:
            Created AuditLog object
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            # Validate action
            valid_actions = ["CREATE", "UPDATE", "DELETE", "DEPLOY", "ROLLBACK"]
            if action not in valid_actions:
                action = "UPDATE"  # Default to UPDATE if invalid

            log = AuditLog(
                rule_id=rule_id,
                audit_id=audit_id,
                action=action,
                timestamp=timestamp,
                user_id=user_id,
                details=details,
                status=status,
                error_message=error_message
            )

            self.table.put_item(Item=log.to_dict())
            return log

        except ClientError as e:
            print(f"Error logging action: {e}")
            raise

    def get_audit_log(self, rule_id: str, audit_id: str) -> Optional[AuditLog]:
        """
        Get a specific audit log entry
        Args:
            rule_id: Rule ID
            audit_id: Audit log ID
        Returns:
            AuditLog object or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    "rule_id": rule_id,
                    "audit_id": audit_id
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return AuditLog(
                rule_id=item["rule_id"],
                audit_id=item["audit_id"],
                action=item["action"],
                timestamp=item["timestamp"],
                user_id=item.get("user_id"),
                details=item.get("details"),
                status=item.get("status", "SUCCESS"),
                error_message=item.get("error_message")
            )

        except ClientError as e:
            print(f"Error getting audit log: {e}")
            return None

    def list_audit_logs(
        self,
        rule_id: str,
        limit: int = 20,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[AuditLog]:
        """
        Get audit logs for a rule
        Args:
            rule_id: Rule ID
            limit: Maximum number of logs to return
            start_time: ISO format start time (optional)
            end_time: ISO format end time (optional)
        Returns:
            List of AuditLog objects (most recent first)
        """
        try:
            query_params = {
                "KeyConditionExpression": "rule_id = :rid",
                "ExpressionAttributeValues": {":rid": rule_id},
                "ScanIndexForward": False,  # Most recent first
                "Limit": limit
            }

            # Add time range filter if provided
            if start_time or end_time:
                conditions = []
                if start_time:
                    conditions.append("timestamp >= :start")
                    query_params["ExpressionAttributeValues"][":start"] = start_time

                if end_time:
                    conditions.append("timestamp <= :end")
                    query_params["ExpressionAttributeValues"][":end"] = end_time

                if conditions:
                    key_condition = query_params["KeyConditionExpression"]
                    query_params["KeyConditionExpression"] = key_condition + " AND " + " AND ".join(conditions)

            response = self.table.query(**query_params)

            logs = []
            for item in response.get("Items", []):
                log = AuditLog(
                    rule_id=item["rule_id"],
                    audit_id=item["audit_id"],
                    action=item["action"],
                    timestamp=item["timestamp"],
                    user_id=item.get("user_id"),
                    details=item.get("details"),
                    status=item.get("status", "SUCCESS"),
                    error_message=item.get("error_message")
                )
                logs.append(log)

            return logs

        except ClientError as e:
            print(f"Error listing audit logs: {e}")
            return []

    def get_audit_summary(self, rule_id: str) -> Dict[str, Any]:
        """
        Get audit summary for a rule
        Args:
            rule_id: Rule ID
        Returns:
            Dictionary with audit summary
        """
        try:
            logs = self.list_audit_logs(rule_id, limit=100)

            # Count actions
            action_counts = {}
            status_counts = {"SUCCESS": 0, "FAILURE": 0}

            for log in logs:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
                status_counts[log.status] = status_counts.get(log.status, 0) + 1

            return {
                "rule_id": rule_id,
                "total_logs": len(logs),
                "action_counts": action_counts,
                "status_counts": status_counts,
                "first_action_date": logs[-1].timestamp if logs else None,
                "last_action_date": logs[0].timestamp if logs else None,
            }

        except Exception as e:
            print(f"Error getting audit summary: {e}")
            return {
                "rule_id": rule_id,
                "total_logs": 0,
                "action_counts": {},
                "status_counts": {}
            }

    def count_actions(self, rule_id: str, action: str) -> int:
        """
        Count how many times an action was performed
        Args:
            rule_id: Rule ID
            action: Action type to count
        Returns:
            Count of actions
        """
        try:
            logs = self.list_audit_logs(rule_id, limit=100)
            return sum(1 for log in logs if log.action == action)

        except Exception as e:
            print(f"Error counting actions: {e}")
            return 0
