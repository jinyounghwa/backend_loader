"""
Sprint 32 Phase 1: Audit Logs Query API Handler
HTTP API Gateway handler for querying WebSocket audit logs
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

lambda_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lambda_dir))

from handlers.audit_logger import AuditLogger


def handle_get_audit_logs(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /audit-logs HTTP API request

    Query Parameters:
      - connection_id (required): Connection ID to query
      - start_time (optional): ISO 8601 start time (e.g., 2026-05-22T15:00:00Z)
      - end_time (optional): ISO 8601 end time (e.g., 2026-05-22T16:00:00Z)
      - event_type (optional): Event type filter ($connect, $disconnect, message, broadcast)

    Returns:
      {
        "statusCode": 200,
        "body": {
          "items": [...],
          "count": N,
          "connection_id": "abc123"
        }
      }
    """
    try:
        # Parse query string parameters
        query_params = event.get("queryStringParameters") or {}
        connection_id = query_params.get("connection_id")
        start_time = query_params.get("start_time")
        end_time = query_params.get("end_time")
        event_type = query_params.get("event_type")

        # Validate required parameter
        if not connection_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameter: connection_id"}),
            }

        # Query audit logs with filters
        logs = AuditLogger.query_with_filters(
            connection_id=connection_id,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "items": logs,
                    "count": len(logs),
                    "connection_id": connection_id,
                    "filters": {
                        "start_time": start_time,
                        "end_time": end_time,
                        "event_type": event_type,
                    },
                }
            ),
        }

    except Exception as e:
        print(f"Error handling audit logs query: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
        }
