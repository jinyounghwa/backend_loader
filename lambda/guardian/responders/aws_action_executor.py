"""AWS Action Executor — separated execution layer for remediation actions.

Handles AWS API calls that modify resources (stop EC2, block S3, etc.)
independently from detection logic in checkers.
"""

import logging
import re

from guardian.aws_client_provider import AWSClientProvider
from guardian.config import Config

logger = logging.getLogger(__name__)

# Validation patterns
INSTANCE_ID_PATTERN = re.compile(r"^i-[0-9a-f]{8,17}$")
BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$")
REGION_PATTERN = re.compile(
    r"^(us|eu|ap|sa|ca|me|af)-(east|west|south|north|central|southeast|northeast)-[0-9]$"
)


class AWSActionExecutor:
    """Execute AWS remediation actions. Stateless — uses AWSClientProvider for clients."""

    def __init__(self):
        self.is_localstack = Config.is_localstack()

    def stop_ec2_instance(self, instance_id: str, region: str) -> bool:
        """Stop a running EC2 instance.

        Args:
            instance_id: EC2 instance identifier (must match i-[0-9a-f]{8,17})
            region: AWS region where the instance runs

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not INSTANCE_ID_PATTERN.match(instance_id):
            logger.error("Invalid instance ID format: %s", instance_id)
            return False
        if not REGION_PATTERN.match(region):
            logger.error("Invalid region format: %s", region)
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping EC2 stop for %s", instance_id)
            return True

        try:
            ec2 = AWSClientProvider.get_client("ec2", region=region)
            ec2.stop_instances(InstanceIds=[instance_id])
            logger.info("Stopped EC2 instance %s in %s", instance_id, region)
            return True
        except Exception as e:
            logger.error("Failed to stop EC2 instance %s: %s", instance_id, e)
            return False

    def block_s3_public_access(self, bucket_name: str) -> bool:
        """Block all public access on an S3 bucket.

        Args:
            bucket_name: S3 bucket name (must match DNS-safe bucket naming rules)

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not BUCKET_NAME_PATTERN.match(bucket_name):
            logger.error("Invalid bucket name format: %s", bucket_name)
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping S3 public access block for %s", bucket_name)
            return True

        try:
            s3 = AWSClientProvider.get_client("s3")
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            logger.info("Blocked public access for S3 bucket %s", bucket_name)
            return True
        except Exception as e:
            logger.error("Failed to block public access for %s: %s", bucket_name, e)
            return False

