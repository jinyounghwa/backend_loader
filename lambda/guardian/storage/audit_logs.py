"""
Audit log storage for guardian admin actions
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)

TABLE_NAME = "guardian-audit-logs"


def _get_table():
    """Lazy-load DynamoDB table via AWSClientProvider (respects LocalStack config)."""
    try:
        return AWSClientProvider.get_resource("dynamodb").Table(TABLE_NAME)
    except Exception as e:
        logger.error("Could not access audit log table: %s", e)
        return None


def save_audit_log(
    user: str,
    action: str,
    resource: str,
    status: str = "success",
    details: Optional[dict] = None,
) -> dict:
    """Save audit log entry for admin actions"""
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "user": user,
        "timestamp": timestamp,
        "action": action,
        "resource": resource,
        "status": status,
        "details": json.dumps(details or {}),
    }

    try:
        table = _get_table()
        if table is None:
            return {"success": False, "error": "DynamoDB table unavailable"}
        table.put_item(Item=item)
        return {"success": True, "timestamp": timestamp}
    except Exception as e:
        logger.error("Error saving audit log: %s", e)
        return {"success": False, "error": str(e)}


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent audit logs"""
    try:
        table = _get_table()
        if table is None:
            return []
        response = table.scan(Limit=limit)
        return response.get("Items", [])
    except Exception as e:
        logger.error("Error retrieving audit logs: %s", e)
        return []


def get_audit_logs_by_user(user: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get audit logs for specific user"""
    try:
        table = _get_table()
        if table is None:
            return []
        response = table.query(
            KeyConditionExpression="user = :user",
            ExpressionAttributeValues={":user": user},
            Limit=limit,
        )
        return response.get("Items", [])
    except Exception as e:
        logger.error("Error querying audit logs for user %s: %s", user, e)
        return []
