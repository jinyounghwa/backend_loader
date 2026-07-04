"""Sprint 49 Phase 1: Remediation Orchestration Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
import time
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator


class TestRemediationOrchestrationIntegration:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    def test_end_to_end_multi_resource_threat_remediation(self, orchestrator):
        """✅ Complete flow: threat → correlate resources → execute remediation."""
        threat = {
            'threat_id': 'threat-e2e',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'role-001', 'resource_type': 'iam', 'account_id': 'acc-123', 'compromised': False},
        ]

        result = orchestrator.execute_multi_resource_remediation(threat, resources)

        assert result['threat_id'] == 'threat-e2e'
        assert result['total_resources'] == 2
        assert all(item['resource_type'] == 'ec2' for item in result['remediation_chain'])

    def test_remediation_execution_order_dependency(self, orchestrator):
        """✅ Verify execution respects dependency order."""
        threat = {
            'threat_id': 'threat-order',
            'threat_type': 'Network Breach',
            'severity': 7,
            'account_id': 'acc-123',
        }

        resources = [
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'role-001', 'resource_type': 'iam', 'account_id': 'acc-123', 'compromised': False},
        ]

        result = orchestrator.execute_multi_resource_remediation(threat, resources)

        chain = result['remediation_chain']
        assert chain[0]['resource_type'] == 'network'

    def test_parallel_remediation_independent_resources(self, orchestrator):
        """✅ Parallel execution for same resource type."""
        threat = {
            'threat_id': 'threat-parallel',
            'threat_type': 'Unauthorized EC2',
            'severity': 6,
            'account_id': 'acc-123',
        }

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-003', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-004', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-005', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ]

        start = time.time()
        result = orchestrator.execute_parallel_remediation(threat, resources)
        parallel_time = time.time() - start

        assert result['total_resources'] == 5
        assert result['successful_remediations'] == 5

    def test_multi_type_resource_remediation_mixed(self, orchestrator):
        """✅ Handle mixed resource types with proper ordering."""
        threat = {
            'threat_id': 'threat-mixed',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-001', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-002', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'bucket-003', 'resource_type': 's3', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'role-001', 'resource_type': 'iam', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'role-002', 'resource_type': 'iam', 'account_id': 'acc-123', 'compromised': False},
        ]

        result = orchestrator.execute_multi_resource_remediation(threat, resources)

        chain = result['remediation_chain']
        assert all(item['resource_type'] == 'ec2' for item in chain)

    def test_impact_assessment_with_multiple_services(self, orchestrator):
        """✅ Impact assessment aggregates across services."""
        threat = {
            'threat_type': 'Network Breach',
            'severity': 7,
            'account_id': 'acc-123',
        }

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123'},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123'},
            {'resource_id': 'sg-002', 'resource_type': 'network', 'account_id': 'acc-123'},
        ]

        impact = orchestrator.assess_remediation_impact(threat, resources)

        assert impact['estimated_downtime_minutes'] == 3.0
        assert 'Connectivity' in impact['affected_services']

    def test_cost_estimation_multi_resource_scenarios(self, orchestrator):
        """✅ Cost estimation for complex remediation scenarios."""
        low_threat = {'threat_id': 'threat-low', 'severity': 3}
        high_threat = {'threat_id': 'threat-high', 'severity': 10}

        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'compromised': False},
        ]

        cost_low = orchestrator.estimate_remediation_cost(low_threat, resources)
        cost_high = orchestrator.estimate_remediation_cost(high_threat, resources)

        assert cost_low['estimated_cost_usd'] == 0.0
        assert cost_high['estimated_cost_usd'] == 0.10

    def test_orchestration_summary_aggregation(self, orchestrator):
        """✅ Summary correctly aggregates multiple executions."""
        threat = {
            'threat_id': 'threat-summary',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

        orchestrator.execute_multi_resource_remediation(threat, [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-003', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ])

        orchestrator.execute_multi_resource_remediation(threat, [
            {'resource_id': 'i-004', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
            {'resource_id': 'i-005', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ])

        orchestrator.execute_multi_resource_remediation(threat, [
            {'resource_id': 'i-006', 'resource_type': 'ec2', 'account_id': 'acc-123', 'compromised': False},
        ])

        summary = orchestrator.get_orchestration_summary()

        assert summary['total_executions'] == 3
        assert summary['total_resources_remediated'] == 6
        assert summary['successful_remediations'] == 6
        assert summary['failed_remediations'] == 0
        assert summary['success_rate'] == 1.0
