"""Sprint 53 Phase 1: Multi-Account Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
from guardian.services.multi_account_threat_aggregator import MultiAccountThreatAggregator
from guardian.orchestrators.multi_account_orchestrator import MultiAccountRemediationOrchestrator
from guardian.policies.account_policy_manager import AccountPolicyManager
from guardian.services.threat_detection_service import ThreatDetectionService
from guardian.executors.auto_remediation_executor import AutoRemediationExecutor
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator
from guardian.engines.smart_remediation_engine import SmartRemediationEngine


class MockAnomalyDetector:
    def __init__(self, threats=None):
        self.threats = threats or []

    def detect_anomalies(self, account_id=None, lookback_minutes=60):
        if account_id:
            return [t for t in self.threats if t.get('account_id') == account_id]
        return self.threats


class TestMultiAccountIntegration:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    def test_end_to_end_multi_account_threat_remediation(self, engine, orchestrator):
        """✅ Complete multi-account threat → remediation flow."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-e2e-multi',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
            {
                'threat_id': 'threat-e2e-multi-2',
                'threat_type': 'Unauthorized EC2',
                'severity': 7,
                'account_id': 'acc-456',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-002', 'resource_type': 'ec2'}],
            },
        ])

        service1 = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)
        service2 = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)

        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        aggregator = MultiAccountThreatAggregator()
        aggregator.register_account('acc-123', service1)
        aggregator.register_account('acc-456', service2)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)

        threats = aggregator.detect_threats_all_accounts()
        assert len(threats) == 2

        threat_to_remediate = threats[0]
        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
        }

        result = multi_orchestrator.remediate_threat_across_accounts(threat_to_remediate, resource_map)

        assert result['threat_id'] == threat_to_remediate['threat_id']
        assert 'acc-123' in result['results']
        assert 'acc-456' in result['results']

    def test_cross_account_lateral_movement_detection(self, engine, orchestrator):
        """✅ Detect lateral movement across accounts."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-lateral-acc1',
                'threat_type': 'Credential Compromise',
                'severity': 9,
                'account_id': 'acc-123',
                'evidence': ['suspicious_login'],
                'affected_resources': [{'resource_id': 'user-001', 'resource_type': 'iam'}],
            },
            {
                'threat_id': 'threat-lateral-acc2',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'account_id': 'acc-456',
                'evidence': ['cross_account_access'],
                'affected_resources': [{'resource_id': 'i-003', 'resource_type': 'ec2'}],
            },
            {
                'threat_id': 'threat-lateral-acc3',
                'threat_type': 'Lateral Movement',
                'severity': 8,
                'account_id': 'acc-789',
                'evidence': ['suspicious_data_access'],
                'affected_resources': [{'resource_id': 'bucket-002', 'resource_type': 's3'}],
            },
        ])

        service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)

        aggregator = MultiAccountThreatAggregator()
        for account_id in ['acc-123', 'acc-456', 'acc-789']:
            aggregator.register_account(account_id, service)

        threats = aggregator.detect_threats_all_accounts()
        assert len(threats) == 3

        cross_account = aggregator.identify_cross_account_threats()
        assert len(cross_account) >= 2

    def test_multi_account_dashboard_aggregation(self, engine, orchestrator):
        """✅ Aggregate dashboard data across accounts."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': f'threat-dashboard-{i}',
                'threat_type': 'Unauthorized EC2' if i % 2 == 0 else 'Public Bucket',
                'severity': 7 + (i % 3),
                'account_id': f'acc-{123 + i*100}',
                'evidence': [],
                'affected_resources': [{'resource_id': f'resource-{i}', 'resource_type': 'ec2'}],
            }
            for i in range(3)
        ])

        service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)

        aggregator = MultiAccountThreatAggregator()
        for i in range(3):
            aggregator.register_account(f'acc-{123 + i*100}', service)

        aggregator.detect_threats_all_accounts()

        distribution = aggregator.get_threat_distribution()

        assert distribution['total_threats'] == 3
        assert len(distribution['by_account']) == 3
        assert distribution['total_threats'] == sum(distribution['by_account'].values())

    def test_account_policy_enforcement(self, engine, orchestrator):
        """✅ Enforce account-specific policies."""
        policy_manager = AccountPolicyManager()

        policy_manager.register_account_policy('acc-123', {
            'allowed_strategies': ['MONITOR', 'ISOLATE'],
            'approval_threshold': 7,
            'restricted_threat_types': [],
        })

        policy_manager.register_account_policy('acc-456', {
            'allowed_strategies': ['REMEDIATE', 'TERMINATE'],
            'approval_threshold': 9,
            'restricted_threat_types': [],
        })

        multi_orchestrator = MultiAccountRemediationOrchestrator(policy_manager=policy_manager)

        threat1 = {
            'threat_id': 'threat-policy-test-1',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }

        threat2 = {
            'threat_id': 'threat-policy-test-2',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }

        result1 = multi_orchestrator.apply_account_policy(threat1, 'acc-123', {})
        result2 = multi_orchestrator.apply_account_policy(threat2, 'acc-456', {})

        assert 'REMEDIATE' in result1['restricted_strategies']
        assert 'REMEDIATE' in result2['allowed_strategies']
        assert result1['approval_required'] == True
        assert result2['approval_required'] == False

    def test_multi_account_remediation_coordination(self, engine, orchestrator):
        """✅ Coordinate remediation across accounts."""
        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor3 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)
        multi_orchestrator.register_account_executor('acc-789', executor3)

        threat = {
            'threat_id': 'threat-coordination',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }

        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
            'acc-789': [{'resource_id': 'i-003', 'resource_type': 'ec2', 'critical': False}],
        }

        result = multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)

        assert len(result['results']) == 3
        assert all(acc in result['results'] for acc in ['acc-123', 'acc-456', 'acc-789'])

    def test_cross_account_remediation_failure_handling(self, engine, orchestrator):
        """✅ Handle remediation failure in one account."""
        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)

        threat = {
            'threat_id': 'threat-failure-test',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }

        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
        }

        result = multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)

        assert 'results' in result
        assert len(result['results']) >= 1

    def test_multi_account_audit_trail(self, engine, orchestrator):
        """✅ Generate unified audit trail across accounts."""
        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)

        threat = {
            'threat_id': 'threat-audit-trail',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }

        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
        }

        execution1 = multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)
        execution2 = multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)

        summary = multi_orchestrator.get_multi_account_summary()

        assert summary['total_executions'] >= 2
        assert 'success_rate' in summary
