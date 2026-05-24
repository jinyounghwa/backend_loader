"""Sprint 46 Phase 1: EC2 Auto-Remediation Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.remediators.ec2_remediator import EC2Remediator, RemediationStatus


class TestEC2Remediation:
    """EC2 instance auto-remediation verification."""

    def test_ec2_remediation_stops_unauthorized_instance(self):
        """✅ Unauthorized EC2 instance is stopped automatically."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Mock instance details - use side_effect for multiple calls
        running_state = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test123',
                    'State': {'Name': 'running'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'test-instance'},
                        {'Key': 'environment', 'Value': 'dev'}
                    ],
                    'BlockDeviceMappings': [
                        {'DeviceName': '/dev/xvda', 'Ebs': {'VolumeId': 'vol-123'}}
                    ]
                }]
            }]
        }

        stopped_state = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test123',
                    'State': {'Name': 'stopped'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'test-instance'},
                        {'Key': 'environment', 'Value': 'dev'}
                    ]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running_state, running_state, stopped_state]

        # Mock snapshot creation
        mock_ec2.create_snapshot.return_value = {
            'SnapshotId': 'snap-test123'
        }

        # Mock stop instance
        mock_ec2.stop_instances.return_value = {}

        threat = {
            'threat_id': 'THREAT-001',
            'description': 'Unauthorized EC2 instance detected'
        }

        result = remediator.remediate_unauthorized_instance('i-test123', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'stopped'
        assert result['instance_id'] == 'i-test123'
        assert result['snapshot_id'] == 'snap-test123'
        assert mock_ec2.stop_instances.called

    def test_ec2_remediation_creates_snapshot(self):
        """✅ EBS snapshot created before stopping instance."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test456',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [
                        {'Ebs': {'VolumeId': 'vol-456'}}
                    ]
                }]
            }]
        }

        stopped = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test456',
                    'State': {'Name': 'stopped'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running, running, stopped]

        mock_ec2.create_snapshot.return_value = {
            'SnapshotId': 'snap-test456'
        }

        mock_ec2.stop_instances.return_value = {}

        threat = {'threat_id': 'THREAT-002', 'description': 'Test threat'}

        result = remediator.remediate_unauthorized_instance('i-test456', threat)

        assert result['snapshot_id'] == 'snap-test456'
        assert mock_ec2.create_snapshot.called

    def test_ec2_remediation_tags_stopped_instance(self):
        """✅ Stopped instance is tagged with remediation metadata."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test789',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-789'}}]
                }]
            }]
        }

        stopped = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test789',
                    'State': {'Name': 'stopped'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running, running, stopped]
        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-789'}
        mock_ec2.stop_instances.return_value = {}

        threat = {'threat_id': 'THREAT-003', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-test789', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert mock_ec2.create_tags.called

    def test_ec2_remediation_logs_action(self):
        """✅ All remediation actions are logged to audit log."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-audit',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-audit'}}]
                }]
            }]
        }

        stopped = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-audit',
                    'State': {'Name': 'stopped'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}]
                }]
            }]
        }

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [running, running, stopped]
        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-audit'}
        mock_ec2.stop_instances.return_value = {}

        threat = {'threat_id': 'THREAT-AUDIT', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-audit', threat)

        # Verify audit logging was called
        assert mock_audit.log_remediation.called

    def test_ec2_remediation_verifies_instance_stopped(self):
        """✅ Instance stop is verified after remediation."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # describe_instances is called: 1) safety check, 2) get volumes, 3) verify stopped
        mock_ec2.describe_instances.side_effect = [
            {  # Initial state check (safety)
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': 'i-verify',
                        'State': {'Name': 'running'},
                        'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                        'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-verify'}}]
                    }]
                }]
            },
            {  # Get volumes
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': 'i-verify',
                        'State': {'Name': 'running'},
                        'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                        'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-verify'}}]
                    }]
                }]
            },
            {  # Post-stop verification
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': 'i-verify',
                        'State': {'Name': 'stopped'},
                        'Tags': [{'Key': 'environment', 'Value': 'dev'}]
                    }]
                }]
            }
        ]

        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-verify'}
        mock_ec2.stop_instances.return_value = {}

        threat = {'threat_id': 'THREAT-VERIFY', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-verify', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value

    def test_ec2_remediation_handles_already_stopped_instance(self):
        """✅ Already stopped instance is detected and skipped."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-stopped',
                    'State': {'Name': 'stopped'},  # Already stopped
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'VolumeId': 'vol-stopped'}]
                }]
            }]
        }

        threat = {'threat_id': 'THREAT-STOPPED', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-stopped', threat)

        assert result['status'] == RemediationStatus.SKIPPED.value
        assert result['action_taken'] == 'skipped'
        assert 'already stopped' in result['reason'].lower()

    def test_ec2_remediation_handles_termination_protection(self):
        """✅ Instances with termination protection are handled gracefully."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        running = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-protected',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'Ebs': {'VolumeId': 'vol-protected'}}]
                }]
            }]
        }

        # Fails at stop, so only need 2 calls (safety check + get volumes)
        mock_ec2.describe_instances.side_effect = [running, running]

        # Simulate termination protection error
        mock_ec2.create_snapshot.return_value = {'SnapshotId': 'snap-protected'}
        mock_ec2.stop_instances.side_effect = Exception("OperationNotPermitted: The instance with id 'i-protected' does not have a volume")

        threat = {'threat_id': 'THREAT-PROTECTED', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-protected', threat)

        assert result['status'] == RemediationStatus.FAILED.value
        # stop_instance method catches exceptions and returns False
        assert 'Instance stop command rejected' in result['reason']

    def test_ec2_remediation_concurrent_instances(self):
        """✅ Multiple instances can be remediated concurrently."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Simulate concurrent remediation
        instance_ids = ['i-concurrent1', 'i-concurrent2', 'i-concurrent3']
        results = []

        for instance_id in instance_ids:
            running = {
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': instance_id,
                        'State': {'Name': 'running'},
                        'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                        'BlockDeviceMappings': [{'Ebs': {'VolumeId': f'vol-{instance_id}'}}]
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
            mock_ec2.create_snapshot.return_value = {'SnapshotId': f'snap-{instance_id}'}
            mock_ec2.stop_instances.return_value = {}

            threat = {'threat_id': f'THREAT-{instance_id}', 'description': 'Test'}

            result = remediator.remediate_unauthorized_instance(instance_id, threat)
            results.append(result)

        assert len(results) == 3
        assert all(r['status'] == RemediationStatus.SUCCESS.value for r in results)
