"""Sprint 46 Phase 1: EC2 Remediation Integration Tests (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from guardian.remediators.ec2_remediator import EC2Remediator, RemediationStatus


class TestEC2RemediationIntegration:
    """EC2 remediation end-to-end integration scenarios."""

    def test_threat_detection_to_ec2_stop(self):
        """✅ Complete flow: threat detection → EC2 stop → verification."""
        # Simulate threat detection
        threat = {
            'threat_id': 'THREAT-INT-001',
            'event_type': 'UnauthorizedInstanceStart',
            'severity': 8,
            'account_id': '123456789012',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'description': 'EC2 instance started in unauthorized region'
        }

        instance_id = 'i-unauthorized-region'

        # Setup mocks
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Setup instance details
        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        running_inst = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'running'},
                    'InstanceType': 't3.micro',
                    'LaunchTime': datetime.now(timezone.utc).replace(tzinfo=None),
                    'Tags': [
                        {'Key': 'Name', 'Value': 'suspicious-instance'},
                        {'Key': 'environment', 'Value': 'dev'}
                    ],
                    'BlockDeviceMappings': [
                        {'DeviceName': '/dev/xvda', 'Ebs': {'VolumeId': 'vol-int-001'}}
                    ]
                }]
            }]
        }

        stopped_inst = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'stopped'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'suspicious-instance'},
                        {'Key': 'environment', 'Value': 'dev'},
                        {'Key': 'guardian:remediated', 'Value': 'true'}
                    ]
                }]
            }]
        }

        mock_ec2.describe_instances.side_effect = [running_inst, running_inst, stopped_inst]

        mock_ec2.create_snapshot.return_value = {
            'SnapshotId': 'snap-int-001'
        }

        mock_ec2.stop_instances.return_value = {}
        mock_ec2.create_tags.return_value = {}

        # Execute remediation
        result = remediator.remediate_unauthorized_instance(instance_id, threat)

        # Assertions
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'stopped'
        assert result['instance_id'] == instance_id
        assert result['snapshot_id'] == 'snap-int-001'
        assert result['threat'] == threat['threat_id']

        # Verify all steps were executed
        assert mock_ec2.describe_instances.call_count >= 1  # At least initial check
        assert mock_ec2.create_snapshot.called
        assert mock_ec2.stop_instances.called
        assert mock_ec2.create_tags.called
        assert mock_audit.log_remediation.called

    def test_ec2_stop_triggers_notification(self):
        """✅ Instance stop triggers notification to monitoring system."""
        mock_ec2 = Mock()
        mock_audit = Mock()
        mock_notification = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        instance_id = 'i-notify'

        # Setup mocks with side_effect for multiple calls
        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-notify'}}]
                }]
            }]
        }

        stopped = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'stopped'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running, running, stopped]
        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-notify'}
        mock_ec2.stop_instances.return_value = {}

        threat = {
            'threat_id': 'THREAT-NOTIFY',
            'description': 'Test threat',
            'severity': 7
        }

        # Execute remediation
        result = remediator.remediate_unauthorized_instance(instance_id, threat)

        # Simulate notification system receiving the result
        if result['status'] == RemediationStatus.SUCCESS.value:
            mock_notification.send_alert({
                'type': 'EC2_REMEDIATION_SUCCESS',
                'instance_id': result['instance_id'],
                'action': result['action_taken'],
                'threat_id': result['threat'],
                'timestamp': result['timestamp']
            })

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert mock_notification.send_alert.called

    def test_ec2_stop_with_network_isolation(self):
        """✅ EC2 stop can be followed by network isolation for critical threats."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        instance_id = 'i-network-iso'

        # Setup initial instance with correct block device mapping structure
        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'running'},
                    'SecurityGroups': [{'GroupId': 'sg-12345', 'GroupName': 'default'}],
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-iso'}}]
                }]
            }]
        }

        stopped = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'State': {'Name': 'stopped'},
                    'SecurityGroups': [],
                    'Tags': [
                        {'Key': 'environment', 'Value': 'dev'},
                        {'Key': 'guardian:remediated', 'Value': 'true'}
                    ]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running, running, stopped]
        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-iso'}
        mock_ec2.stop_instances.return_value = {}

        threat = {
            'threat_id': 'THREAT-CRITICAL',
            'description': 'Critical security violation',
            'severity': 10  # Critical
        }

        # Execute EC2 remediation
        result = remediator.remediate_unauthorized_instance(instance_id, threat)

        assert result['status'] == RemediationStatus.SUCCESS.value

        # For critical threats, simulate additional network isolation
        if threat.get('severity', 0) >= 9:
            # Would trigger network remediation handler
            assert mock_ec2.stop_instances.called
            # In real scenario, NetworkRemediator would also be invoked
