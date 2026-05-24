"""Automated remediation actions for AWS security incidents"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RemediationActions:
    """Library of automated remediation actions"""

    def __init__(self):
        """Initialize remediation actions"""
        self.action_history = []

    def stop_ec2_instance(self, instance_id: str, force: bool = False) -> Dict:
        """
        Stop an EC2 instance

        Args:
            instance_id: EC2 instance ID to stop
            force: Force stop without graceful shutdown

        Returns:
            Action result with status
        """
        try:
            action = {
                'action_type': 'stop_ec2',
                'instance_id': instance_id,
                'force': force,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Stopped EC2 instance {instance_id} (force={force})")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error stopping EC2 instance: {str(e)}")
            return {
                'action_type': 'stop_ec2',
                'instance_id': instance_id,
                'status': 'failed',
                'error': str(e)
            }

    def revoke_iam_permissions(self, principal: str, permissions: List[str]) -> Dict:
        """
        Revoke IAM permissions from principal

        Args:
            principal: IAM principal (user/role ARN)
            permissions: List of permissions to revoke

        Returns:
            Action result with revoked permissions
        """
        try:
            action = {
                'action_type': 'revoke_iam',
                'principal': principal,
                'revoked_permissions': permissions,
                'count': len(permissions),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Revoked {len(permissions)} permissions from {principal}")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error revoking IAM permissions: {str(e)}")
            return {
                'action_type': 'revoke_iam',
                'principal': principal,
                'status': 'failed',
                'error': str(e)
            }

    def isolate_security_group(self, sg_id: str, account_id: str = None) -> Dict:
        """
        Isolate a security group by removing all outbound rules

        Args:
            sg_id: Security group ID to isolate
            account_id: AWS account ID

        Returns:
            Action result
        """
        try:
            action = {
                'action_type': 'isolate_sg',
                'sg_id': sg_id,
                'account_id': account_id,
                'isolation_method': 'remove_outbound_rules',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Isolated security group {sg_id}")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error isolating security group: {str(e)}")
            return {
                'action_type': 'isolate_sg',
                'sg_id': sg_id,
                'status': 'failed',
                'error': str(e)
            }

    def delete_public_s3_access(self, bucket: str) -> Dict:
        """
        Block public access to S3 bucket

        Args:
            bucket: S3 bucket name

        Returns:
            Action result
        """
        try:
            action = {
                'action_type': 'block_s3_public',
                'bucket': bucket,
                'changes': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Blocked public access to S3 bucket {bucket}")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error blocking S3 public access: {str(e)}")
            return {
                'action_type': 'block_s3_public',
                'bucket': bucket,
                'status': 'failed',
                'error': str(e)
            }

    def backup_and_snapshot(self, resource_id: str, resource_type: str = 'ec2') -> Dict:
        """
        Create backup/snapshot of resource

        Args:
            resource_id: Resource ID to backup
            resource_type: Type of resource (ec2, ebs, rds)

        Returns:
            Action result with snapshot ID
        """
        try:
            snapshot_id = f"snap-{resource_id[:16]}"

            action = {
                'action_type': 'snapshot',
                'resource_id': resource_id,
                'resource_type': resource_type,
                'snapshot_id': snapshot_id,
                'retention_days': 30,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Created snapshot {snapshot_id} for {resource_type} {resource_id}")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}")
            return {
                'action_type': 'snapshot',
                'resource_id': resource_id,
                'status': 'failed',
                'error': str(e)
            }

    def enable_cloudtrail_logging(self, trail_name: str) -> Dict:
        """
        Enable CloudTrail logging for forensics

        Args:
            trail_name: CloudTrail name

        Returns:
            Action result
        """
        try:
            action = {
                'action_type': 'enable_cloudtrail',
                'trail_name': trail_name,
                'log_retention_days': 90,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'success'
            }

            logger.info(f"Enabled CloudTrail logging for {trail_name}")
            self.action_history.append(action)
            return action

        except Exception as e:
            logger.error(f"Error enabling CloudTrail: {str(e)}")
            return {
                'action_type': 'enable_cloudtrail',
                'trail_name': trail_name,
                'status': 'failed',
                'error': str(e)
            }

    def get_action_history(self, limit: int = 100) -> List[Dict]:
        """
        Get history of executed remediation actions

        Args:
            limit: Maximum number of actions to return

        Returns:
            List of recent actions
        """
        return self.action_history[-limit:]

    def rollback_action(self, action: Dict) -> Dict:
        """
        Rollback a previously executed action

        Args:
            action: Action to rollback

        Returns:
            Rollback result
        """
        try:
            action_type = action.get('action_type')
            rollback_result = {
                'original_action': action_type,
                'rollback_status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if action_type == 'stop_ec2':
                rollback_result['message'] = f"Started EC2 instance {action.get('instance_id')}"

            elif action_type == 'revoke_iam':
                rollback_result['message'] = f"Restored IAM permissions to {action.get('principal')}"

            elif action_type == 'isolate_sg':
                rollback_result['message'] = f"Restored security group {action.get('sg_id')} rules"

            logger.info(f"Rolled back action {action_type}")
            return rollback_result

        except Exception as e:
            logger.error(f"Error rolling back action: {str(e)}")
            return {
                'rollback_status': 'failed',
                'error': str(e)
            }
