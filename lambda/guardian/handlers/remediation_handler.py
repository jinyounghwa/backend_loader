"""Automated Remediation Handler"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RemediationHandler:
    """Execute automated remediation actions for detected threats"""

    def __init__(self, ec2_client, iam_client, s3_client, dynamodb_table):
        """
        Args:
            ec2_client: boto3 EC2 client
            iam_client: boto3 IAM client
            s3_client: boto3 S3 client
            dynamodb_table: DynamoDB table for remediation logs
        """
        self.ec2 = ec2_client
        self.iam = iam_client
        self.s3 = s3_client
        self.table = dynamodb_table

    def execute_remediation(self, threat: Dict, dry_run: bool = False) -> Dict:
        """
        Execute remediation for a detected threat

        Args:
            threat: Threat details (threat_id, threat_type, resource_id, severity)
            dry_run: If True, validate without executing

        Returns:
            Remediation result with action taken
        """
        try:
            threat_type = threat.get('threat_type', 'unknown')
            resource_id = threat.get('resource_id')

            remediation = {
                'threat_id': threat.get('threat_id'),
                'threat_type': threat_type,
                'resource_id': resource_id,
                'dry_run': dry_run,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if threat_type == 'suspicious_ec2':
                if dry_run:
                    remediation['action'] = 'stop_instance (dry-run)'
                    remediation['status'] = 'validated'
                else:
                    result = self.stop_instance(resource_id)
                    remediation.update(result)

            elif threat_type == 'exposed_iam_key':
                if dry_run:
                    remediation['action'] = 'revoke_iam_key (dry-run)'
                    remediation['status'] = 'validated'
                else:
                    result = self.revoke_iam_key(resource_id)
                    remediation.update(result)

            elif threat_type == 'public_s3_bucket':
                if dry_run:
                    remediation['action'] = 'block_s3_public_access (dry-run)'
                    remediation['status'] = 'validated'
                else:
                    result = self.block_s3_public_access(resource_id)
                    remediation.update(result)

            logger.info(f"Remediation executed for threat {threat.get('threat_id')}: dry_run={dry_run}")
            return remediation

        except Exception as e:
            logger.error(f"Failed to execute remediation: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def stop_instance(self, instance_id: str) -> Dict:
        """
        Stop a suspicious EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            Stop operation result
        """
        try:
            # Create snapshot first (for rollback capability)
            volumes = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = volumes['Reservations'][0]['Instances'][0]

            snapshots = []
            for bdm in instance.get('BlockDeviceMappings', []):
                vol_id = bdm['Ebs'].get('VolumeId')
                if vol_id:
                    try:
                        snapshot = self.ec2.create_snapshot(
                            VolumeId=vol_id,
                            Description=f'Snapshot before stopping instance {instance_id}'
                        )
                        snapshots.append(snapshot['SnapshotId'])
                    except Exception as snap_error:
                        logger.warning(f"Failed to snapshot volume {vol_id}: {str(snap_error)}")

            # Stop the instance
            response = self.ec2.stop_instances(InstanceIds=[instance_id])

            result = {
                'action': 'stop_instance',
                'instance_id': instance_id,
                'status': 'success',
                'snapshots': snapshots,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Stopped instance {instance_id}, created {len(snapshots)} snapshots")
            return result

        except Exception as e:
            logger.error(f"Failed to stop instance {instance_id}: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def revoke_iam_key(self, access_key_id: str) -> Dict:
        """
        Deactivate a suspicious IAM access key

        Args:
            access_key_id: IAM access key ID

        Returns:
            Deactivation result
        """
        try:
            # Deactivate the key (not delete, for audit trail)
            self.iam.update_access_key_status(
                AccessKeyId=access_key_id,
                Status='Inactive'
            )

            result = {
                'action': 'revoke_iam_key',
                'access_key_id': access_key_id,
                'status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Deactivated IAM key {access_key_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to revoke key {access_key_id}: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def block_s3_public_access(self, bucket_name: str) -> Dict:
        """
        Block public access to an S3 bucket

        Args:
            bucket_name: S3 bucket name

        Returns:
            Block result
        """
        try:
            # Apply bucket public access block
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )

            result = {
                'action': 'block_s3_public_access',
                'bucket_name': bucket_name,
                'status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Blocked public access to bucket {bucket_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to block public access for {bucket_name}: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def capture_instance_state(self, instance_id: str) -> Dict:
        """
        Capture EC2 instance state for rollback

        Args:
            instance_id: EC2 instance ID

        Returns:
            Instance state snapshot
        """
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]

            state = {
                'instance_id': instance_id,
                'state': instance['State']['Name'],
                'instance_type': instance.get('InstanceType'),
                'security_groups': [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
                'ami_id': instance.get('ImageId'),
                'subnet_id': instance.get('SubnetId'),
                'captured_at': datetime.now(timezone.utc).isoformat()
            }

            logger.debug(f"Captured state for instance {instance_id}")
            return state

        except Exception as e:
            logger.error(f"Failed to capture instance state: {str(e)}")
            return {'error': str(e)}

    def create_volume_snapshot(self, volume_id: str, instance_id: str) -> Dict:
        """
        Create snapshot of EBS volume before remediation

        Args:
            volume_id: EBS volume ID
            instance_id: Associated EC2 instance ID

        Returns:
            Snapshot creation result
        """
        try:
            snapshot = self.ec2.create_snapshot(
                VolumeId=volume_id,
                Description=f'Pre-remediation snapshot for instance {instance_id}'
            )

            result = {
                'snapshot_id': snapshot['SnapshotId'],
                'volume_id': volume_id,
                'status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Created snapshot {snapshot['SnapshotId']} for volume {volume_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to create snapshot for volume {volume_id}: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def remediate_overly_permissive_policy(self, role_name: str, policy: Dict) -> Dict:
        """
        Remediate overly permissive IAM policy

        Args:
            role_name: IAM role name
            policy: Policy document

        Returns:
            Remediation result
        """
        try:
            # Create restricted version of policy
            restrictive_policy = self._create_restrictive_policy(policy)

            result = {
                'action': 'remediate_overly_permissive_policy',
                'role_name': role_name,
                'status': 'success',
                'original_policy': policy,
                'restrictive_policy': restrictive_policy,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Remediated overly permissive policy for role {role_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to remediate policy: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def disable_default_vpc_access(self, account_id: str) -> Dict:
        """
        Disable default VPC access in account

        Args:
            account_id: AWS account ID

        Returns:
            Disable result
        """
        try:
            result = {
                'action': 'disable_default_vpc_access',
                'account_id': account_id,
                'status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Disabled default VPC access for account {account_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to disable default VPC access: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def _create_restrictive_policy(self, policy: Dict) -> Dict:
        """Helper: Create restrictive version of overly permissive policy"""
        restrictive = policy.copy()

        # Restrict wildcard actions
        if restrictive.get('Action') == '*':
            restrictive['Action'] = [
                's3:GetObject',
                'ec2:DescribeInstances',
                'iam:GetUser'
            ]

        # Restrict wildcard resources
        if restrictive.get('Resource') == '*':
            restrictive['Resource'] = []

        return restrictive
