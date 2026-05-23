"""
Sprint 32 Phase 5: Export Handler
Exports audit logs in CSV/JSON format
"""

import json
import logging
import os
import csv
import io
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def handle_export_logs(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Export audit logs in requested format (CSV or JSON).

    Args:
        event: API Gateway event with query parameters
        context: Lambda context

    Returns:
        Export response with file content
    """
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        account_id = query_params.get('account_id')
        connection_id = query_params.get('connection_id')
        format_type = query_params.get('format', 'json').lower()
        start_time = query_params.get('start_time')
        end_time = query_params.get('end_time')

        if format_type not in ['json', 'csv']:
            return error_response('Invalid format. Use "json" or "csv"', 400)

        if not account_id and not connection_id:
            return error_response('Missing required parameter: account_id or connection_id', 400)

        # Get logs
        logs = get_filtered_logs(account_id, connection_id, start_time, end_time)

        # Generate file content
        if format_type == 'json':
            content = generate_json(logs)
            filename = f'audit-logs-{datetime.now().isoformat()}.json'
            content_type = 'application/json'
        else:
            content = generate_csv(logs)
            filename = f'audit-logs-{datetime.now().isoformat()}.csv'
            content_type = 'text/csv'

        return {
            'statusCode': 200,
            'body': content,
            'headers': {
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        }

    except Exception as e:
        logger.error(f'Error exporting logs: {str(e)}')
        return error_response('Failed to export logs', 500)


def get_filtered_logs(
    account_id: str = None,
    connection_id: str = None,
    start_time: str = None,
    end_time: str = None
) -> List[Dict[str, Any]]:
    """
    Get filtered logs from DynamoDB.

    Args:
        account_id: AWS account ID
        connection_id: WebSocket connection ID
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        List of audit log items
    """
    # This would call audit_logger.query_with_filters()
    # For now, returning empty list
    return []


def generate_json(logs: List[Dict[str, Any]]) -> str:
    """
    Generate JSON export.

    Args:
        logs: List of log items

    Returns:
        JSON string
    """
    return json.dumps(logs, indent=2, default=str)


def generate_csv(logs: List[Dict[str, Any]]) -> str:
    """
    Generate CSV export.

    Args:
        logs: List of log items

    Returns:
        CSV string
    """
    if not logs:
        return ''

    output = io.StringIO()
    fieldnames = get_csv_fieldnames(logs)
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    writer.writeheader()
    for log in logs:
        writer.writerow({field: log.get(field, '') for field in fieldnames})

    return output.getvalue()


def get_csv_fieldnames(logs: List[Dict[str, Any]]) -> List[str]:
    """
    Get CSV field names from logs.

    Args:
        logs: List of log items

    Returns:
        List of field names in order
    """
    # Standard fields in order
    standard_fields = [
        'timestamp',
        'connection_id',
        'account_id',
        'event_type',
        'user_id',
        'status',
        'message_type',
        'threat_score',
        'details'
    ]

    # Add any additional fields from logs
    additional_fields = set()
    for log in logs:
        additional_fields.update(log.keys())

    # Keep standard fields in order, add additional fields
    result = [f for f in standard_fields if f in additional_fields]
    result.extend(sorted(additional_fields - set(standard_fields)))

    return result


def error_response(message: str, status_code: int) -> Dict[str, Any]:
    """Build error response."""
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': message}),
        'headers': {
            'Content-Type': 'application/json'
        }
    }
