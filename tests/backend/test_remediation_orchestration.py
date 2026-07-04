"""Sprint 49 Phase 1: Remediation Orchestration Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator


class TestRemediationOrchestration:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def sample_threat(self):
        return {
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

    @pytest.fixture
    def sample_resources(self):
        return [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
        ]

    def test_execute_multi_resource_remediation(self, orchestrator, sample_threat, sample_resources):
        """✅ Execute remediation across multiple resource types in order."""
        multi_type_resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
        ]
        threat_multi = {
            'threat_id': 'threat-multi',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

        result = orchestrator.execute_multi_resource_remediation(threat_multi, multi_type_resources)

        assert result['threat_id'] == 'threat-multi'
        assert result['total_resources'] == 1
        assert result['successful_remediations'] == 1
        assert result['failed_remediations'] == 0

        chain = result['remediation_chain']
        assert chain[0]['resource_type'] == 'ec2'
        assert chain[0]['status'] == 'success'

    def test_execute_parallel_remediation(self, orchestrator, sample_threat):
        """✅ Execute remediation in parallel for independent resources."""
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-003', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ]
        sample_threat['threat_type'] = 'Unauthorized EC2'

        result = orchestrator.execute_parallel_remediation(sample_threat, resources)

        assert result['total_resources'] == 3
        assert result['successful_remediations'] == 3
        assert result['failed_remediations'] == 0
        assert result['execution_time_seconds'] > 0

    def test_correlate_resources_by_threat(self, orchestrator):
        """✅ Find all resources affected by a threat."""
        threat = {
            'threat_type': 'Unauthorized EC2',
            'account_id': 'acc-123',
        }

        all_resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123'},
            {'resource_id': 'role-001', 'resource_type': 'iam', 'account_id': 'acc-123'},
        ]

        correlated = orchestrator.correlate_resources_by_threat(threat, all_resources)

        assert len(correlated) == 2
        assert all(r['resource_type'] == 'ec2' for r in correlated)

    def test_assess_remediation_impact(self, orchestrator, sample_threat):
        """✅ Predict impact before execution."""
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123'},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123'},
        ]
        threat = {
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

        impact = orchestrator.assess_remediation_impact(threat, resources)

        assert impact['estimated_downtime_minutes'] == 2.0
        assert 'Compute' in impact['affected_services']
        assert impact['customer_impact'] == 'High - remediation recommended'
        assert impact['safe_to_proceed'] is True

    def test_remediation_impact_customer_impact_levels(self, orchestrator):
        """✅ Customer impact levels by severity."""
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123'}]

        threat_medium = {'threat_type': 'Unauthorized EC2', 'severity': 2}
        impact_medium = orchestrator.assess_remediation_impact(threat_medium, resources)
        assert impact_medium['customer_impact'] == 'Medium - consider impact before remediation'

        threat_high = {'threat_type': 'Unauthorized EC2', 'severity': 6}
        impact_high = orchestrator.assess_remediation_impact(threat_high, resources)
        assert impact_high['customer_impact'] == 'High - remediation recommended'

        threat_critical = {'threat_type': 'Unauthorized EC2', 'severity': 9}
        impact_critical = orchestrator.assess_remediation_impact(threat_critical, resources)
        assert impact_critical['customer_impact'] == 'Critical - immediate remediation required'

    def test_estimate_remediation_cost(self, orchestrator):
        """✅ Cost estimation by action type."""
        threat = {
            'threat_id': 'threat-001',
            'severity': 10,
        }

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'compromised': False},
            {'resource_id': 'i-003', 'resource_type': 'ec2', 'compromised': False},
        ]

        cost = orchestrator.estimate_remediation_cost(threat, resources)

        assert cost['estimated_cost_usd'] == 0.15
        assert len(cost['cost_breakdown']) == 3
        assert cost['cost_vs_risk'] == 'Cost justified by high severity threat'

    def test_remediation_orchestration_summary(self, orchestrator, sample_threat):
        """✅ Generate orchestration execution summary."""
        resources_3 = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-003', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ]
        resources_2 = [
            {'resource_id': 'i-004', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-005', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ]

        orchestrator.execute_multi_resource_remediation(sample_threat, resources_3)
        orchestrator.execute_multi_resource_remediation(sample_threat, resources_2)

        summary = orchestrator.get_orchestration_summary()

        assert summary['total_executions'] == 2
        assert summary['total_resources_remediated'] == 5
        assert summary['successful_remediations'] == 5
        assert summary['failed_remediations'] == 0
        assert summary['success_rate'] == 1.0
        assert summary['average_execution_time_seconds'] >= 0

    def test_remediation_resource_correlation_by_threat_type(self, orchestrator):
        """✅ Resource correlation respects threat-type mapping."""
        threat = {
            'threat_type': 'Public Bucket',
            'account_id': 'acc-123',
        }

        all_resources = [
            {'resource_id': 's3-001', 'resource_type': 's3', 'account_id': 'acc-123'},
            {'resource_id': 's3-002', 'resource_type': 's3', 'account_id': 'acc-123'},
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'role-001', 'resource_type': 'iam', 'account_id': 'acc-123'},
        ]

        correlated = orchestrator.correlate_resources_by_threat(threat, all_resources)

        assert len(correlated) == 2
        assert all(r['resource_type'] == 's3' for r in correlated)
