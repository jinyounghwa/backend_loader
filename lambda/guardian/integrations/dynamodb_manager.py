"""Real AWS DynamoDB API client for table management."""

import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class DynamoDBManager:
    """AWS DynamoDB manager for table operations."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize DynamoDB manager.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._dynamodb_client = self.clients.get("dynamodb")

    @property
    def dynamodb_client(self):
        """Lazy DynamoDB client."""
        if self._dynamodb_client is None:
            self._dynamodb_client = boto3.client("dynamodb", **Config.get_boto3_kwargs())
        return self._dynamodb_client

    def list_tables(self) -> List[str]:
        """List all DynamoDB tables.
        
        Returns:
            List of table names
        """
        try:
            response = self.dynamodb_client.list_tables()
            return response['TableNames']
        except ClientError as e:
            logger.error(f"Failed to list DynamoDB tables: {e}")
            return []

    def get_table_description(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get description for a DynamoDB table.
        
        Args:
            table_name: Table name
            
        Returns:
            Table details or None
        """
        try:
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table = response['Table']
            return {
                'name': table['TableName'],
                'status': table['TableStatus'],
                'item_count': table['ItemCount'],
                'size_bytes': table['TableSizeBytes'],
                'key_schema': table['KeySchema'],
                'billing_mode': table['BillingModeSummary'].get(
                    'BillingMode', 'UNKNOWN'
                ),
            }
        except ClientError as e:
            logger.error(f"Failed to describe table {table_name}: {e}")
            return None

    def enable_ttl(self, table_name: str, attribute_name: str) -> bool:
        """Enable TTL for a DynamoDB table.
        
        Args:
            table_name: Table name
            attribute_name: Attribute to use as TTL
            
        Returns:
            True if successful
        """
        try:
            self.dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'AttributeName': attribute_name,
                    'Enabled': True,
                },
            )
            logger.info(f"Enabled TTL for {table_name} on {attribute_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to enable TTL: {e}")
            return False

    def disable_ttl(self, table_name: str, attribute_name: str) -> bool:
        """Disable TTL for a DynamoDB table.
        
        Args:
            table_name: Table name
            attribute_name: Attribute to disable TTL on
            
        Returns:
            True if successful
        """
        try:
            self.dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'AttributeName': attribute_name,
                    'Enabled': False,
                },
            )
            logger.info(f"Disabled TTL for {table_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to disable TTL: {e}")
            return False

    def get_ttl_status(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get TTL status for a table.
        
        Args:
            table_name: Table name
            
        Returns:
            TTL status or None
        """
        try:
            response = self.dynamodb_client.describe_time_to_live(
                TableName=table_name
            )
            ttl = response['TimeToLiveDescription']
            return {
                'attribute_name': ttl.get('AttributeName'),
                'enabled': ttl.get('TimeToLiveStatus') == 'ENABLED',
                'status': ttl.get('TimeToLiveStatus'),
            }
        except ClientError as e:
            logger.error(f"Failed to get TTL status: {e}")
            return None

    def get_table_metrics(self, table_name: str) -> Dict[str, Any]:
        """Get CloudWatch metrics for DynamoDB table.
        
        Args:
            table_name: Table name
            
        Returns:
            Dictionary of metrics
        """
        try:
            cloudwatch = boto3.client("cloudwatch", **Config.get_boto3_kwargs())
            
            consumed_write = cloudwatch.get_metric_statistics(
                Namespace='AWS/DynamoDB',
                MetricName='ConsumedWriteCapacityUnits',
                Dimensions=[
                    {'Name': 'TableName', 'Value': table_name},
                ],
                StartTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ) - __import__('datetime').timedelta(hours=1),
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=300,
                Statistics=['Sum'],
            )
            
            consumed_read = cloudwatch.get_metric_statistics(
                Namespace='AWS/DynamoDB',
                MetricName='ConsumedReadCapacityUnits',
                Dimensions=[
                    {'Name': 'TableName', 'Value': table_name},
                ],
                StartTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ) - __import__('datetime').timedelta(hours=1),
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=300,
                Statistics=['Sum'],
            )
            
            total_write = sum(
                dp['Sum'] for dp in consumed_write['Datapoints']
            )
            total_read = sum(dp['Sum'] for dp in consumed_read['Datapoints'])
            
            return {
                'consumed_write_units': total_write,
                'consumed_read_units': total_read,
            }
        except Exception as e:
            logger.error(f"Failed to get DynamoDB metrics: {e}")
            return {}

    def update_billing_mode(
        self, table_name: str, mode: str
    ) -> bool:
        """Update billing mode for a table (PAY_PER_REQUEST or PROVISIONED).
        
        Args:
            table_name: Table name
            mode: Billing mode ('PAY_PER_REQUEST' or 'PROVISIONED')
            
        Returns:
            True if successful
        """
        try:
            if mode not in ['PAY_PER_REQUEST', 'PROVISIONED']:
                logger.error(f"Invalid billing mode: {mode}")
                return False
            
            update_kwargs = {
                'TableName': table_name,
                'BillingMode': mode,
            }
            
            self.dynamodb_client.update_billing_mode(**update_kwargs)
            logger.info(f"Updated {table_name} billing mode to {mode}")
            return True
        except ClientError as e:
            logger.error(f"Failed to update billing mode: {e}")
            return False
