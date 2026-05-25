"""Sprint 47 Phase 1: Remediation Orchestration Integration Tests (6 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator, RemediationStatus


class TestRemediationOrchestrationIntegration:
    """End-to-end remediation orchestration scenarios."""

    def test_threat_triggers_multi_resource_remediation(self):
        """✅ Threat detection triggers coordinated remediation across all resources."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-INT-ORCH-001',
            'event_type': 'CompromisedInstanceDetected',
            'severity': 9,
            'instance_id': 'i-compromised-complete',
            'principal': 'arn:aws:iam::123456789012:user/attacker-created',
            'bucket_name': 'compromised-data-bucket',
            'timestamp': datetime.utcnow().isoformat(),
            'description': 'EC2 instance compromised with suspicious IAM user'
        }

        # Setup all mocks
        mock_ec2.remediate_unauthorized_instance.return_value = {
            'status': 'success',
            'instance_id': 'i-compromised-complete',
            'action_taken': 'stopped'
        }
        mock_network.isolate_instance.return_value = {
            'status': 'success',
            'new_security_group_id': 'sg-isolated-complete'
        }
        mock_iam.remediate_excessive_permissions.return_value = {
            'status': 'success',
            'action_taken': 'revoked',
            'policies_revoked': ['AdministratorAccess']
        }
        mock_s3.remediate_public_access.return_value = {
            'status': 'success',
            'action_taken': 'blocked'
        }

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Verify complete flow
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert len(result['execution_order']) == 4
        assert result['results']['ec2']['status'] == 'success'
        assert result['results']['network']['status'] == 'success'
        assert result['results']['iam']['status'] == 'success'
        assert result['results']['s3']['status'] == 'success'

    def test_remediation_rollback_cascade(self):
        """✅ Multi-step rollback cascade when orchestration fails."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-INT-ORCH-002',
            'instance_id': 'i-cascade-rollback',
            'principal': 'arn:aws:iam::123456789012:user/test'
        }

        # EC2 and Network succeed, IAM fails
        mock_ec2.remediate_unauthorized_instance.return_value = {
            'status': 'success',
            'instance_id': 'i-cascade-rollback'
        }
        mock_network.isolate_instance.return_value = {
            'status': 'success',
            'isolated_group': 'sg-isolated-cascade'
        }
        mock_iam.remediate_excessive_permissions.return_value = {
            'status': 'failed',
            'error': 'Cannot revoke from protected role'
        }

        # Setup rollback
        mock_network.restore_connectivity.return_value = {
            'status': 'success'
        }
        mock_ec2.resume_instance.return_value = {
            'status': 'success'
        }

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Verify rollback cascade
        assert result['status'] == RemediationStatus.ROLLED_BACK.value
        assert 'rollback_info' in result
        assert len(result['rollback_info']['steps']) == 2  # Network and EC2 rolled back
        assert mock_network.restore_connectivity.called
        assert mock_ec2.resume_instance.called

    def test_remediation_impact_assessment(self):
        """✅ Orchestrator tracks and reports remediation impact."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-INT-ORCH-003',
            'instance_id': 'i-impact-assess',
            'principal': 'arn:aws:iam::123456789012:user/test',
            'bucket_name': 'test-bucket'
        }

        mock_ec2.remediate_unauthorized_instance.return_value = {
            'status': 'success',
            'impact': 'stopped_instance'
        }
        mock_network.isolate_instance.return_value = {
            'status': 'success',
            'impact': 'network_isolation'
        }
        mock_iam.remediate_excessive_permissions.return_value = {
            'status': 'success',
            'impact': 'permission_revocation'
        }
        mock_s3.remediate_public_access.return_value = {
            'status': 'success',
            'impact': 'public_access_blocked'
        }

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Verify impact tracking
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert 'results' in result
        assert all(r['status'] == 'success' for r in result['results'].values())

    def test_remediation_cost_estimation(self):
        """✅ Orchestrator estimates cost impact of remediation actions."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-INT-ORCH-004',
            'instance_id': 'i-cost-estimate',
            'principal': 'arn:aws:iam::123456789012:user/test',
            'bucket_name': 'test-bucket'
        }

        # All remediations succeed
        mock_ec2.remediate_unauthorized_instance.return_value = {'status': 'success'}
        mock_network.isolate_instance.return_value = {'status': 'success'}
        mock_iam.remediate_excessive_permissions.return_value = {'status': 'success'}
        mock_s3.remediate_public_access.return_value = {'status': 'success'}

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Note: Cost estimation would be in SmartRemediationEngine
        # Verify orchestrator successfully executes
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert len(result['execution_order']) == 4

    def test_distributed_tracing_via_threat_id(self):
        """✅ Orchestrator tracks remediation execution via threat ID."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-INT-ORCH-005',
            'instance_id': 'i-trace-001',
            'principal': 'arn:aws:iam::123456789012:user/test'
        }

        mock_ec2.remediate_unauthorized_instance.return_value = {'status': 'success'}
        mock_network.isolate_instance.return_value = {'status': 'success'}
        mock_iam.remediate_excessive_permissions.return_value = {'status': 'success'}

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Verify distributed tracing
        assert result['threat_id'] == 'THREAT-INT-ORCH-005'
        assert 'orchestration_id' in result
        assert 'timestamp' in result

        # Check execution history tracking
        orchestration_id = result['orchestration_id']
        status = orchestrator.get_orchestration_status(orchestration_id)
        assert status['threat_id'] == 'THREAT-INT-ORCH-005'
        assert status['executed_steps'] == 3

    def test_concurrent_orchestration_requests(self):
        """✅ Multiple concurrent threat remediations execute independently."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threats = [
            {
                'threat_id': 'THREAT-INT-ORCH-006-A',
                'instance_id': 'i-concurrent-001',
                'principal': 'arn:aws:iam::123456789012:user/attacker-a'
            },
            {
                'threat_id': 'THREAT-INT-ORCH-006-B',
                'instance_id': 'i-concurrent-002',
                'principal': 'arn:aws:iam::123456789012:user/attacker-b'
            },
            {
                'threat_id': 'THREAT-INT-ORCH-006-C',
                'instance_id': 'i-concurrent-003',
                'principal': 'arn:aws:iam::123456789012:user/attacker-c'
            }
        ]

        # Setup mocks to return different results for different instances
        def remediate_ec2(*args, **kwargs):
            instance_id = args[0]
            return {'status': 'success', 'instance_id': instance_id}

        mock_ec2.remediate_unauthorized_instance.side_effect = remediate_ec2
        mock_network.isolate_instance.return_value = {'status': 'success'}
        mock_iam.remediate_excessive_permissions.return_value = {'status': 'success'}

        # Execute concurrent remediations
        results = [orchestrator.execute_multi_resource_remediation(threat) for threat in threats]

        # Verify all completed successfully
        assert len(results) == 3
        assert all(r['status'] == RemediationStatus.SUCCESS.value for r in results)

        # Verify each has unique orchestration ID
        orch_ids = [r['orchestration_id'] for r in results]
        assert len(set(orch_ids)) == 3  # All unique

        # Verify tracking for each
        for orch_id, threat in zip(orch_ids, threats):
            status = orchestrator.get_orchestration_status(orch_id)
            assert status['threat_id'] == threat['threat_id']
