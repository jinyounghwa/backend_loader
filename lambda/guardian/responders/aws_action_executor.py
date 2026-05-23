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

    def disable_lambda_function(self, function_name: str, region: str = "us-east-1") -> bool:
        """Disable a Lambda function by setting concurrency to 0.

        Args:
            function_name: Lambda function name or ARN
            region: AWS region where the function is deployed

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not function_name:
            logger.error("Invalid function name")
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping Lambda disable for %s", function_name)
            return True

        try:
            lambda_client = AWSClientProvider.get_client("lambda", region=region)
            lambda_client.put_function_concurrency(
                FunctionName=function_name,
                ReservedConcurrentExecutions=0
            )
            logger.info("Disabled Lambda function %s in %s", function_name, region)
            return True
        except Exception as e:
            logger.error("Failed to disable Lambda function %s: %s", function_name, e)
            return False

    def remove_lambda_layer(self, function_name: str, layer_arn: str, region: str = "us-east-1") -> bool:
        """Remove a Lambda layer from a function.

        Args:
            function_name: Lambda function name or ARN
            layer_arn: ARN of the layer to remove
            region: AWS region

        Returns:
            True if the action succeeded
        """
        if not function_name or not layer_arn:
            logger.error("Invalid function name or layer ARN")
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping Lambda layer removal for %s", function_name)
            return True

        try:
            lambda_client = AWSClientProvider.get_client("lambda", region=region)

            # Get current function config
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            current_layers = response.get("Layers", [])

            # Filter out the layer to remove
            new_layers = [l["Arn"] for l in current_layers if l["Arn"] != layer_arn]

            # Update function with new layers
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Layers=new_layers
            )
            logger.info("Removed layer %s from function %s", layer_arn, function_name)
            return True
        except Exception as e:
            logger.error("Failed to remove Lambda layer %s: %s", layer_arn, e)
            return False

    def restrict_lambda_concurrency(
        self,
        function_name: str,
        max_concurrency: int = 1,
        region: str = "us-east-1"
    ) -> bool:
        """Restrict Lambda function concurrency.

        Args:
            function_name: Lambda function name or ARN
            max_concurrency: Maximum concurrent executions (0-999, default 1)
            region: AWS region

        Returns:
            True if the action succeeded
        """
        if max_concurrency < 0 or max_concurrency > 999:
            logger.error("Invalid concurrency value: %d", max_concurrency)
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping Lambda concurrency restriction for %s", function_name)
            return True

        try:
            lambda_client = AWSClientProvider.get_client("lambda", region=region)
            lambda_client.put_function_concurrency(
                FunctionName=function_name,
                ReservedConcurrentExecutions=max_concurrency
            )
            logger.info(
                "Restricted Lambda function %s concurrency to %d in %s",
                function_name,
                max_concurrency,
                region
            )
            return True
        except Exception as e:
            logger.error("Failed to restrict Lambda concurrency for %s: %s", function_name, e)
            return False

    def create_rds_snapshot(self, db_instance_id: str, region: str = "us-east-1") -> bool:
        """Create a snapshot of an RDS database instance.

        Args:
            db_instance_id: RDS database instance identifier
            region: AWS region

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not db_instance_id:
            logger.error("Invalid database instance ID")
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping RDS snapshot for %s", db_instance_id)
            return True

        try:
            rds = AWSClientProvider.get_client("rds", region=region)
            snapshot_id = f"snapshot-{db_instance_id}-{int(__import__('time').time())}"
            rds.create_db_snapshot(
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceIdentifier=db_instance_id
            )
            logger.info("Created snapshot %s for RDS instance %s in %s", snapshot_id, db_instance_id, region)
            return True
        except Exception as e:
            logger.error("Failed to create RDS snapshot for %s: %s", db_instance_id, e)
            return False

    def disable_rds_public_access(self, db_instance_id: str, region: str = "us-east-1") -> bool:
        """Disable public access on an RDS database instance.

        Args:
            db_instance_id: RDS database instance identifier
            region: AWS region

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not db_instance_id:
            logger.error("Invalid database instance ID")
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping RDS public access disable for %s", db_instance_id)
            return True

        try:
            rds = AWSClientProvider.get_client("rds", region=region)
            rds.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                PubliclyAccessible=False,
                ApplyImmediately=True
            )
            logger.info("Disabled public access for RDS instance %s in %s", db_instance_id, region)
            return True
        except Exception as e:
            logger.error("Failed to disable public access for RDS instance %s: %s", db_instance_id, e)
            return False

    def enable_rds_encryption(self, db_instance_id: str, region: str = "us-east-1") -> bool:
        """Enable encryption at rest for an RDS database instance.

        Args:
            db_instance_id: RDS database instance identifier
            region: AWS region

        Returns:
            True if the action succeeded or was skipped (LocalStack)

        Note: Enabling encryption on existing instances requires a snapshot/restore cycle.
        """
        if not db_instance_id:
            logger.error("Invalid database instance ID")
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping RDS encryption enable for %s", db_instance_id)
            return True

        try:
            rds = AWSClientProvider.get_client("rds", region=region)
            # Note: For existing instances, this typically requires modify_db_instance
            # Some engines/configurations may not support direct modification
            rds.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                StorageEncrypted=True,
                ApplyImmediately=False  # Typically requires maintenance window
            )
            logger.info("Enabled encryption for RDS instance %s in %s", db_instance_id, region)
            return True
        except Exception as e:
            logger.error("Failed to enable encryption for RDS instance %s: %s", db_instance_id, e)
            return False

    def enable_rds_backups(self, db_instance_id: str, backup_retention_days: int = 7, region: str = "us-east-1") -> bool:
        """Enable automated backups for an RDS database instance.

        Args:
            db_instance_id: RDS database instance identifier
            backup_retention_days: Number of days to retain backups (1-35, default 7)
            region: AWS region

        Returns:
            True if the action succeeded or was skipped (LocalStack)
        """
        if not db_instance_id:
            logger.error("Invalid database instance ID")
            return False

        if backup_retention_days < 1 or backup_retention_days > 35:
            logger.error("Invalid backup retention days: %d", backup_retention_days)
            return False

        if self.is_localstack:
            logger.info("[LocalStack] Skipping RDS backup enable for %s", db_instance_id)
            return True

        try:
            rds = AWSClientProvider.get_client("rds", region=region)
            rds.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                BackupRetentionPeriod=backup_retention_days,
                ApplyImmediately=True
            )
            logger.info(
                "Enabled backups for RDS instance %s with %d day retention in %s",
                db_instance_id,
                backup_retention_days,
                region
            )
            return True
        except Exception as e:
            logger.error("Failed to enable backups for RDS instance %s: %s", db_instance_id, e)
            return False
