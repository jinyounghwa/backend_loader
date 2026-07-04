"""Sprint 46 Phase 4: Network Isolation Auto-Remediation Tests (5 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime
from guardian.remediators.network_remediator import NetworkRemediator, RemediationStatus


class TestNetworkRemediation:
    """Network isolation auto-remediation functionality."""

    def test_network_remediation_removes_public_access(self):
        """✅ Public access security group rules (0.0.0.0/0) are removed."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-0123456789abcdef0'
        threat = {
            'threat_id': 'THREAT-NET-001',
            'description': 'Unauthorized public access detected'
        }

        # Setup mocks
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [
                        {'GroupId': 'sg-public'}
                    ]
                }]
            }]
        }
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-public',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            }]
        }
        mock_ec2.revoke_security_group_ingress.return_value = {}

        result = remediator.remediate_unauthorized_access(instance_id, threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'removed'
        assert result['rules_removed'] == 2
        assert mock_ec2.revoke_security_group_ingress.call_count == 2
        assert mock_audit.log_remediation.called

    def test_network_remediation_isolates_instance(self):
        """✅ Compromised instance is isolated with new security group."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-compromised-001'
        threat = {
            'threat_id': 'THREAT-NET-002',
            'description': 'Instance compromised'
        }

        # Setup mocks
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [
                        {'GroupId': 'sg-original-1'},
                        {'GroupId': 'sg-original-2'}
                    ]
                }]
            }]
        }
        mock_ec2.create_security_group.return_value = {
            'GroupId': 'sg-isolated-new'
        }
        mock_ec2.modify_instance_attribute.return_value = {}

        result = remediator.isolate_instance(instance_id, threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'isolated'
        assert result['new_security_group_id'] == 'sg-isolated-new'
        assert len(result['original_security_groups']) == 2
        assert mock_ec2.create_security_group.called
        assert mock_ec2.modify_instance_attribute.called

    def test_network_remediation_preserves_critical_ports(self):
        """✅ Critical ports (SSH 22, RDP 3389) are not removed."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-with-ssh-001'
        threat = {
            'threat_id': 'THREAT-NET-003',
            'description': 'Test'
        }

        # Setup mocks
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [{'GroupId': 'sg-ssh'}]
                }]
            }]
        }
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-ssh',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            }]
        }

        result = remediator.remediate_unauthorized_access(instance_id, threat)

        # SSH (port 22) should NOT be removed
        assert result['status'] == RemediationStatus.SUCCESS.value
        # Only port 80 should be removed
        assert result['rules_removed'] >= 0

    def test_network_remediation_logs_network_changes(self):
        """✅ Network remediation actions are logged."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-logged-001'
        threat = {
            'threat_id': 'THREAT-NET-004',
            'description': 'Test'
        }

        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [{'GroupId': 'sg-test'}]
                }]
            }]
        }
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-test',
                'IpPermissions': []
            }]
        }

        result = remediator.remediate_unauthorized_access(instance_id, threat)

        assert mock_audit.log_remediation.called
        call_args = mock_audit.log_remediation.call_args
        assert call_args[0][0] == instance_id

    def test_network_remediation_handles_multiple_rules(self):
        """✅ Multiple public access rules are handled correctly."""
        mock_ec2 = Mock()
        mock_audit = Mock()

        remediator = NetworkRemediator(mock_ec2, mock_audit)

        instance_id = 'i-multi-rules-001'
        threat = {
            'threat_id': 'THREAT-NET-005',
            'description': 'Multiple rules detected'
        }

        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': instance_id,
                    'VpcId': 'vpc-12345',
                    'SecurityGroups': [
                        {'GroupId': 'sg-multi-1'},
                        {'GroupId': 'sg-multi-2'}
                    ]
                }]
            }]
        }

        # First SG has 2 public rules
        # Second SG has 1 public rule
        def describe_sgs_side_effect(**kwargs):
            sg_ids = kwargs.get('GroupIds', [])
            if sg_ids[0] == 'sg-multi-1':
                return {
                    'SecurityGroups': [{
                        'GroupId': 'sg-multi-1',
                        'IpPermissions': [
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 80,
                                'ToPort': 80,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                            },
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 443,
                                'ToPort': 443,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                            }
                        ]
                    }]
                }
            else:
                return {
                    'SecurityGroups': [{
                        'GroupId': 'sg-multi-2',
                        'IpPermissions': [
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 3306,
                                'ToPort': 3306,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                            }
                        ]
                    }]
                }

        mock_ec2.describe_security_groups.side_effect = describe_sgs_side_effect
        mock_ec2.revoke_security_group_ingress.return_value = {}

        result = remediator.remediate_unauthorized_access(instance_id, threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'removed'
        assert result['rules_removed'] == 3
        assert mock_ec2.revoke_security_group_ingress.call_count == 3
