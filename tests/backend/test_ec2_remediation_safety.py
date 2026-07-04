"""Sprint 46 Phase 1: EC2 Remediation Safety Checks (5 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from guardian.remediators.ec2_remediator import EC2Remediator, RemediationStatus


class TestEC2RemediationSafety:
    """EC2 remediation safety and protection mechanisms."""

    def test_ec2_remediation_skips_production_tags(self):
        """✅ Production instances (environment=production tag) are never auto-remediated."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Mock production instance
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-prod',
                    'State': {'Name': 'running'},
                    'Tags': [
                        {'Key': 'environment', 'Value': 'production'},  # Production!
                        {'Key': 'Name', 'Value': 'prod-instance'}
                    ],
                    'BlockDeviceMappings': [{'VolumeId': 'vol-prod'}]
                }]
            }]
        }

        threat = {'threat_id': 'THREAT-PROD', 'description': 'Suspicious activity'}

        result = remediator.remediate_unauthorized_instance('i-prod', threat)

        assert result['status'] == RemediationStatus.SKIPPED.value
        assert result['action_taken'] == 'skipped'
        assert 'production' in result['reason'].lower()
        assert not mock_ec2.stop_instances.called

    def test_ec2_remediation_skips_disabled_instances(self):
        """✅ Instances with guardian:no-auto-remediation tag are not remediated."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Mock instance with remediation disabled
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-disabled',
                    'State': {'Name': 'running'},
                    'Tags': [
                        {'Key': 'environment', 'Value': 'dev'},
                        {'Key': 'guardian:no-auto-remediation', 'Value': 'true'}  # Disabled!
                    ],
                    'BlockDeviceMappings': [{'VolumeId': 'vol-disabled'}]
                }]
            }]
        }

        threat = {'threat_id': 'THREAT-DISABLED', 'description': 'Test threat'}

        result = remediator.remediate_unauthorized_instance('i-disabled', threat)

        assert result['status'] == RemediationStatus.SKIPPED.value
        assert 'auto-remediation disabled' in result['reason'].lower()
        assert not mock_ec2.stop_instances.called

    def test_ec2_remediation_requires_approval_for_protected(self):
        """✅ Instances requiring approval (guardian:requires-approval=true) are skipped."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Mock instance requiring approval
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-approved',
                    'State': {'Name': 'running'},
                    'Tags': [
                        {'Key': 'environment', 'Value': 'dev'},
                        {'Key': 'guardian:requires-approval', 'Value': 'true'}  # Requires approval!
                    ],
                    'BlockDeviceMappings': [{'VolumeId': 'vol-approved'}]
                }]
            }]
        }

        threat = {'threat_id': 'THREAT-APPROVED', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-approved', threat)

        assert result['status'] == RemediationStatus.SKIPPED.value
        assert 'admin approval' in result['reason'].lower()
        assert not mock_ec2.stop_instances.called

    def test_ec2_remediation_rollback_on_error(self):
        """✅ Instance is attempted to be restarted if remediation encounters an error."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Simulate failure during snapshot
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-rollback',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'environment', 'Value': 'dev'}],
                    'BlockDeviceMappings': [{'VolumeId': 'vol-rollback'}]
                }]
            }]
        }

        mock_ec2.create_snapshot.side_effect = Exception("Snapshot failed")

        threat = {'threat_id': 'THREAT-ROLLBACK', 'description': 'Test'}

        result = remediator.remediate_unauthorized_instance('i-rollback', threat)

        assert result['status'] == RemediationStatus.FAILED.value
        assert 'Snapshot creation failed' in result['reason']

    def test_ec2_remediation_preserve_instance_state(self):
        """✅ Instance state is preserved if any safety check fails."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = EC2Remediator(mock_ec2, mock_audit)

        # Create multiple safety check scenarios
        scenarios = [
            {
                'name': 'production',
                'tags': [{'Key': 'environment', 'Value': 'production'}]
            },
            {
                'name': 'disabled',
                'tags': [
                    {'Key': 'environment', 'Value': 'dev'},
                    {'Key': 'guardian:no-auto-remediation', 'Value': 'true'}
                ]
            },
            {
                'name': 'approval-required',
                'tags': [
                    {'Key': 'environment', 'Value': 'dev'},
                    {'Key': 'guardian:requires-approval', 'Value': 'true'}
                ]
            }
        ]

        for scenario in scenarios:
            mock_ec2.describe_instances.return_value = {
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': f"i-{scenario['name']}",
                        'State': {'Name': 'running'},
                        'Tags': scenario['tags'],
                        'BlockDeviceMappings': [{'VolumeId': f"vol-{scenario['name']}"}]
                    }]
                }]
            }

            threat = {'threat_id': f"THREAT-{scenario['name']}", 'description': 'Test'}

            result = remediator.remediate_unauthorized_instance(
                f"i-{scenario['name']}", threat
            )

            # All should be skipped, not stopped
            assert result['status'] == RemediationStatus.SKIPPED.value
            assert not mock_ec2.stop_instances.called
