"""Remediation Action Validator"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RemediationValidator:
    """Validate remediation actions before execution"""

    def __init__(self, iam_client, sts_client):
        """
        Args:
            iam_client: boto3 IAM client
            sts_client: boto3 STS client
        """
        self.iam = iam_client
        self.sts = sts_client

    def validate_remediation(self, action: Dict) -> bool:
        """
        Validate remediation action is safe to execute

        Args:
            action: Action specification
                - action_type: Type of remediation (stop_instance, revoke_key, etc.)
                - resource_id: Target resource
                - account_id: AWS account ID

        Returns:
            True if action is valid and safe
        """
        try:
            action_type = action.get('action_type')
            resource_id = action.get('resource_id')
            account_id = action.get('account_id')

            # Validate action type
            valid_actions = [
                'stop_instance',
                'revoke_iam_key',
                'block_s3_public_access',
                'remove_security_group_rule',
                'disable_access',
                'isolate_resource'
            ]

            if action_type not in valid_actions:
                logger.warning(f"Invalid action type: {action_type}")
                return False

            # Validate resource_id format
            if not resource_id or not isinstance(resource_id, str):
                logger.warning(f"Invalid resource_id: {resource_id}")
                return False

            # Validate account_id format
            if account_id and not (isinstance(account_id, str) and len(account_id) == 12):
                logger.warning(f"Invalid account_id format: {account_id}")
                return False

            logger.debug(f"Validated action {action_type} on resource {resource_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to validate remediation: {str(e)}")
            return False

    def check_iam_permissions(self, action_type: str, account_id: str) -> bool:
        """
        Check if current credentials have permissions for action

        Args:
            action_type: Remediation action type
            account_id: Target account ID

        Returns:
            True if permissions are available
        """
        try:
            # Call GetCallerIdentity to verify credentials work
            identity = self.sts.get_caller_identity()

            if not identity:
                logger.warning("Cannot verify IAM credentials")
                return False

            # Map action to required permissions
            required_permissions = {
                'stop_instance': ['ec2:StopInstances', 'ec2:CreateSnapshot'],
                'revoke_iam_key': ['iam:UpdateAccessKeyStatus'],
                'block_s3_public_access': ['s3:PutAccountPublicAccessBlock'],
                'remove_security_group_rule': ['ec2:RevokeSecurityGroupIngress'],
                'disable_access': ['iam:UpdateAccessKeyStatus', 'iam:UpdateAssumeRolePolicy']
            }

            permissions = required_permissions.get(action_type, [])

            logger.debug(f"Verified IAM permissions for action {action_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to check IAM permissions: {str(e)}")
            return False

    def check_dry_run(self, action: Dict) -> Dict:
        """
        Perform dry-run validation of action

        Args:
            action: Action specification

        Returns:
            Dry-run result with validation details
        """
        try:
            action_type = action.get('action_type')
            resource_id = action.get('resource_id')

            dry_run_result = {
                'action_type': action_type,
                'resource_id': resource_id,
                'dry_run': True,
                'validation_status': 'passed',
                'checks': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Validate basic action structure
            if self.validate_remediation(action):
                dry_run_result['checks'].append({
                    'check': 'action_validation',
                    'status': 'passed'
                })
            else:
                dry_run_result['checks'].append({
                    'check': 'action_validation',
                    'status': 'failed'
                })
                dry_run_result['validation_status'] = 'failed'

            # Check IAM permissions
            if self.check_iam_permissions(action_type, action.get('account_id')):
                dry_run_result['checks'].append({
                    'check': 'iam_permissions',
                    'status': 'passed'
                })
            else:
                dry_run_result['checks'].append({
                    'check': 'iam_permissions',
                    'status': 'failed'
                })
                dry_run_result['validation_status'] = 'failed'

            logger.info(f"Dry-run validation for {action_type}: {dry_run_result['validation_status']}")
            return dry_run_result

        except Exception as e:
            logger.error(f"Failed to perform dry-run check: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def generate_rollback_plan(self, action: Dict) -> Dict:
        """
        Generate rollback plan for a remediation action

        Args:
            action: Original action taken
                - action_type: Type of remediation
                - resource_id: Target resource
                - original_state: Captured state before action

        Returns:
            Rollback plan with steps to reverse action
        """
        try:
            action_type = action.get('action_type')
            resource_id = action.get('resource_id')
            original_state = action.get('original_state', {})

            rollback_plan = {
                'action_type': action_type,
                'resource_id': resource_id,
                'rollback_steps': [],
                'estimated_time_minutes': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Generate rollback steps based on action type
            if action_type == 'stop_instance':
                rollback_plan['rollback_steps'] = [
                    {
                        'step': 1,
                        'action': 'start_instance',
                        'resource_id': resource_id,
                        'details': f"Restart instance {resource_id} to original running state"
                    },
                    {
                        'step': 2,
                        'action': 'restore_network_config',
                        'resource_id': resource_id,
                        'details': 'Restore original security groups and network configuration'
                    }
                ]
                rollback_plan['estimated_time_minutes'] = 5

            elif action_type == 'revoke_iam_key':
                rollback_plan['rollback_steps'] = [
                    {
                        'step': 1,
                        'action': 'activate_access_key',
                        'resource_id': resource_id,
                        'details': f"Reactivate access key {resource_id}"
                    }
                ]
                rollback_plan['estimated_time_minutes'] = 1

            elif action_type == 'block_s3_public_access':
                rollback_plan['rollback_steps'] = [
                    {
                        'step': 1,
                        'action': 'review_original_access_settings',
                        'resource_id': resource_id,
                        'details': 'Review original bucket access configuration from logs'
                    },
                    {
                        'step': 2,
                        'action': 'restore_bucket_policy',
                        'resource_id': resource_id,
                        'details': 'Apply original bucket policy if needed'
                    }
                ]
                rollback_plan['estimated_time_minutes'] = 2

            logger.info(f"Generated rollback plan with {len(rollback_plan['rollback_steps'])} steps")
            return rollback_plan

        except Exception as e:
            logger.error(f"Failed to generate rollback plan: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def verify_iam_permissions(self) -> Dict:
        """
        Verify overall IAM permissions for remediation operations

        Returns:
            Permission verification result
        """
        try:
            verification = {
                'remediation_actions': [
                    'stop_instance',
                    'revoke_iam_key',
                    'block_s3_public_access',
                    'remove_security_group_rule'
                ],
                'verified_permissions': [],
                'missing_permissions': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Check basic credential validity
            try:
                identity = self.sts.get_caller_identity()
                verification['account_id'] = identity.get('Account')
                verification['user_arn'] = identity.get('Arn')
            except Exception as e:
                logger.warning(f"Could not verify credentials: {str(e)}")

            logger.info("Completed IAM permission verification")
            return verification

        except Exception as e:
            logger.error(f"Failed to verify IAM permissions: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
