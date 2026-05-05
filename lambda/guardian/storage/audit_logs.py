"""Audit log storage for guardian admin actions"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class AuditLogStorage:
    def __init__(self, table_name: str = "guardian-audit-logs"):
        self.table_name = table_name
        self._table = None

    @property
    def table(self):
        if self._table is None:
            try:
                self._table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
            except Exception as e:
                logger.error("Could not access audit log table: %s", e)
        return self._table

    def save_audit_log(
        self,
        user: str,
        action: str,
        resource: str,
        status: str = "success",
        details: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        item = {
            "user": user,
            "timestamp": timestamp,
            "action": action,
            "resource": resource,
            "status": status,
            "details": details or {},
        }

        try:
            if self.table is None:
                return {"success": False, "error": "DynamoDB table unavailable"}
            self.table.put_item(Item=item)
            return {"success": True, "timestamp": timestamp}
        except Exception as e:
            logger.error("Error saving audit log: %s", e)
            return {"success": False, "error": str(e)}

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            if self.table is None:
                return []
            response = self.table.scan(Limit=limit)
            return response.get("Items", [])
        except Exception as e:
            logger.error("Error retrieving audit logs: %s", e)
            return []

    def get_audit_logs_by_user(self, user: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            if self.table is None:
                return []
            from boto3.dynamodb.conditions import Key

            response = self.table.query(
                KeyConditionExpression=Key("user").eq(user),
                Limit=limit,
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error("Error querying audit logs for user %s: %s", user, e)
            return []
