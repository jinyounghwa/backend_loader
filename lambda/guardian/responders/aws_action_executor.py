"""AWS Action Executor — separated execution layer for remediation actions.

Handles AWS API calls that modify resources (stop EC2, block S3, etc.)
independently from detection logic in checkers.
"""
import logging

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class AWSActionExecutor:
    """Execute AWS remediation actions. Stateless — uses AWSClientProvider for clients."""

    def __init__(self):
        self.is_localstack = Config.is_localstack()

    def stop_ec2_instance(self, instance_id: str, region: str) -> bool:
        """Stop a running EC2 instance.

        Args:
            instance_id: EC2 instance identifier
            region: AWS region where the instance runs

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if self.is_localstack:
            logger.info("[LocalStack] Skipping EC2 stop for %s", instance_id)
            return True

        try:
            ec2 = AWSClientProvider.get_client('ec2', region=region)
            ec2.stop_instances(InstanceIds=[instance_id])
            logger.info("Stopped EC2 instance %s in %s", instance_id, region)
            return True
        except Exception as e:
            logger.error("Failed to stop EC2 instance %s: %s", instance_id, e)
            return False

    def block_s3_public_access(self, bucket_name: str) -> bool:
        """Block all public access on an S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if self.is_localstack:
            logger.info("[LocalStack] Skipping S3 public access block for %s", bucket_name)
            return True

        try:
            s3 = AWSClientProvider.get_client('s3')
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True,
                }
            )
            logger.info("Blocked public access for S3 bucket %s", bucket_name)
            return True
        except Exception as e:
            logger.error("Failed to block public access for %s: %s", bucket_name, e)
            return False
