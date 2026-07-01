"""
Sprint 32 Phase 1: Audit Logs Query API Handler
HTTP API Gateway handler for querying WebSocket audit logs
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

lambda_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lambda_dir))

from guardian.http_response import success_response, error_response
from handlers.audit_logger import AuditLogger


def handle_get_audit_logs(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /audit-logs HTTP API request

    Query Parameters:
      - account_id (optional): AWS Account ID to query (filters by account)
      - connection_id (optional): Connection ID to query (filters by connection)
      - start_time (optional): ISO 8601 start time (e.g., 2026-05-22T15:00:00Z)
      - end_time (optional): ISO 8601 end time (e.g., 2026-05-22T16:00:00Z)
      - event_type (optional): Event type filter ($connect, $disconnect, message, broadcast)

    Returns:
      {
        "statusCode": 200,
        "body": {
          "items": [...],
          "count": N,
          "total": N,
          "filters": {...}
        }
      }
    """
    try:
        # Parse query string parameters
        query_params = event.get("queryStringParameters") or {}
        account_id = query_params.get("account_id")
        connection_id = query_params.get("connection_id")
        start_time = query_params.get("start_time") or "1970-01-01T00:00:00Z"
        end_time = query_params.get("end_time") or "2099-12-31T23:59:59Z"
        event_type = query_params.get("event_type")

        # Validate: at least one filter required
        if not account_id and not connection_id:
            return error_response(400, "Missing required parameter: account_id or connection_id")

        # Query audit logs with filters
        logs = AuditLogger.query_with_filters(
            connection_id=connection_id,
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
        )

        return success_response({
            "items": logs,
            "count": len(logs),
            "total": len(logs),
            "account_id": account_id,
            "connection_id": connection_id,
            "filters": {
                "start_time": start_time,
                "end_time": end_time,
                "event_type": event_type,
            },
        })

    except Exception as e:
        print(f"Error handling audit logs query: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
        }
