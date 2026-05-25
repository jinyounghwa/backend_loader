"""Sprint 47 Phase 1: Remediation Orchestration Tests (6 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator, RemediationStatus


class TestRemediationOrchestration:
    """Remediation orchestration and multi-resource coordination."""

    def test_orchestrator_executes_multi_resource_remediation(self):
        """✅ Orchestrator executes remediation across EC2, Network, IAM, S3."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-001',
            'instance_id': 'i-orchestrated-001',
            'principal': 'arn:aws:iam::123456789012:user/compromised',
            'bucket_name': 'compromised-bucket',
            'severity': 9
        }

        # Setup mocks
        mock_ec2.remediate_unauthorized_instance.return_value = {
            'status': 'success',
            'instance_id': 'i-orchestrated-001'
        }
        mock_network.isolate_instance.return_value = {
            'status': 'success',
            'new_security_group_id': 'sg-isolated'
        }
        mock_iam.remediate_excessive_permissions.return_value = {
            'status': 'success',
            'policies_revoked': ['AdministratorAccess']
        }
        mock_s3.remediate_public_access.return_value = {
            'status': 'success',
            'bucket_name': 'compromised-bucket'
        }

        result = orchestrator.execute_multi_resource_remediation(threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert 'orchestration_id' in result
        assert len(result['execution_order']) == 4
        assert result['execution_order'] == ['ec2', 'network', 'iam', 's3']
        assert mock_audit.log_orchestration.called

    def test_orchestrator_chains_remediations_in_order(self):
        """✅ Remediations execute in correct dependency order."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-002',
            'instance_id': 'i-order-test',
            'principal': 'arn:aws:iam::123456789012:user/test',
            'bucket_name': 'test-bucket',
            'severity': 8
        }

        # Setup mocks with side effects to track call order
        call_order = []
        mock_ec2.remediate_unauthorized_instance.side_effect = lambda *args, **kwargs: (
            call_order.append('ec2'),
            {'status': 'success'}
        )[1]
        mock_network.isolate_instance.side_effect = lambda *args, **kwargs: (
            call_order.append('network'),
            {'status': 'success'}
        )[1]
        mock_iam.remediate_excessive_permissions.side_effect = lambda *args, **kwargs: (
            call_order.append('iam'),
            {'status': 'success'}
        )[1]
        mock_s3.remediate_public_access.side_effect = lambda *args, **kwargs: (
            call_order.append('s3'),
            {'status': 'success'}
        )[1]

        result = orchestrator.execute_multi_resource_remediation(threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert call_order == ['ec2', 'network', 'iam', 's3']

    def test_orchestrator_rolls_back_all_on_failure(self):
        """✅ If any step fails, all previous steps are rolled back."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-003',
            'instance_id': 'i-rollback-test',
            'principal': 'arn:aws:iam::123456789012:user/test',
            'bucket_name': 'test-bucket'
        }

        # EC2 succeeds, Network succeeds, IAM fails
        mock_ec2.remediate_unauthorized_instance.return_value = {
            'status': 'success'
        }
        mock_network.isolate_instance.return_value = {
            'status': 'success'
        }
        mock_iam.remediate_excessive_permissions.return_value = {
            'status': 'failed',
            'error': 'Permission denied'
        }

        # Rollback mocks
        mock_network.restore_connectivity.return_value = {
            'status': 'success'
        }
        mock_ec2.resume_instance.return_value = {
            'status': 'success'
        }

        result = orchestrator.execute_multi_resource_remediation(threat)

        assert result['status'] == RemediationStatus.ROLLED_BACK.value
        assert 'rollback_info' in result
        assert mock_network.restore_connectivity.called
        assert mock_ec2.resume_instance.called

    def test_orchestrator_correlates_resources_by_threat(self):
        """✅ Orchestrator can find all resources affected by same threat ID."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-004',
            'instance_id': 'i-correlated-001',
            'principal': 'arn:aws:iam::123456789012:user/compromised',
            'bucket_name': 'affected-bucket'
        }

        # Execute remediation first
        mock_ec2.remediate_unauthorized_instance.return_value = {'status': 'success'}
        mock_network.isolate_instance.return_value = {'status': 'success'}
        mock_iam.remediate_excessive_permissions.return_value = {'status': 'success'}
        mock_s3.remediate_public_access.return_value = {'status': 'success'}

        orchestrator.execute_multi_resource_remediation(threat)

        # Now correlate resources
        correlation = orchestrator.correlate_resources_by_threat(threat['threat_id'])

        assert correlation['threat_id'] == 'THREAT-ORCH-004'
        assert correlation['resources']['instances']
        assert correlation['resources']['principals']
        assert correlation['resources']['buckets']

    def test_orchestrator_logs_orchestration_flow(self):
        """✅ All orchestration steps are logged."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-005',
            'instance_id': 'i-logged-orch',
            'principal': 'arn:aws:iam::123456789012:user/test',
            'bucket_name': 'test-bucket'
        }

        mock_ec2.remediate_unauthorized_instance.return_value = {'status': 'success'}
        mock_network.isolate_instance.return_value = {'status': 'success'}
        mock_iam.remediate_excessive_permissions.return_value = {'status': 'success'}
        mock_s3.remediate_public_access.return_value = {'status': 'success'}

        result = orchestrator.execute_multi_resource_remediation(threat)

        assert mock_audit.log_orchestration.called
        call_args = mock_audit.log_orchestration.call_args
        assert call_args[0][0] == result['orchestration_id']

    def test_orchestrator_handles_timeout(self):
        """✅ Orchestrator gracefully handles execution timeout."""
        mock_ec2 = Mock()
        mock_network = Mock()
        mock_iam = Mock()
        mock_s3 = Mock()
        mock_audit = Mock()

        orchestrator = RemediationOrchestrator(mock_ec2, mock_network, mock_iam, mock_s3, mock_audit)

        threat = {
            'threat_id': 'THREAT-ORCH-006',
            'instance_id': 'i-timeout-test',
            'principal': 'arn:aws:iam::123456789012:user/test'
        }

        # Network remediation times out (raises exception)
        mock_ec2.remediate_unauthorized_instance.return_value = {'status': 'success'}
        mock_network.isolate_instance.side_effect = TimeoutError('Network call timeout')

        # Setup rollback
        mock_ec2.resume_instance.return_value = {'status': 'success'}

        result = orchestrator.execute_multi_resource_remediation(threat)

        # Timeout is caught and rollback is attempted
        assert result['status'] in [RemediationStatus.FAILED.value, RemediationStatus.ROLLED_BACK.value]
        assert 'error' in result
        assert 'timeout' in result['error'].lower()
