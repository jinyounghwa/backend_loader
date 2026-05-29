"""Real AWS RDS API client for database management."""

import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class RDSManager:
    """AWS RDS manager for database operations."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize RDS manager.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._rds_client = self.clients.get("rds")

    @property
    def rds_client(self):
        """Lazy RDS client."""
        if self._rds_client is None:
            self._rds_client = boto3.client("rds", **Config.get_boto3_kwargs())
        return self._rds_client

    def list_instances(self) -> List[Dict[str, Any]]:
        """List all RDS instances.
        
        Returns:
            List of instance details
        """
        try:
            response = self.rds_client.describe_db_instances()
            instances = []
            for instance in response['DBInstances']:
                instances.append({
                    'identifier': instance['DBInstanceIdentifier'],
                    'class': instance['DBInstanceClass'],
                    'engine': instance['Engine'],
                    'status': instance['DBInstanceStatus'],
                    'allocated_storage': instance['AllocatedStorage'],
                    'multi_az': instance['MultiAZ'],
                })
            return instances
        except ClientError as e:
            logger.error(f"Failed to list RDS instances: {e}")
            return []

    def get_instance_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get details for specific RDS instance.
        
        Args:
            identifier: DB instance identifier
            
        Returns:
            Instance details or None
        """
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=identifier
            )
            if response['DBInstances']:
                instance = response['DBInstances'][0]
                return {
                    'identifier': instance['DBInstanceIdentifier'],
                    'class': instance['DBInstanceClass'],
                    'engine': instance['Engine'],
                    'status': instance['DBInstanceStatus'],
                    'storage': instance['AllocatedStorage'],
                    'multi_az': instance['MultiAZ'],
                    'endpoint': instance.get('Endpoint', {}).get('Address'),
                }
            return None
        except ClientError as e:
            logger.error(f"Failed to get RDS instance details: {e}")
            return None

    def modify_instance_class(self, identifier: str, new_class: str) -> bool:
        """Modify RDS instance class (scale up/down).
        
        Args:
            identifier: DB instance identifier
            new_class: New instance class (e.g., 'db.t3.micro')
            
        Returns:
            True if modification initiated
        """
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=identifier,
                DBInstanceClass=new_class,
                ApplyImmediately=True,
            )
            logger.info(f"Modified RDS instance {identifier} to {new_class}")
            return True
        except ClientError as e:
            logger.error(f"Failed to modify RDS instance: {e}")
            return False

    def enable_multi_az(self, identifier: str) -> bool:
        """Enable Multi-AZ for an RDS instance.
        
        Args:
            identifier: DB instance identifier
            
        Returns:
            True if successful
        """
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=identifier,
                MultiAZ=True,
                ApplyImmediately=False,
            )
            logger.info(f"Enabled Multi-AZ for {identifier}")
            return True
        except ClientError as e:
            logger.error(f"Failed to enable Multi-AZ: {e}")
            return False

    def disable_multi_az(self, identifier: str) -> bool:
        """Disable Multi-AZ for an RDS instance.
        
        Args:
            identifier: DB instance identifier
            
        Returns:
            True if successful
        """
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=identifier,
                MultiAZ=False,
                ApplyImmediately=False,
            )
            logger.info(f"Disabled Multi-AZ for {identifier}")
            return True
        except ClientError as e:
            logger.error(f"Failed to disable Multi-AZ: {e}")
            return False

    def get_instance_metrics(self, identifier: str) -> Dict[str, Any]:
        """Get CloudWatch metrics for RDS instance.
        
        Args:
            identifier: DB instance identifier
            
        Returns:
            Dictionary of metrics
        """
        try:
            cloudwatch = boto3.client("cloudwatch", **Config.get_boto3_kwargs())
            
            cpu_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'DBInstanceIdentifier', 'Value': identifier},
                ],
                StartTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ) - __import__('datetime').timedelta(hours=1),
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=300,
                Statistics=['Average'],
            )
            
            cpu = 0
            if cpu_response['Datapoints']:
                cpu = cpu_response['Datapoints'][-1]['Average']
            
            return {
                'cpu_utilization': cpu,
                'status': 'monitoring',
            }
        except Exception as e:
            logger.error(f"Failed to get RDS metrics: {e}")
            return {}
