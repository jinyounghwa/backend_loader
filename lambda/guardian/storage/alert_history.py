"""Alert History Storage for Sprint 33 Phase 3

Stores alert sending history for audit trail and analytics.
Tracks which alerts were successfully sent vs. failed.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


class AlertHistory:
    """Data class for alert history record"""

    def __init__(
        self,
        alert_id: str,
        rule_id: str,
        severity: int,
        account_id: str,
        timestamp: str,
        message: str,
        status: str = "sent",  # sent, failed, retried
        created_at: Optional[str] = None,
    ):
        self.alert_id = alert_id
        self.rule_id = rule_id
        self.severity = severity
        self.account_id = account_id
        self.timestamp = timestamp
        self.message = message
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "account_id": self.account_id,
            "timestamp": self.timestamp,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dynamodb_item(item: Dict[str, Any]) -> "AlertHistory":
        """Create from DynamoDB item"""
        return AlertHistory(
            alert_id=item["alert_id"],
            rule_id=item["rule_id"],
            severity=item["severity"],
            account_id=item["account_id"],
            timestamp=item["timestamp"],
            message=item["message"],
            status=item.get("status", "sent"),
            created_at=item.get("created_at"),
        )


class AlertHistoryRepository:
    """Repository for managing alert history in DynamoDB"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def save_alert(self, alert_history: AlertHistory) -> bool:
        """Save an alert to history"""
        try:
            self.table.put_item(Item=alert_history.to_dynamodb_item())
            return True
        except ClientError as e:
            print(f"Error saving alert history: {e}")
            return False

    def get_alert(self, alert_id: str) -> Optional[AlertHistory]:
        """Get an alert from history"""
        try:
            response = self.table.get_item(Key={"alert_id": alert_id})
            if "Item" not in response:
                return None
            return AlertHistory.from_dynamodb_item(response["Item"])
        except ClientError as e:
            print(f"Error getting alert: {e}")
            return None

    def list_alerts_by_rule(
        self, rule_id: str, limit: int = 100
    ) -> List[AlertHistory]:
        """List alerts for a specific rule"""
        try:
            response = self.table.query(
                IndexName="RuleIdIndex",
                KeyConditionExpression="rule_id = :rid",
                ExpressionAttributeValues={":rid": rule_id},
                Limit=limit,
            )
            return [
                AlertHistory.from_dynamodb_item(item) for item in response.get("Items", [])
            ]
        except ClientError as e:
            print(f"Error listing alerts by rule: {e}")
            return []

    def list_alerts_by_account(
        self, account_id: str, limit: int = 100
    ) -> List[AlertHistory]:
        """List alerts for a specific account"""
        try:
            response = self.table.query(
                IndexName="AccountIdIndex",
                KeyConditionExpression="account_id = :aid",
                ExpressionAttributeValues={":aid": account_id},
                Limit=limit,
            )
            return [
                AlertHistory.from_dynamodb_item(item) for item in response.get("Items", [])
            ]
        except ClientError as e:
            print(f"Error listing alerts by account: {e}")
            return []

    def list_failed_alerts(self, limit: int = 100) -> List[AlertHistory]:
        """List all failed alerts for retry"""
        try:
            response = self.table.scan(
                FilterExpression="status = :status",
                ExpressionAttributeValues={":status": "failed"},
                Limit=limit,
            )
            return [
                AlertHistory.from_dynamodb_item(item) for item in response.get("Items", [])
            ]
        except ClientError as e:
            print(f"Error listing failed alerts: {e}")
            return []

    def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update alert status"""
        try:
            self.table.update_item(
                Key={"alert_id": alert_id},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": status},
            )
            return True
        except ClientError as e:
            print(f"Error updating alert status: {e}")
            return False
