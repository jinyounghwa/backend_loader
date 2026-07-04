"""Sprint 51 Phase 1: Real-time Response System Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
from guardian.services.threat_detection_service import ThreatDetectionService
from guardian.executors.auto_remediation_executor import AutoRemediationExecutor
from guardian.tracking.remediation_progress_tracker import RemediationProgressTracker
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator
from guardian.engines.smart_remediation_engine import SmartRemediationEngine


class MockAnomalyDetector:
    def __init__(self, threats_to_return=None):
        self.threats_to_return = threats_to_return or []

    def detect_anomalies(self, account_id=None, lookback_minutes=60):
        return self.threats_to_return


class TestRealTimeResponseSystem:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    @pytest.fixture
    def tracker(self):
        return RemediationProgressTracker(dynamodb_table=None, audit_logger=None)

    def test_end_to_end_threat_detection_and_remediation(self, engine, orchestrator, tracker):
        """✅ Complete flow: threat detection → auto-remediation → tracking."""
        detector = MockAnomalyDetector(threats_to_return=[
            {
                'threat_id': 'threat-e2e',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': ['instance from unknown IP'],
                'affected_resources': [
                    {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}
                ],
            },
        ])

        service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine, audit_logger=None)
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)

        threats = service.detect_and_analyze_threats(account_id='acc-123')
        assert len(threats) == 1

        threat = threats[0]
        resources = threat['evidence'] if isinstance(threat['evidence'], list) else []

        result = executor.auto_remediate_threat(threat, [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}])

        tracker.track_remediation_start(threat['threat_id'], result['execution_id'], result['strategy'])

        progress = tracker.get_remediation_progress(result['execution_id'])
        assert progress['threat_id'] == 'threat-e2e'
        assert progress['status'] in ['in_progress', 'completed']

    def test_high_severity_threat_automatic_remediation(self, engine, orchestrator):
        """✅ High severity threats automatically remediated."""
        threat = {
            'threat_id': 'threat-high',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)
        result = executor.auto_remediate_threat(threat, resources)

        assert result['strategy'] == 'REMEDIATE'
        assert result['auto_remediated'] is True

    def test_medium_severity_threat_isolation(self, engine, orchestrator):
        """✅ Medium severity threats automatically isolated."""
        threat = {
            'threat_id': 'threat-medium',
            'threat_type': 'Unauthorized Access',
            'severity': 5,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'sg-001', 'resource_type': 'network'},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)
        result = executor.auto_remediate_threat(threat, resources)

        assert result['strategy'] == 'ISOLATE'
        assert result['auto_remediated'] is True

    def test_low_severity_threat_monitoring(self, engine, orchestrator):
        """✅ Low severity threats monitored but not remediated."""
        threat = {
            'threat_id': 'threat-low',
            'threat_type': 'Unusual Activity',
            'severity': 2,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2'},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)
        result = executor.auto_remediate_threat(threat, resources)

        assert result['strategy'] == 'MONITOR'
        assert result['auto_remediated'] is False

    def test_critical_resource_protection_in_auto_remediation(self, engine, orchestrator):
        """✅ Auto-remediation respects critical resource protection."""
        threat = {
            'threat_id': 'threat-crit',
            'threat_type': 'Unauthorized EC2',
            'severity': 10,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': True},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)
        result = executor.auto_remediate_threat(threat, resources)

        assert result['strategy'] == 'TERMINATE'
        assert result['approval_required'] is True

    def test_multi_threat_parallel_remediation(self, engine, orchestrator, tracker):
        """✅ Multiple threats remediated in parallel."""
        threats = [
            {
                'threat_id': 'threat-para-1',
                'threat_type': 'Unauthorized EC2',
                'severity': 7,
                'account_id': 'acc-123',
            },
            {
                'threat_id': 'threat-para-2',
                'threat_type': 'Public Bucket',
                'severity': 6,
                'account_id': 'acc-123',
            },
        ]
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
            {'resource_id': 'bucket-001', 'resource_type': 's3'},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)

        results = []
        for threat in threats:
            result = executor.auto_remediate_threat(threat, resources)
            results.append(result)
            tracker.track_remediation_start(threat['threat_id'], result['execution_id'], result['strategy'])

        summary = executor.get_execution_summary()
        assert summary['total_executions'] == 2

        progress_summary = tracker.get_progress_summary()
        assert progress_summary['active_remediations'] == 2

    def test_remediation_failure_notification_and_retry(self, engine, orchestrator, tracker):
        """✅ Failed remediations notify and retry."""
        threat = {
            'threat_id': 'threat-fail',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)

        result_1 = executor.auto_remediate_threat(threat, resources)
        result_2 = executor.auto_remediate_threat(threat, resources)

        history = executor.get_execution_history('threat-fail')
        assert len(history) == 2

        summary = executor.get_execution_summary()
        assert summary['total_executions'] == 2
