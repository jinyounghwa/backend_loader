"""Real AWS S3 API client for bucket management."""

import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class S3Manager:
    """AWS S3 manager for bucket operations."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize S3 manager.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._s3_client = self.clients.get("s3")

    @property
    def s3_client(self):
        """Lazy S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client("s3", **Config.get_boto3_kwargs())
        return self._s3_client

    def list_buckets(self) -> List[Dict[str, Any]]:
        """List all S3 buckets.
        
        Returns:
            List of bucket details
        """
        try:
            response = self.s3_client.list_buckets()
            buckets = []
            for bucket in response['Buckets']:
                buckets.append({
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat(),
                })
            return buckets
        except ClientError as e:
            logger.error(f"Failed to list buckets: {e}")
            return []

    def get_bucket_acl(self, bucket_name: str) -> Dict[str, Any]:
        """Get ACL for a bucket.
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            ACL details
        """
        try:
            response = self.s3_client.get_bucket_acl(Bucket=bucket_name)
            return {
                'owner': response.get('Owner', {}),
                'grants': response.get('Grants', []),
            }
        except ClientError as e:
            logger.error(f"Failed to get ACL for {bucket_name}: {e}")
            return {}

    def get_bucket_policy(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """Get bucket policy.
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            Policy dict or None
        """
        try:
            response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
            import json
            return json.loads(response['Policy'])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                return None
            logger.error(f"Failed to get policy for {bucket_name}: {e}")
            return None

    def is_bucket_public(self, bucket_name: str) -> bool:
        """Check if bucket is publicly accessible.
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            True if bucket has public access
        """
        try:
            # Check ACL
            acl = self.get_bucket_acl(bucket_name)
            for grant in acl.get('grants', []):
                grantee = grant.get('Grantee', {})
                if grantee.get('Type') == 'Group' and 'AllUsers' in grantee.get('URI', ''):
                    return True
            
            # Check bucket policy
            policy = self.get_bucket_policy(bucket_name)
            if policy:
                for statement in policy.get('Statement', []):
                    if statement.get('Effect') == 'Allow':
                        principal = statement.get('Principal', '')
                        if principal == '*' or principal == {'AWS': '*'}:
                            return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking if bucket is public: {e}")
            return False

    def block_public_access(self, bucket_name: str) -> bool:
        """Enable Block Public Access for a bucket.
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True,
                }
            )
            logger.info(f"Blocked public access for {bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to block public access for {bucket_name}: {e}")
            return False

    def get_bucket_size(self, bucket_name: str) -> int:
        """Get total size of bucket in bytes (using CloudWatch metric).
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            Total size in bytes
        """
        try:
            cloudwatch = boto3.client("cloudwatch", **Config.get_boto3_kwargs())
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'},
                ],
                StartTime=boto3.utils.get_partition(
                    'aws'
                ),  # Simplified for demo
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=86400,
                Statistics=['Average'],
            )
            
            if response['Datapoints']:
                return int(response['Datapoints'][0]['Average'])
            return 0
        except Exception as e:
            logger.error(f"Failed to get bucket size: {e}")
            return 0

    def delete_bucket(self, bucket_name: str) -> bool:
        """Delete an empty S3 bucket.
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_bucket(Bucket=bucket_name)
            logger.info(f"Deleted bucket {bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete bucket {bucket_name}: {e}")
            return False
