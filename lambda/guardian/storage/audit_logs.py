"""
Audit log storage for guardian admin actions
"""

import json
from datetime import datetime
from typing import Optional

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("guardian-audit-logs")


def save_audit_log(
    user: str,
    action: str,
    resource: str,
    status: str = "success",
    details: Optional[dict] = None,
) -> dict:
    """Save audit log entry for admin actions"""
    timestamp = datetime.utcnow().isoformat()

    item = {
        "user": user,
        "timestamp": timestamp,
        "action": action,
        "resource": resource,
        "status": status,
        "details": json.dumps(details or {}),
    }

    try:
        table.put_item(Item=item)
        return {"success": True, "timestamp": timestamp}
    except Exception as e:
        print(f"Error saving audit log: {e}")
        return {"success": False, "error": str(e)}


def get_audit_logs(limit: int = 100) -> list:
    """Get recent audit logs"""
    try:
        response = table.scan(Limit=limit)
        return response.get("Items", [])
    except Exception as e:
        print(f"Error retrieving audit logs: {e}")
        return []


def get_audit_logs_by_user(user: str, limit: int = 50) -> list:
    """Get audit logs for specific user"""
    try:
        response = table.query(
            KeyConditionExpression="usr = :user",
            ExpressionAttributeValues={":user": user},
            Limit=limit,
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error querying audit logs for user {user}: {e}")
        return []
