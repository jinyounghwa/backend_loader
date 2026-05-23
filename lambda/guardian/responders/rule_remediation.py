"""Rule-Based Automatic Remediation System (Sprint 36 Phase 2)

Executes automatic remediation actions based on rule definitions.
Each rule can specify remediation_actions to be executed when threat is detected.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.detectors.anomaly_detector import Threat

logger = logging.getLogger(__name__)


@dataclass
class RemediationResult:
    """Result of a remediation action execution"""
    action_type: str
    success: bool
    target: str
    message: str
    timestamp: str


class RuleRemediationExecutor:
    """Executes remediation actions from rule definitions"""

    def __init__(self, aws_executor: Optional[AWSActionExecutor] = None):
        """
        Initialize remediation executor
        Args:
            aws_executor: AWSActionExecutor instance (mocked in tests)
        """
        self.aws_executor = aws_executor or AWSActionExecutor()

    def execute_remediation(
        self,
        rule: Dict[str, Any],
        threat: Threat
    ) -> List[RemediationResult]:
        """
        Execute remediation actions for a threat based on rule definition
        Args:
            rule: Security rule with remediation_actions
            threat: Detected threat
        Returns:
            List of remediation results
        """
        results = []

        try:
            # Parse rule action
            action_config = rule.get('action', {})
            if isinstance(action_config, str):
                action_config = json.loads(action_config)

            # Check if auto-remediation is enabled
            if not action_config.get('auto_remediate', False):
                logger.info(f"Auto-remediation disabled for rule {rule['rule_id']}")
                return []

            # Get remediation actions
            remediation_actions = action_config.get('remediation_actions', [])
            if not remediation_actions:
                logger.info(f"No remediation actions defined for rule {rule['rule_id']}")
                return []

            # Execute each enabled action
            for action in remediation_actions:
                if not action.get('enabled', False):
                    continue

                result = self._execute_action(action, threat)
                if result:
                    results.append(result)

        except Exception as e:
            logger.error(f"Error executing remediation for rule {rule.get('rule_id')}: {e}")

        return results

    def _execute_action(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[RemediationResult]:
        """
        Execute a single remediation action
        Args:
            action: Action configuration
            threat: Detected threat with evidence
        Returns:
            RemediationResult or None if action type not supported
        """
        action_type = action.get('type')
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            if action_type == 'EC2_STOP':
                return self._execute_ec2_stop(action, threat, timestamp)
            elif action_type == 'S3_BLOCK_PUBLIC':
                return self._execute_s3_block(action, threat, timestamp)
            elif action_type == 'SG_RESTRICT':
                return self._execute_sg_restrict(action, threat, timestamp)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return None

        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return RemediationResult(
                action_type=action_type,
                success=False,
                target="unknown",
                message=str(e),
                timestamp=timestamp
            )

    def _execute_ec2_stop(
        self,
        action: Dict[str, Any],
        threat: Threat,
        timestamp: str
    ) -> Optional[RemediationResult]:
        """
        Execute EC2 stop remediation
        Extracts instance ID from threat evidence
        """
        params = action.get('parameters', {})
        region = params.get('region', 'us-east-1')

        # Extract instance ID from threat evidence
        instance_id = self._extract_instance_id_from_threat(threat)
        if not instance_id:
            return RemediationResult(
                action_type='EC2_STOP',
                success=False,
                target='unknown',
                message='Could not extract instance ID from threat evidence',
                timestamp=timestamp
            )

        success = self.aws_executor.stop_ec2_instance(instance_id, region)

        return RemediationResult(
            action_type='EC2_STOP',
            success=success,
            target=instance_id,
            message=f"{'Successfully stopped' if success else 'Failed to stop'} instance {instance_id}",
            timestamp=timestamp
        )

    def _execute_s3_block(
        self,
        action: Dict[str, Any],
        threat: Threat,
        timestamp: str
    ) -> Optional[RemediationResult]:
        """
        Execute S3 public access block remediation
        Extracts bucket name from threat evidence
        """
        # Extract bucket name from threat evidence
        bucket_name = self._extract_bucket_name_from_threat(threat)
        if not bucket_name:
            return RemediationResult(
                action_type='S3_BLOCK_PUBLIC',
                success=False,
                target='unknown',
                message='Could not extract bucket name from threat evidence',
                timestamp=timestamp
            )

        success = self.aws_executor.block_s3_public_access(bucket_name)

        return RemediationResult(
            action_type='S3_BLOCK_PUBLIC',
            success=success,
            target=bucket_name,
            message=f"{'Successfully blocked' if success else 'Failed to block'} public access on {bucket_name}",
            timestamp=timestamp
        )

    def _execute_sg_restrict(
        self,
        action: Dict[str, Any],
        threat: Threat,
        timestamp: str
    ) -> Optional[RemediationResult]:
        """
        Execute security group restriction remediation
        Currently placeholder - would require more complex implementation
        """
        params = action.get('parameters', {})
        sg_id = params.get('security_group_id')

        if not sg_id:
            return RemediationResult(
                action_type='SG_RESTRICT',
                success=False,
                target='unknown',
                message='No security group ID specified in action parameters',
                timestamp=timestamp
            )

        # Placeholder: actual implementation would restrict ingress rules
        logger.info(f"Security group restriction for {sg_id} (not yet implemented)")

        return RemediationResult(
            action_type='SG_RESTRICT',
            success=False,
            target=sg_id,
            message='Security group restriction not yet implemented',
            timestamp=timestamp
        )

    @staticmethod
    def _extract_instance_id_from_threat(threat: Threat) -> Optional[str]:
        """
        Extract EC2 instance ID from threat evidence
        Looks for 'instance_id' or 'InstanceId' field in evidence
        """
        if not threat.evidence:
            return None

        for item in threat.evidence:
            if isinstance(item, dict):
                if 'instance_id' in item:
                    return item['instance_id']
                if 'InstanceId' in item:
                    return item['InstanceId']
                if 'resource_id' in item:
                    resource = item['resource_id']
                    if resource.startswith('i-'):
                        return resource

        return None

    @staticmethod
    def _extract_bucket_name_from_threat(threat: Threat) -> Optional[str]:
        """
        Extract S3 bucket name from threat evidence
        Looks for 'bucket_name', 'BucketName', or 'bucket' field
        """
        if not threat.evidence:
            return None

        for item in threat.evidence:
            if isinstance(item, dict):
                if 'bucket_name' in item:
                    return item['bucket_name']
                if 'BucketName' in item:
                    return item['BucketName']
                if 'bucket' in item:
                    return item['bucket']
                if 'resource_id' in item and not item['resource_id'].startswith('i-'):
                    return item['resource_id']

        return None
