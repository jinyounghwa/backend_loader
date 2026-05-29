"""Real AWS EC2 API client for instance management."""

import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class EC2Manager:
    """AWS EC2 manager for instance operations."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize EC2 manager.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._ec2_client = self.clients.get("ec2")

    @property
    def ec2_client(self):
        """Lazy EC2 client."""
        if self._ec2_client is None:
            self._ec2_client = boto3.client("ec2", **Config.get_boto3_kwargs())
        return self._ec2_client

    def list_instances(self, filters: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """List EC2 instances with optional filters.
        
        Args:
            filters: Optional list of filter dicts
            
        Returns:
            List of instance details
        """
        try:
            kwargs = {}
            if filters:
                kwargs['Filters'] = filters
            
            response = self.ec2_client.describe_instances(**kwargs)
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'state': instance['State']['Name'],
                        'instance_type': instance['InstanceType'],
                        'launch_time': instance['LaunchTime'].isoformat(),
                        'private_ip': instance.get('PrivateIpAddress'),
                        'public_ip': instance.get('PublicIpAddress'),
                        'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])},
                    })
            return instances
        except ClientError as e:
            logger.error(f"Failed to list instances: {e}")
            return []

    def get_instance_details(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get details for specific instance.
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Instance details or None
        """
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            if response['Reservations']:
                instance = response['Reservations'][0]['Instances'][0]
                return {
                    'instance_id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'instance_type': instance['InstanceType'],
                    'launch_time': instance['LaunchTime'].isoformat(),
                    'security_groups': [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
                }
            return None
        except ClientError as e:
            logger.error(f"Failed to get instance details: {e}")
            return None

    def stop_instance(self, instance_id: str) -> bool:
        """Stop an EC2 instance.
        
        Args:
            instance_id: Instance ID to stop
            
        Returns:
            True if successful
        """
        try:
            self.ec2_client.stop_instances(InstanceIds=[instance_id])
            logger.info(f"Stopped instance {instance_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            return False

    def start_instance(self, instance_id: str) -> bool:
        """Start a stopped EC2 instance.
        
        Args:
            instance_id: Instance ID to start
            
        Returns:
            True if successful
        """
        try:
            self.ec2_client.start_instances(InstanceIds=[instance_id])
            logger.info(f"Started instance {instance_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            return False

    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate an EC2 instance.
        
        Args:
            instance_id: Instance ID to terminate
            
        Returns:
            True if successful
        """
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            logger.info(f"Terminated instance {instance_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to terminate instance {instance_id}: {e}")
            return False

    def get_security_groups(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get security groups for an instance.
        
        Args:
            instance_id: Instance ID
            
        Returns:
            List of security group details
        """
        try:
            instance_details = self.get_instance_details(instance_id)
            if not instance_details:
                return []
            
            sg_ids = instance_details.get('security_groups', [])
            if not sg_ids:
                return []
            
            response = self.ec2_client.describe_security_groups(GroupIds=sg_ids)
            
            sgs = []
            for sg in response['SecurityGroups']:
                sgs.append({
                    'group_id': sg['GroupId'],
                    'group_name': sg['GroupName'],
                    'inbound_rules': sg['IpPermissions'],
                    'outbound_rules': sg['IpPermissionsEgress'],
                })
            return sgs
        except ClientError as e:
            logger.error(f"Failed to get security groups: {e}")
            return []
