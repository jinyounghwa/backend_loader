"""DynamoDB storage for AWS Guardian"""
import boto3
from typing import Dict, Any, List
from datetime import datetime
import json

class DynamoDBStorage:
    def __init__(self, table_name: str = 'aws-guardian-events'):
        """Initialize DynamoDB storage"""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = table_name
        self.table = self.dynamodb.Table(table_name)

    def save_event(self, event_type: str, severity: str, details: Dict[str, Any]) -> bool:
        """
        Save an event to DynamoDB

        Args:
            event_type: 'cost', 'ec2', 's3'
            severity: 'info', 'warning', 'critical'
            details: Event details dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            item = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'severity': severity,
                'details': details
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
                'timestamp': datetime.utcnow().isoformat(),
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
        """Get recent events from DynamoDB"""
        try:
            from boto3.dynamodb.conditions import Key, Attr
            from datetime import timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Query with filter
            if event_type:
                response = self.table.scan(
                    FilterExpression=Attr('timestamp').gt(cutoff_time.isoformat()) &
                                     Attr('event_type').eq(event_type)
                )
            else:
                response = self.table.scan(
                    FilterExpression=Attr('timestamp').gt(cutoff_time.isoformat())
                )

            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting recent events: {e}")
            return []

    def get_event_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of events from last N hours"""
        try:
            events = self.get_recent_events(hours)

            summary = {
                'total_events': len(events),
                'by_type': {},
                'by_severity': {},
                'timestamp': datetime.utcnow().isoformat()
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
