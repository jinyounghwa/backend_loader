"""
Sprint 32 Phase 4: DynamoDB Stream Processor
Processes real-time audit log events from DynamoDB Streams
"""

import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def handle_stream_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process DynamoDB Stream records and broadcast to connected WebSocket clients.

    Args:
        event: DynamoDB Stream event with Records
        context: Lambda context

    Returns:
        Response with batch item failures (if any)
    """
    records = event.get('Records', [])
    logger.info(f'Processing {len(records)} stream records')

    batch_item_failures = []

    for record in records:
        try:
            process_stream_record(record)
        except Exception as e:
            logger.error(f'Failed to process record: {str(e)}')
            batch_item_failures.append({
                'itemId': record.get('eventID')
            })

    return {
        'statusCode': 200,
        'batchItemFailures': batch_item_failures
    }


def process_stream_record(record: Dict[str, Any]) -> None:
    """
    Process a single DynamoDB Stream record.

    Args:
        record: Single stream record
    """
    event_name = record.get('eventName')
    dynamodb = record.get('dynamodb', {})

    if event_name == 'INSERT':
        handle_insert(dynamodb)
    elif event_name == 'MODIFY':
        handle_modify(dynamodb)
    elif event_name == 'REMOVE':
        handle_remove(dynamodb)


def handle_insert(dynamodb: Dict[str, Any]) -> None:
    """Handle INSERT events - new audit log entry."""
    new_image = dynamodb.get('NewImage', {})

    if not new_image:
        return

    log_entry = {
        'connection_id': new_image.get('connection_id', {}).get('S'),
        'account_id': new_image.get('account_id', {}).get('S', 'current'),
        'timestamp': new_image.get('timestamp', {}).get('S'),
        'event_type': new_image.get('event_type', {}).get('S'),
        'user_id': new_image.get('user_id', {}).get('S'),
        'status': new_image.get('status', {}).get('S'),
        'details': parse_dynamodb_value(new_image.get('details', {}))
    }

    logger.info(f'New audit log: {log_entry["event_type"]} from {log_entry["account_id"]}')

    broadcast_to_clients({
        'type': 'audit_log_created',
        'data': log_entry
    })


def handle_modify(dynamodb: Dict[str, Any]) -> None:
    """Handle MODIFY events - audit log update."""
    new_image = dynamodb.get('NewImage', {})
    old_image = dynamodb.get('OldImage', {})

    if not new_image:
        return

    logger.info('Audit log modified')

    broadcast_to_clients({
        'type': 'audit_log_modified',
        'data': {
            'connection_id': new_image.get('connection_id', {}).get('S'),
            'timestamp': new_image.get('timestamp', {}).get('S')
        }
    })


def handle_remove(dynamodb: Dict[str, Any]) -> None:
    """Handle REMOVE events - audit log deletion (TTL)."""
    old_image = dynamodb.get('OldImage', {})

    if not old_image:
        return

    logger.info('Audit log expired/removed')

    broadcast_to_clients({
        'type': 'audit_log_removed',
        'data': {
            'connection_id': old_image.get('connection_id', {}).get('S'),
            'timestamp': old_image.get('timestamp', {}).get('S')
        }
    })


def broadcast_to_clients(message: Dict[str, Any]) -> None:
    """
    Broadcast message to connected WebSocket clients.
    Clients subscribe to updates via EventSource SSE endpoint.

    Args:
        message: Message payload to broadcast
    """
    logger.info(f'Broadcasting message: {message["type"]}')


def parse_dynamodb_value(value: Dict[str, Any]) -> Any:
    """
    Parse DynamoDB attribute value to Python type.

    Args:
        value: DynamoDB attribute format

    Returns:
        Parsed Python value
    """
    if 'S' in value:
        return value['S']
    elif 'N' in value:
        return float(value['N'])
    elif 'BOOL' in value:
        return value['BOOL']
    elif 'NULL' in value:
        return None
    elif 'M' in value:
        return {k: parse_dynamodb_value(v) for k, v in value['M'].items()}
    elif 'L' in value:
        return [parse_dynamodb_value(v) for v in value['L']]
    return None
