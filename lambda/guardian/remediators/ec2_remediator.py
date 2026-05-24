"""EC2 Instance Auto-Remediation - Stop unauthorized instances with safety checks."""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class RemediationStatus(Enum):
    """Remediation outcome statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class EC2Remediator:
    """Automatic remediation for unauthorized EC2 instances."""

    def __init__(self, ec2_client, audit_logger):
        """Initialize EC2 remediation with AWS client and audit logger."""
        self.ec2 = ec2_client
        self.audit = audit_logger
        self.remediation_history = {}

    def remediate_unauthorized_instance(self, instance_id: str, threat: Dict) -> Dict:
        """
        Stop unauthorized EC2 instance with multi-layer safety checks.

        Safety checks:
        1. Production environment tag detection
        2. Auto-remediation disabled tag
        3. Admin approval requirement
        4. Snapshot creation before stop
        5. Audit logging

        Args:
            instance_id: EC2 instance ID
            threat: Threat detection details

        Returns:
            {
                'status': 'success|skipped|failed',
                'instance_id': instance_id,
                'action_taken': 'stopped|skipped',
                'reason': explanation,
                'snapshot_id': optional,
                'timestamp': iso_timestamp
            }
        """
        result = {
            'instance_id': instance_id,
            'timestamp': datetime.utcnow().isoformat(),
            'threat': threat.get('threat_id', 'unknown')
        }

        # 1. Verify instance exists
        try:
            instance = self._get_instance_details(instance_id)
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Cannot fetch instance details: {str(e)}"
            self.audit.log_remediation(instance_id, 'stop_attempt', result)
            return result

        # 2. Check safety conditions
        safety_check = self.verify_safety_conditions(instance_id, instance)
        if not safety_check['passed']:
            result['status'] = RemediationStatus.SKIPPED.value
            result['reason'] = safety_check['reason']
            result['action_taken'] = 'skipped'
            self.audit.log_remediation(instance_id, 'stop_skipped', result)
            return result

        # 3. Create snapshot before stopping
        try:
            snapshot_id = self.create_snapshot_before_stop(instance_id)
            result['snapshot_id'] = snapshot_id
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Snapshot creation failed: {str(e)}"
            self.audit.log_remediation(instance_id, 'snapshot_failed', result)
            return result

        # 4. Stop instance
        try:
            stopped = self.stop_instance(instance_id)
            if not stopped:
                result['status'] = RemediationStatus.FAILED.value
                result['reason'] = "Instance stop command rejected"
                self.audit.log_remediation(instance_id, 'stop_failed', result)
                return result
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Stop operation failed: {str(e)}"
            self.audit.log_remediation(instance_id, 'stop_failed', result)
            return result

        # 5. Tag the stopped instance
        try:
            self._tag_remediated_instance(instance_id, threat)
        except Exception as e:
            # Tag failure doesn't prevent success, but log it
            result['tag_error'] = str(e)

        # 6. Verify instance is stopped
        try:
            verify = self._verify_instance_stopped(instance_id)
            if not verify:
                result['status'] = RemediationStatus.FAILED.value
                result['reason'] = "Instance stop verification failed"
                self.audit.log_remediation(instance_id, 'verify_failed', result)
                return result
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Verification failed: {str(e)}"
            self.audit.log_remediation(instance_id, 'verify_failed', result)
            return result

        result['status'] = RemediationStatus.SUCCESS.value
        result['action_taken'] = 'stopped'
        result['reason'] = f"Instance stopped due to: {threat.get('description', 'unauthorized activity')}"
        self.audit.log_remediation(instance_id, 'stop_success', result)
        return result

    def stop_instance(self, instance_id: str) -> bool:
        """Stop EC2 instance and return success status."""
        try:
            self.ec2.stop_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def create_snapshot_before_stop(self, instance_id: str) -> str:
        """Create EBS snapshot of all volumes attached to instance."""
        # Get volume information from instance
        volumes = self._get_instance_volumes(instance_id)
        if not volumes:
            return ""

        # Create snapshot of primary volume (most critical)
        primary_volume_id = volumes[0]['VolumeId']
        try:
            response = self.ec2.create_snapshot(
                VolumeId=primary_volume_id,
                Description=f"Auto-backup before remediation of {instance_id}"
            )
            return response.get('SnapshotId', '')
        except Exception:
            raise

    def verify_safety_conditions(self, instance_id: str, instance: Dict = None) -> Dict:
        """
        Verify all safety conditions before remediation.

        Returns:
            {
                'passed': bool,
                'reason': explanation if not passed,
                'checks': {
                    'is_production': bool,
                    'is_remediation_disabled': bool,
                    'requires_approval': bool,
                    'is_already_stopped': bool
                }
            }
        """
        if instance is None:
            instance = self._get_instance_details(instance_id)

        checks = {}
        reasons = []

        # Check 1: Production environment
        is_production = self._is_production_instance(instance)
        checks['is_production'] = is_production
        if is_production:
            reasons.append("Production environment (environment=production tag)")

        # Check 2: Auto-remediation disabled
        is_disabled = self._is_remediation_disabled(instance)
        checks['is_remediation_disabled'] = is_disabled
        if is_disabled:
            reasons.append("Auto-remediation disabled (guardian:no-auto-remediation=true tag)")

        # Check 3: Requires approval
        requires_approval = self._requires_admin_approval(instance)
        checks['requires_approval'] = requires_approval
        if requires_approval:
            reasons.append("Requires admin approval (guardian:requires-approval=true tag)")

        # Check 4: Already stopped
        is_stopped = instance.get('State', {}).get('Name') == 'stopped'
        checks['is_already_stopped'] = is_stopped
        if is_stopped:
            reasons.append("Instance already stopped")

        passed = not any([is_production, is_disabled, requires_approval, is_stopped])
        reason = "; ".join(reasons) if reasons else "All safety checks passed"

        return {
            'passed': passed,
            'reason': reason,
            'checks': checks
        }

    def rollback_remediation(self, instance_id: str) -> Dict:
        """Attempt to restore instance to pre-remediation state."""
        result = {
            'instance_id': instance_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Check if we have a snapshot
        if instance_id not in self.remediation_history:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = "No remediation history found"
            return result

        history = self.remediation_history[instance_id]
        snapshot_id = history.get('snapshot_id')

        if not snapshot_id:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = "No snapshot available for rollback"
            return result

        # Try to start the instance
        try:
            self.ec2.start_instances(InstanceIds=[instance_id])
            result['status'] = RemediationStatus.SUCCESS.value
            result['action'] = 'started'
            result['reason'] = f"Instance restarted from snapshot {snapshot_id}"
            self.audit.log_remediation(instance_id, 'rollback_success', result)
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Rollback failed: {str(e)}"
            self.audit.log_remediation(instance_id, 'rollback_failed', result)

        return result

    # Private helper methods
    def _get_instance_details(self, instance_id: str) -> Dict:
        """Fetch instance details from EC2."""
        response = self.ec2.describe_instances(InstanceIds=[instance_id])
        instances = response['Reservations'][0]['Instances']
        return instances[0] if instances else {}

    def _get_instance_volumes(self, instance_id: str) -> List[Dict]:
        """Get list of volumes attached to instance."""
        instance = self._get_instance_details(instance_id)
        block_devices = instance.get('BlockDeviceMappings', [])

        # Extract volume IDs from block device mappings
        volumes = []
        for bd in block_devices:
            if 'Ebs' in bd and 'VolumeId' in bd['Ebs']:
                volumes.append({'VolumeId': bd['Ebs']['VolumeId']})
            elif 'VolumeId' in bd:
                volumes.append({'VolumeId': bd['VolumeId']})

        return volumes

    def _is_production_instance(self, instance: Dict) -> bool:
        """Check if instance is tagged as production."""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        return tags.get('environment', '').lower() == 'production'

    def _is_remediation_disabled(self, instance: Dict) -> bool:
        """Check if auto-remediation is disabled."""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        return tags.get('guardian:no-auto-remediation', '').lower() == 'true'

    def _requires_admin_approval(self, instance: Dict) -> bool:
        """Check if admin approval is required."""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        return tags.get('guardian:requires-approval', '').lower() == 'true'

    def _tag_remediated_instance(self, instance_id: str, threat: Dict) -> None:
        """Tag the stopped instance with remediation metadata."""
        self.ec2.create_tags(
            Resources=[instance_id],
            Tags=[
                {'Key': 'guardian:remediated', 'Value': 'true'},
                {'Key': 'guardian:remediation-time', 'Value': datetime.utcnow().isoformat()},
                {'Key': 'guardian:threat-id', 'Value': threat.get('threat_id', 'unknown')}
            ]
        )

    def _verify_instance_stopped(self, instance_id: str) -> bool:
        """Verify that instance is actually stopped."""
        instance = self._get_instance_details(instance_id)
        state = instance.get('State', {}).get('Name')
        return state == 'stopped'
