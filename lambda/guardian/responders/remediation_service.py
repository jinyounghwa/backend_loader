"""Remediation Service for handling auto-remediation actions"""
from typing import Dict, Any
from logging import Logger

from guardian.storage.dynamodb import DynamoDBStorage
from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.logging_config import log_remediation


class AutoRemediationResponder:
    """Handle auto-remediation using AWSActionExecutor (no checker dependency)."""

    def __init__(self, logger: Logger, storage: DynamoDBStorage):
        self.logger = logger
        self.storage = storage
        self.executor = AWSActionExecutor()

    def handle_exposed_instances(self, ec2_data: Dict[str, Any]) -> None:
        exposed_instances = ec2_data.get('exposed_instances', [])
        if not exposed_instances:
            return

        for exposed in exposed_instances:
            instance_id = exposed['instance_id']
            region = exposed['region']
            try:
                self.logger.info("Auto-stopping exposed instance: %s", instance_id)
                success = self.executor.stop_ec2_instance(instance_id, region)

                self.storage.save_auto_response(
                    'stop_ec2', instance_id,
                    'success' if success else 'failed',
                    {'region': region, 'reason': 'exposed_to_0_0_0_0'},
                )
                log_remediation(self.logger, 'stop_ec2', instance_id, 'success' if success else 'failed')
            except Exception as e:
                self.logger.error("Error stopping instance %s: %s", instance_id, e)
                self.storage.save_auto_response(
                    'stop_ec2', instance_id, 'failed',
                    {'region': region, 'reason': 'exposed_to_0_0_0_0', 'error': str(e)},
                )

    def handle_public_buckets(self, s3_data: Dict[str, Any]) -> None:
        public_buckets = s3_data.get('public_buckets', [])
        if not public_buckets:
            return

        for public_bucket in public_buckets:
            bucket_name = public_bucket['bucket_name']
            try:
                self.logger.info("Auto-blocking public access for: %s", bucket_name)
                success = self.executor.block_s3_public_access(bucket_name)

                self.storage.save_auto_response(
                    'block_s3_public', bucket_name,
                    'success' if success else 'failed',
                    {'reasons': public_bucket['public_reasons']},
                )
                log_remediation(self.logger, 'block_s3_public', bucket_name, 'success' if success else 'failed')
            except Exception as e:
                self.logger.error("Error blocking public access for %s: %s", bucket_name, e)
                self.storage.save_auto_response(
                    'block_s3_public', bucket_name, 'failed',
                    {'reasons': public_bucket['public_reasons'], 'error': str(e)},
                )

    def handle_check_result(self, check_name: str, check_result) -> None:
        """Dispatch remediation based on a CheckResult from any checker."""
        if check_result.severity == 'INFO':
            return

        details = check_result.details
        if check_name == 'ec2' and details.get('exposed_instances'):
            self.handle_exposed_instances(details)
        elif check_name == 's3' and details.get('public_buckets'):
            self.handle_public_buckets(details)
