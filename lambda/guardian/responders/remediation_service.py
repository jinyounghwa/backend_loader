"""Remediation Service for rule-based auto-remediation"""
from typing import Dict, Any, Optional
from logging import Logger

from guardian.storage.dynamodb import DynamoDBStorage
from guardian.storage.response_rules import ResponseRuleStorage
from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.responders.telegram import TelegramResponder
from guardian.logging_config import log_remediation


class AutoRemediationResponder:
    """Handle auto-remediation using rule-based execution engine."""

    def __init__(self, logger: Logger, storage: DynamoDBStorage, telegram: Optional[TelegramResponder] = None):
        self.logger = logger
        self.storage = storage
        self.telegram = telegram
        self.executor = AWSActionExecutor()
        self.rule_storage = ResponseRuleStorage()

    def _execute_action(self, action_type: str, resource_id: str, region: str,
                       rule_id: str, dry_run: bool = False) -> bool:
        """Execute an action and log the result."""
        if dry_run:
            self.logger.info("[DRY-RUN] Would execute %s on %s in %s (rule: %s)",
                           action_type, resource_id, region, rule_id)
            return True

        try:
            success = False
            action_desc = None

            if action_type == 'stop_instance':
                success = self.executor.stop_ec2_instance(resource_id, region)
                action_desc = 'Stopped EC2 instance'
            elif action_type == 'block_bucket':
                success = self.executor.block_s3_public_access(resource_id)
                action_desc = 'Blocked S3 public access'
            elif action_type == 'revoke_key':
                self.logger.warning("Key revocation not yet implemented")
                return False

            if self.telegram:
                self.telegram.send_auto_response_notification(
                    action_type=action_type,
                    resource_id=resource_id,
                    status='success' if success else 'failed',
                    region=region,
                    rule_id=rule_id,
                    action_description=action_desc,
                )

            self.storage.save_auto_response(
                action_type, resource_id,
                'success' if success else 'failed',
                {'region': region, 'rule_id': rule_id},
            )
            log_remediation(self.logger, action_type, resource_id, 'success' if success else 'failed')
            return success
        except Exception as e:
            self.logger.error("Error executing %s on %s: %s", action_type, resource_id, e)
            if self.telegram:
                self.telegram.send_auto_response_notification(
                    action_type=action_type,
                    resource_id=resource_id,
                    status='failed',
                    region=region,
                    rule_id=rule_id,
                )
            return False

    def _match_event_to_rule(self, event_type: str, region: str, resource_region: str) -> Optional[Dict]:
        """Find the best matching rule for an event using priority."""
        rule = self.rule_storage.get_effective_rule(region, event_type)
        if not rule:
            rule = self.rule_storage.get_effective_rule(resource_region, event_type)
        if not rule:
            rule = self.rule_storage.get_effective_rule('*', event_type)
        return rule

    def handle_ec2_anomalies(self, ec2_data: Dict[str, Any], region: str) -> None:
        """Handle EC2 anomalies (exposed instances)."""
        anomalies = ec2_data.get('exposed_instances', [])
        if not anomalies:
            return

        for anomaly in anomalies:
            instance_id = anomaly['instance_id']
            instance_region = anomaly.get('region', region)

            rule = self._match_event_to_rule('unauthorized_exposure', region, instance_region)
            if not rule or not rule.get('enabled'):
                self.logger.debug("No matching rule for instance %s", instance_id)
                continue

            self._execute_action(
                action_type=rule['action'],
                resource_id=instance_id,
                region=instance_region,
                rule_id=rule['rule_id'],
                dry_run=rule.get('dry_run', False),
            )

    def handle_s3_anomalies(self, s3_data: Dict[str, Any], region: str) -> None:
        """Handle S3 anomalies (public buckets)."""
        anomalies = s3_data.get('public_buckets', [])
        if not anomalies:
            return

        for anomaly in anomalies:
            bucket_name = anomaly['bucket_name']

            rule = self._match_event_to_rule('public_bucket', region, region)
            if not rule or not rule.get('enabled'):
                self.logger.debug("No matching rule for bucket %s", bucket_name)
                continue

            self._execute_action(
                action_type=rule['action'],
                resource_id=bucket_name,
                region=region,
                rule_id=rule['rule_id'],
                dry_run=rule.get('dry_run', False),
            )

    def handle_check_result(self, check_name: str, check_result, region: str = '*') -> None:
        """Dispatch remediation based on check result using rule engine."""
        if check_result.severity == 'INFO':
            return

        details = check_result.details
        if check_name == 'ec2' and details.get('exposed_instances'):
            self.handle_ec2_anomalies(details, region)
        elif check_name == 's3' and details.get('public_buckets'):
            self.handle_s3_anomalies(details, region)
