"""
Sprint 32 Phase 5: Statistics and Analytics Handler
Provides aggregated audit log statistics and analytics
"""

import logging
import os
from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
from guardian.http_response import success_response, error_response

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def handle_get_statistics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get audit log statistics for a given time range.

    Args:
        event: API Gateway event with query parameters
        context: Lambda context

    Returns:
        Statistics response with statusCode and body
    """
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        account_id = query_params.get('account_id')
        connection_id = query_params.get('connection_id')
        start_time = query_params.get('start_time')
        end_time = query_params.get('end_time')

        if not account_id and not connection_id:
            return error_response(400, 'Missing required parameter: account_id or connection_id')

        stats = calculate_statistics(
            account_id=account_id,
            connection_id=connection_id,
            start_time=start_time,
            end_time=end_time
        )

        return success_response(stats)

    except Exception as e:
        logger.error(f'Error getting statistics: {str(e)}')
        return error_response(500, 'Failed to get statistics')


def calculate_statistics(
    account_id: str = None,
    connection_id: str = None,
    start_time: str = None,
    end_time: str = None
) -> Dict[str, Any]:
    """
    Calculate audit log statistics.

    Args:
        account_id: AWS account ID (optional)
        connection_id: WebSocket connection ID (optional)
        start_time: Start timestamp (optional)
        end_time: End timestamp (optional)

    Returns:
        Statistics dictionary
    """
    # Get logs from database
    logs = get_filtered_logs(account_id, connection_id, start_time, end_time)

    if not logs:
        return {
            'total_events': 0,
            'event_types': {},
            'hourly_distribution': {},
            'top_connections': [],
            'top_accounts': [],
            'success_rate': 0.0,
            'time_range': {
                'start': start_time or 'N/A',
                'end': end_time or 'N/A'
            }
        }

    # Calculate statistics
    stats = {
        'total_events': len(logs),
        'event_types': count_by_field(logs, 'event_type'),
        'hourly_distribution': get_hourly_distribution(logs),
        'top_connections': get_top_connections(logs),
        'top_accounts': get_top_accounts(logs),
        'success_rate': calculate_success_rate(logs),
        'time_range': {
            'start': start_time or 'N/A',
            'end': end_time or 'N/A'
        },
        'status_distribution': count_by_field(logs, 'status'),
        'user_distribution': count_by_field(logs, 'user_id')
    }

    return stats


def get_filtered_logs(
    account_id: str = None,
    connection_id: str = None,
    start_time: str = None,
    end_time: str = None
) -> List[Dict[str, Any]]:
    """
    Get filtered logs from DynamoDB.
    In a real implementation, this would query DynamoDB.
    For now, returning empty list (would use audit_logger.query_with_filters).

    Args:
        account_id: AWS account ID
        connection_id: WebSocket connection ID
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        List of audit log items
    """
    # This would typically call audit_logger.query_with_filters()
    # For mock purposes, returning empty list
    return []


def count_by_field(logs: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    """
    Count occurrences of each value in a field.

    Args:
        logs: List of log items
        field: Field name to count by

    Returns:
        Dictionary with field values and counts
    """
    counts = defaultdict(int)
    for log in logs:
        value = log.get(field, 'unknown')
        counts[value] += 1
    return dict(counts)


def get_hourly_distribution(logs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get distribution of events by hour.

    Args:
        logs: List of log items

    Returns:
        Dictionary with hours and counts
    """
    hourly = defaultdict(int)
    for log in logs:
        timestamp = log.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                hourly[hour_key] += 1
            except ValueError:
                pass
    return dict(hourly)


def get_top_connections(logs: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top WebSocket connections by event count.

    Args:
        logs: List of log items
        limit: Maximum results

    Returns:
        List of {connection_id, count} dicts
    """
    counts = count_by_field(logs, 'connection_id')
    sorted_conns = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {'connection_id': conn_id, 'count': count}
        for conn_id, count in sorted_conns[:limit]
    ]


def get_top_accounts(logs: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top AWS accounts by event count.

    Args:
        logs: List of log items
        limit: Maximum results

    Returns:
        List of {account_id, count} dicts
    """
    counts = count_by_field(logs, 'account_id')
    sorted_accts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {'account_id': acct_id, 'count': count}
        for acct_id, count in sorted_accts[:limit]
    ]


def calculate_success_rate(logs: List[Dict[str, Any]]) -> float:
    """
    Calculate percentage of successful events.

    Args:
        logs: List of log items

    Returns:
        Success rate (0.0-100.0)
    """
    if not logs:
        return 0.0

    successful = sum(1 for log in logs if log.get('status') == 'success')
    return (successful / len(logs)) * 100.0
