"""DynamoDB storage for AWS Guardian"""
import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class DynamoDBStorage:
    def __init__(self, table_name: str = None):
        self.table_name = table_name or Config.get_dynamodb_table_name()
        self.is_localstack = Config.is_localstack()

        try:
            self.table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
        except Exception as e:
            logger.warning("Could not access table %s: %s", self.table_name, e)
            self.table = None

    def save_event(self, event_type: str, severity: str, details: Dict[str, Any],
                   account_id: str = 'current') -> bool:
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            item = {
                'event_id': str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'severity': severity,
                'account_id': account_id,
                'gsi_pk': 'EVENT',
                'details': json.dumps(details) if isinstance(details, dict) else details
            }

            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving event: %s", e)
            return False

    def save_auto_response(self, action_type: str, resource_id: str, status: str, details: Dict[str, Any]) -> bool:
        try:
            item = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action_type': action_type,
                'resource_id': resource_id,
                'status': status,
                'details': details
            }

            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving auto-response: %s", e)
            return False

    def get_recent_events(self, hours: int = 24, event_type: str = None) -> List[Dict]:
        try:
            from boto3.dynamodb.conditions import Key

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            if event_type:
                response = self.table.query(
                    IndexName='TypeTimestampIndex',
                    KeyConditionExpression=Key('event_type').eq(event_type) &
                                           Key('timestamp').gt(cutoff_time.isoformat()),
                    ScanIndexForward=False,
                    Limit=100
                )
            else:
                response = self.table.query(
                    IndexName='AllEventsIndex',
                    KeyConditionExpression=Key('gsi_pk').eq('EVENT') &
                                           Key('timestamp').gt(cutoff_time.isoformat()),
                    ScanIndexForward=False,
                    Limit=100
                )

            return response.get('Items', [])
        except Exception as e:
            logger.error("Error getting recent events: %s", e)
            return []

    def get_events_by_severity(self, severity: str, hours: int = 24) -> List[Dict]:
        try:
            from boto3.dynamodb.conditions import Key

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            response = self.table.query(
                IndexName='SeverityTimestampIndex',
                KeyConditionExpression=Key('severity').eq(severity) &
                                       Key('timestamp').gt(cutoff_time.isoformat()),
                ScanIndexForward=False,
                Limit=100
            )

            return response.get('Items', [])
        except Exception as e:
            logger.error("Error getting events by severity: %s", e)
            return []

    def get_events_by_account(self, account_id: str, hours: int = 24) -> List[Dict]:
        """Query events for a specific account (Phase 4: Multi-account support)."""
        try:
            from boto3.dynamodb.conditions import Key, Attr

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            response = self.table.scan(
                FilterExpression=Attr('account_id').eq(account_id) &
                                Attr('timestamp').gt(cutoff_time.isoformat()),
                Limit=100
            )

            return response.get('Items', [])
        except Exception as e:
            logger.error("Error getting events by account %s: %s", account_id, e)
            return []

    def get_event_summary(self, hours: int = 24, account_id: str = None) -> Dict[str, Any]:
        try:
            if account_id:
                events = self.get_events_by_account(account_id, hours)
            else:
                events = self.get_recent_events(hours)

            summary: Dict[str, Any] = {
                'total_events': len(events),
                'by_type': {},
                'by_severity': {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if account_id:
                summary['account_id'] = account_id

            for event in events:
                event_type = event.get('event_type', 'unknown')
                severity = event.get('severity', 'unknown')

                summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1
                summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1

            return summary
        except Exception as e:
            logger.error("Error getting event summary: %s", e)
            return {}

    def get_latest_check_result(self, time_filter: str = None) -> List[Dict]:
        try:
            from boto3.dynamodb.conditions import Key

            if time_filter:
                cutoff = time_filter
            else:
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            response = self.table.query(
                IndexName='TypeTimestampIndex',
                KeyConditionExpression=Key('event_type').eq('check_result') &
                                       Key('timestamp').gt(cutoff),
                ScanIndexForward=False,
                Limit=10
            )

            return response.get('Items', [])
        except Exception as e:
            logger.error("Error getting latest check result: %s", e)
            return []

    def create_table(self) -> bool:
        try:
            dynamodb = AWSClientProvider.get_resource('dynamodb')
            dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'timestamp', 'KeyType': 'HASH'},
                    {'AttributeName': 'event_type', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                    {'AttributeName': 'event_type', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )

            self.table.meta.client.get_waiter('table_exists').wait(
                TableName=self.table_name
            )
            return True
        except Exception as e:
            if 'ResourceInUseException' in str(e):
                logger.info("Table %s already exists", self.table_name)
                return True
            logger.error("Error creating table: %s", e)
            return False
