"""DynamoDB storage for AWS Guardian"""
import boto3
import os
from typing import Dict, Any, List
from datetime import datetime
import json

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import Config

class DynamoDBStorage:
    def __init__(self, table_name: str = 'aws-guardian-events'):
        """Initialize DynamoDB storage"""
        boto3_kwargs = Config.get_boto3_kwargs()
        self.dynamodb = boto3.resource('dynamodb', **boto3_kwargs)
        self.table_name = table_name
        self.is_localstack = Config.is_localstack()

        try:
            self.table = self.dynamodb.Table(table_name)
        except Exception as e:
            print(f"Warning: Could not access table {table_name}: {e}")
            self.table = None

    def save_event(self, event_type: str, severity: str, details: Dict[str, Any]) -> bool:
        """
        Save an event to DynamoDB

        Args:
            event_type: 'cost', 'ec2', 's3', 'check_result'
            severity: 'info', 'warning', 'critical'
            details: Event details dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.table:
                print("Warning: DynamoDB table not available")
                return False

            import uuid
            from datetime import timezone

            item = {
                'event_id': str(uuid.uuid4()),  # Unique identifier
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'severity': severity,
                'gsi_pk': 'EVENT',  # For AllEventsIndex GSI
                'details': json.dumps(details) if isinstance(details, dict) else details
            }

            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving event: {e}")
            return False

    def save_auto_response(self, action_type: str, resource_id: str, status: str, details: Dict[str, Any]) -> bool:
        """
        Save an auto-response action to DynamoDB

        Args:
            action_type: 'stop_ec2', 'block_s3_public', etc.
            resource_id: Resource identifier
            status: 'success', 'failed'
            details: Action details

        Returns:
            True if successful, False otherwise
        """
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
            print(f"Error saving auto-response: {e}")
            return False

    def get_recent_events(self, hours: int = 24, event_type: str = None) -> List[Dict]:
        """Get recent events from DynamoDB using optimized GSI queries"""
        try:
            from boto3.dynamodb.conditions import Key, Attr
            from datetime import timedelta

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            if event_type:
                # ✅ Use TypeTimestampIndex GSI for efficient lookup
                response = self.table.query(
                    IndexName='TypeTimestampIndex',
                    KeyConditionExpression=Key('event_type').eq(event_type) &
                                           Key('timestamp').gt(cutoff_time.isoformat()),
                    ScanIndexForward=False,  # DESC - latest first
                    Limit=100
                )
            else:
                # ✅ Use AllEventsIndex GSI for dashboard queries
                response = self.table.query(
                    IndexName='AllEventsIndex',
                    KeyConditionExpression=Key('gsi_pk').eq('EVENT') &
                                           Key('timestamp').gt(cutoff_time.isoformat()),
                    ScanIndexForward=False,  # DESC
                    Limit=100
                )

            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting recent events: {e}")
            return []

    def get_events_by_severity(self, severity: str, hours: int = 24) -> List[Dict]:
        """Get events filtered by severity using SeverityTimestampIndex GSI"""
        try:
            from boto3.dynamodb.conditions import Key
            from datetime import timedelta

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            response = self.table.query(
                IndexName='SeverityTimestampIndex',
                KeyConditionExpression=Key('severity').eq(severity) &
                                       Key('timestamp').gt(cutoff_time.isoformat()),
                ScanIndexForward=False,  # DESC
                Limit=100
            )

            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting events by severity: {e}")
            return []

    def get_event_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of events from last N hours"""
        try:
            events = self.get_recent_events(hours)

            summary = {
                'total_events': len(events),
                'by_type': {},
                'by_severity': {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            for event in events:
                event_type = event.get('event_type', 'unknown')
                severity = event.get('severity', 'unknown')

                summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1
                summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1

            return summary
        except Exception as e:
            print(f"Error getting event summary: {e}")
            return {}

    def create_table(self) -> bool:
        """Create the DynamoDB table if it doesn't exist"""
        try:
            self.dynamodb.create_table(
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

            # Wait for table to be created
            self.table.meta.client.get_waiter('table_exists').wait(
                TableName=self.table_name
            )
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print(f"Table {self.table_name} already exists")
            return True
        except Exception as e:
            print(f"Error creating table: {e}")
            return False
