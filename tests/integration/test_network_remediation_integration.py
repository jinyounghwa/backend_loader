"""Sprint 46 Phase 4: Network Isolation Integration Tests (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from guardian.remediators.network_remediator import NetworkRemediator, RemediationStatus


class TestNetworkRemediationIntegration:
    """Network isolation end-to-end integration scenarios."""

    def test_threat_detection_to_network_isolation(self):
        """✅ Complete flow: threat detection → network isolation → audit log."""
        threat = {
            'threat_id': 'THREAT-NET-INT-001',
            'event_type': 'UnauthorizedPublicAccess',
            'severity': 9,
            'instance_id': 'i-compromised-production',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'description': 'Instance exposed to public internet'
        }

        instance_id = threat['instance_id']
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        # Step 1: Detect unauthorized access (simulation)
        # Step 2: Isolate instance
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-prod',
                    'SecurityGroups': [
                        {'GroupId': 'sg-prod-1'},
                        {'GroupId': 'sg-prod-2'}
                    ]
                }]
            }]
        }
        mock_ec2.create_security_group.return_value = {
            'GroupId': 'sg-isolation-prod'
        }
        mock_ec2.modify_instance_attribute.return_value = {}

        result = remediator.isolate_instance(instance_id, threat)

        # Assertions
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'isolated'
        assert len(result['original_security_groups']) == 2
        assert result['new_security_group_id'] == 'sg-isolation-prod'
        assert mock_audit.log_remediation.called

    def test_network_isolation_with_rollback(self):
        """✅ Network isolation can be rolled back to restore connectivity."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-isolated-001'
        threat = {
            'threat_id': 'THREAT-NET-INT-002',
            'description': 'Test isolation'
        }

        # Step 1: Isolate
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [
                        {'GroupId': 'sg-original-prod'},
                        {'GroupId': 'sg-original-app'}
                    ]
                }]
            }]
        }
        mock_ec2.create_security_group.return_value = {
            'GroupId': 'sg-isolated-temp'
        }
        mock_ec2.modify_instance_attribute.return_value = {}

        isolate_result = remediator.isolate_instance(instance_id, threat)
        assert isolate_result['status'] == RemediationStatus.SUCCESS.value

        # Step 2: Verify isolation was recorded
        assert instance_id in remediator.remediation_history

        # Step 3: Restore connectivity
        restore_result = remediator.restore_connectivity(instance_id)

        assert restore_result['status'] == RemediationStatus.SUCCESS.value
        assert restore_result['action_taken'] == 'restored'
        assert len(restore_result['restored_groups']) == 2
        assert restore_result['restored_groups'][0] == 'sg-original-prod'
        assert restore_result['restored_groups'][1] == 'sg-original-app'
        # History should be cleaned
        assert instance_id not in remediator.remediation_history

    def test_network_isolation_concurrent_instances(self):
        """✅ Multiple instances can be isolated concurrently with separate rollback history."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        threat = {
            'threat_id': 'THREAT-NET-INT-003',
            'description': 'Concurrent threat'
        }

        instances = [
            'i-concurrent-001',
            'i-concurrent-002',
            'i-concurrent-003'
        ]

        # Mock responses for each instance
        isolation_results = []

        for idx, instance_id in enumerate(instances):
            mock_ec2.describe_instances.return_value = {
                'Reservations': [{
                    'Instances': [{
                        'InstanceId': instance_id,
                        'VpcId': f'vpc-{idx}',
                        'SecurityGroups': [
                            {'GroupId': f'sg-orig-{idx}'}
                        ]
                    }]
                }]
            }
            mock_ec2.create_security_group.return_value = {
                'GroupId': f'sg-isolated-{idx}'
            }
            mock_ec2.modify_instance_attribute.return_value = {}

            result = remediator.isolate_instance(instance_id, threat)
            isolation_results.append(result)

            assert result['status'] == RemediationStatus.SUCCESS.value
            assert result['new_security_group_id'] == f'sg-isolated-{idx}'

        # Verify each has separate rollback history
        assert len(remediator.remediation_history) == 3

        for instance_id in instances:
            assert instance_id in remediator.remediation_history
            history = remediator.remediation_history[instance_id]
            assert 'original_groups' in history
            assert 'isolated_group' in history
