"""
Sprint 31 Phase 3: WebSocket Audit Logging
Event logging utility for tracking WebSocket connections, messages, and broadcasts
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3


class AuditLogger:
    """WebSocket event audit logging to DynamoDB"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table_name = os.getenv("AUDIT_LOGS_TABLE")
        self.enabled = os.getenv("AUDIT_LOGS_ENABLED", "true").lower() == "true"
        self.ttl_days = int(os.getenv("TTL_DAYS", "90"))

        if self.table_name and self.enabled:
            self.table = self.dynamodb.Table(self.table_name)
        else:
            self.table = None

    def _get_expiration_timestamp(self) -> int:
        """Get Unix timestamp for TTL expiration (90 days from now)"""
        expiration = datetime.utcnow() + timedelta(days=self.ttl_days)
        return int(expiration.timestamp())

    def _put_item(self, connection_id: str, timestamp: str, event_data: Dict[str, Any], account_id: str = "current") -> bool:
        """Put audit log item into DynamoDB"""
        if not self.table:
            return False

        try:
            item = {
                "connection_id": connection_id,
                "timestamp": timestamp,
                "account_id": account_id,
                "expiration_time": self._get_expiration_timestamp(),
                **event_data,
            }
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error writing audit log: {e}")
            return False

    @staticmethod
    def log_connect(
        connection_id: str,
        user_id: Optional[str] = None,
        account_id: str = "current",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log $connect event"""
        logger = AuditLogger()
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_data = {
            "event_type": "$connect",
            "user_id": user_id or "anonymous",
            "status": status,
            "details": details or {},
        }
        return logger._put_item(connection_id, timestamp, event_data, account_id)

    @staticmethod
    def log_disconnect(
        connection_id: str,
        user_id: Optional[str] = None,
        account_id: str = "current",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log $disconnect event"""
        logger = AuditLogger()
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_data = {
            "event_type": "$disconnect",
            "user_id": user_id or "anonymous",
            "status": status,
            "details": details or {},
        }
        return logger._put_item(connection_id, timestamp, event_data, account_id)

    @staticmethod
    def log_message(
        connection_id: str,
        user_id: Optional[str] = None,
        message_type: str = "unknown",
        account_id: str = "current",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log message processing event"""
        logger = AuditLogger()
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_data = {
            "event_type": "message",
            "user_id": user_id or "anonymous",
            "message_type": message_type,
            "status": status,
            "details": details or {},
        }
        return logger._put_item(connection_id, timestamp, event_data, account_id)

    @staticmethod
    def log_broadcast(
        connection_id: str,
        user_id: Optional[str] = None,
        threat_score: int = 0,
        account_id: str = "current",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log threat broadcast event"""
        logger = AuditLogger()
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_data = {
            "event_type": "broadcast",
            "user_id": user_id or "system",
            "threat_score": threat_score,
            "status": status,
            "details": details or {},
        }
        return logger._put_item(connection_id, timestamp, event_data, account_id)

    @staticmethod
    def query_connection_logs(connection_id: str) -> list:
        """Query all logs for a specific connection"""
        logger = AuditLogger()
        if not logger.table:
            return []

        try:
            response = logger.table.query(
                KeyConditionExpression="connection_id = :cid",
                ExpressionAttributeValues={":cid": connection_id},
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error querying audit logs: {e}")
            return []

    @staticmethod
    def query_with_filters(
        connection_id: Optional[str] = None,
        account_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> list:
        """Query audit logs with filtering by connection/account, time range, and event type"""
        logger = AuditLogger()
        if not logger.table:
            return []

        try:
            # Query by account_id using GSI
            if account_id and account_id != "all":
                response = logger.table.query(
                    IndexName="AccountIdTimestampIndex",
                    KeyConditionExpression="account_id = :aid AND #ts BETWEEN :start AND :end",
                    ExpressionAttributeNames={"#ts": "timestamp"},
                    ExpressionAttributeValues={
                        ":aid": account_id,
                        ":start": start_time or "1970-01-01T00:00:00Z",
                        ":end": end_time or "2099-12-31T23:59:59Z",
                    },
                )
                logs = response.get("Items", [])
            # Query by connection_id (primary key)
            elif connection_id and connection_id != "all":
                logs = AuditLogger.query_connection_logs(connection_id)
            else:
                # Return empty for now (full scan not implemented)
                return []

            if not logs:
                return []

            filtered_logs = logs

            # Filter by start_time (ISO 8601 string comparison)
            if start_time:
                filtered_logs = [log for log in filtered_logs if log.get("timestamp", "") >= start_time]

            # Filter by end_time (ISO 8601 string comparison)
            if end_time:
                filtered_logs = [log for log in filtered_logs if log.get("timestamp", "") <= end_time]

            # Filter by event_type
            if event_type:
                filtered_logs = [log for log in filtered_logs if log.get("event_type") == event_type]

            return filtered_logs
        except Exception as e:
            print(f"Error querying audit logs with filters: {e}")
            return []
