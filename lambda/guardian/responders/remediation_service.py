"""Remediation Service for handling auto-remediation actions"""
from typing import Dict, Any, Optional
from logging import Logger

from storage.dynamodb import DynamoDBStorage
from checkers.ec2 import EC2Checker
from checkers.s3 import S3Checker
from config import Config
from logging_config import log_remediation


class AutoRemediationResponder:
    """
    Handles auto-remediation actions for security and compliance issues.
    Separates remediation logic from detection and notification logic.
    """

    def __init__(
        self,
        logger: Logger,
        storage: DynamoDBStorage,
        ec2_checker: EC2Checker,
        s3_checker: S3Checker,
    ):
        """
        Initialize the remediation responder.

        Args:
            logger: Logger instance
            storage: DynamoDB storage for recording actions
            ec2_checker: EC2 checker with remediation methods
            s3_checker: S3 checker with remediation methods
        """
        self.logger = logger
        self.storage = storage
        self.ec2_checker = ec2_checker
        self.s3_checker = s3_checker
        self.is_localstack = Config.is_localstack()

    def handle_exposed_instances(self, ec2_data: Dict[str, Any]) -> None:
        """
        Remediate exposed EC2 instances by stopping them.

        Args:
            ec2_data: EC2 check results containing exposed instances
        """
        exposed_instances = ec2_data.get('exposed_instances', [])

        if not exposed_instances:
            return

        for exposed in exposed_instances:
            instance_id = exposed['instance_id']
            region = exposed['region']

            try:
                self.logger.info(f"Auto-stopping exposed instance: {instance_id}")

                # Execute stop action (skip in LocalStack)
                if not self.is_localstack:
                    success = self.ec2_checker.stop_instance(instance_id, region)
                else:
                    success = True

                # Record the action
                self.storage.save_auto_response(
                    'stop_ec2',
                    instance_id,
                    'success' if success else 'failed',
                    {'region': region, 'reason': 'exposed_to_0_0_0_0'}
                )
                log_remediation(self.logger, 'stop_ec2', instance_id, 'success' if success else 'failed')

            except Exception as e:
                self.logger.error(f"Error stopping instance {instance_id}: {e}")
                self.storage.save_auto_response(
                    'stop_ec2',
                    instance_id,
                    'failed',
                    {'region': region, 'reason': 'exposed_to_0_0_0_0', 'error': str(e)}
                )

    def handle_public_buckets(self, s3_data: Dict[str, Any]) -> None:
        """
        Remediate public S3 buckets by blocking public access.

        Args:
            s3_data: S3 check results containing public buckets
        """
        public_buckets = s3_data.get('public_buckets', [])

        if not public_buckets:
            return

        for public_bucket in public_buckets:
            bucket_name = public_bucket['bucket_name']

            try:
                self.logger.info(f"Auto-blocking public access for: {bucket_name}")

                # Execute block action (skip in LocalStack)
                if not self.is_localstack:
                    success = self.s3_checker.block_public_access(bucket_name)
                else:
                    success = True

                # Record the action
                self.storage.save_auto_response(
                    'block_s3_public',
                    bucket_name,
                    'success' if success else 'failed',
                    {'reasons': public_bucket['public_reasons']}
                )
                log_remediation(self.logger, 'block_s3_public', bucket_name, 'success' if success else 'failed')

            except Exception as e:
                self.logger.error(f"Error blocking public access for {bucket_name}: {e}")
                self.storage.save_auto_response(
                    'block_s3_public',
                    bucket_name,
                    'failed',
                    {'reasons': public_bucket['public_reasons'], 'error': str(e)}
                )

    def handle_cost_anomaly(self, cost_data: Dict[str, Any]) -> None:
        """
        Remediate cost anomalies (future implementation).

        Args:
            cost_data: Cost check results
        """
        # This could trigger cost optimization actions in the future
        # For now, it's handled via Telegram commands
        pass
