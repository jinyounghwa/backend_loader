"""Sprint 53 Phase 1: Multi-Account Orchestration Tests (8 tests)"""

import sys
from pathlib import Path
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

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


class TestMultiAccountThreatAggregator:

    def test_register_account(self):
        """✅ Register threat service for account."""
        aggregator = MultiAccountThreatAggregator()

        detector = MockAnomalyDetector(threats=[])
        service = ThreatDetectionService(anomaly_detector=detector, smart_engine=None)

        aggregator.register_account('acc-123', service)

        assert 'acc-123' in aggregator.threat_services
        assert aggregator.threat_services['acc-123'] == service

    def test_detect_threats_all_accounts(self):
        """✅ Detect threats across all accounts."""
        detector1 = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-acc1',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
        ])

        detector2 = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-acc2',
                'threat_type': 'Public Bucket',
                'severity': 7,
                'account_id': 'acc-456',
                'evidence': [],
                'affected_resources': [{'resource_id': 'bucket-001', 'resource_type': 's3'}],
            },
        ])

        service1 = ThreatDetectionService(anomaly_detector=detector1, smart_engine=None)
        service2 = ThreatDetectionService(anomaly_detector=detector2, smart_engine=None)

        aggregator = MultiAccountThreatAggregator()
        aggregator.register_account('acc-123', service1)
        aggregator.register_account('acc-456', service2)

        threats = aggregator.detect_threats_all_accounts()

        assert len(threats) == 2
        assert any(t.get('account_id') == 'acc-123' for t in threats)
        assert any(t.get('account_id') == 'acc-456' for t in threats)

    def test_get_threats_by_account(self):
        """✅ Get account-specific threats."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-1',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
            {
                'threat_id': 'threat-2',
                'threat_type': 'Public Bucket',
                'severity': 7,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'bucket-001', 'resource_type': 's3'}],
            },
            {
                'threat_id': 'threat-3',
                'threat_type': 'Unauthorized Access',
                'severity': 6,
                'account_id': 'acc-456',
                'evidence': [],
                'affected_resources': [{'resource_id': 'role-001', 'resource_type': 'iam'}],
            },
        ])

        service = ThreatDetectionService(anomaly_detector=detector, smart_engine=None)
        aggregator = MultiAccountThreatAggregator()
        aggregator.register_account('acc-123', service)
        aggregator.register_account('acc-456', service)

        aggregator.detect_threats_all_accounts()

        acc_123_threats = aggregator.get_threats_by_account('acc-123')

        assert len(acc_123_threats) == 2
        assert all(t.get('account_id') == 'acc-123' for t in acc_123_threats)

    def test_identify_cross_account_threats(self):
        """✅ Identify threats spanning multiple accounts."""
        detector1 = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-lateral-1',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
        ])

        detector2 = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-lateral-2',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'account_id': 'acc-456',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-002', 'resource_type': 'ec2'}],
            },
        ])

        service1 = ThreatDetectionService(anomaly_detector=detector1, smart_engine=None)
        service2 = ThreatDetectionService(anomaly_detector=detector2, smart_engine=None)

        aggregator = MultiAccountThreatAggregator()
        aggregator.register_account('acc-123', service1)
        aggregator.register_account('acc-456', service2)

        aggregator.detect_threats_all_accounts()
        cross_account = aggregator.identify_cross_account_threats()

        assert len(cross_account) == 2
        assert all(t.get('threat_type') == 'Lateral Movement' for t in cross_account)

    def test_remediate_threat_across_accounts(self):
        """✅ Execute remediation across multiple accounts."""
        orchestrator = RemediationOrchestrator(audit_logger=None, max_workers=3)
        engine = SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)

        threat = {
            'threat_id': 'threat-multi-remediate',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }

        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
        }

        result = multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)

        assert result['execution_id']
        assert result['threat_id'] == 'threat-multi-remediate'
        assert 'acc-123' in result['results']
        assert 'acc-456' in result['results']

    def test_apply_account_policy(self):
        """✅ Apply account-specific policy to remediation."""
        policy_manager = AccountPolicyManager()

        policy_manager.register_account_policy('acc-123', {
            'allowed_strategies': ['MONITOR', 'ISOLATE'],
            'approval_threshold': 7,
        })

        multi_orchestrator = MultiAccountRemediationOrchestrator(policy_manager=policy_manager)

        threat = {
            'threat_id': 'threat-policy',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }

        result = multi_orchestrator.apply_account_policy(threat, 'acc-123', {})

        assert result['account_id'] == 'acc-123'
        assert 'REMEDIATE' in result['restricted_strategies']
        assert 'ISOLATE' in result['allowed_strategies']

    def test_coordinate_remediation_sequence(self):
        """✅ Coordinate remediation with dependencies."""
        multi_orchestrator = MultiAccountRemediationOrchestrator()

        threats = [
            {'threat_id': 'threat-1', 'threat_type': 'Type1'},
            {'threat_id': 'threat-2', 'threat_type': 'Type2'},
            {'threat_id': 'threat-3', 'threat_type': 'Type3'},
        ]

        dependency_map = {
            'threat-1': [],
            'threat-2': ['threat-1'],
            'threat-3': ['threat-2'],
        }

        result = multi_orchestrator.coordinate_remediation_sequence(threats, dependency_map)

        assert result['execution_sequence'] == ['threat-1', 'threat-2', 'threat-3']
        assert result['total_threats'] == 3


class TestMultiAccountSummary:

    def test_get_multi_account_summary(self):
        """✅ Get summary of multi-account remediation activity."""
        orchestrator = RemediationOrchestrator(audit_logger=None, max_workers=3)
        engine = SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

        executor1 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        executor2 = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        multi_orchestrator = MultiAccountRemediationOrchestrator()
        multi_orchestrator.register_account_executor('acc-123', executor1)
        multi_orchestrator.register_account_executor('acc-456', executor2)

        threat = {
            'threat_id': 'threat-summary',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }

        resource_map = {
            'acc-123': [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}],
            'acc-456': [{'resource_id': 'i-002', 'resource_type': 'ec2', 'critical': False}],
        }

        multi_orchestrator.remediate_threat_across_accounts(threat, resource_map)

        summary = multi_orchestrator.get_multi_account_summary()

        assert summary['total_executions'] >= 1
        assert 'success_rate' in summary
        assert 0 <= summary['success_rate'] <= 100
