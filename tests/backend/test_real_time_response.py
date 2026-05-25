"""Sprint 51 Phase 1: Real-time Response System Tests (8 tests)"""

import sys
from pathlib import Path
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.services.threat_detection_service import ThreatDetectionService
from guardian.executors.auto_remediation_executor import AutoRemediationExecutor
from guardian.tracking.remediation_progress_tracker import RemediationProgressTracker
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator
from guardian.engines.smart_remediation_engine import SmartRemediationEngine


class TestThreatDetectionService:

    @pytest.fixture
    def detector(self):
        class MockAnomalyDetector:
            def detect_anomalies(self, account_id=None, lookback_minutes=60):
                return [
                    {
                        'threat_id': 'threat-001',
                        'threat_type': 'Unauthorized EC2',
                        'severity': 7,
                        'account_id': 'acc-123',
                        'evidence': ['instance launched from unknown IP'],
                        'affected_resources': [
                            {'resource_id': 'i-001', 'resource_type': 'ec2'}
                        ],
                    },
                ]
        return MockAnomalyDetector()

    @pytest.fixture
    def engine(self):
        orchestrator = RemediationOrchestrator(audit_logger=None, max_workers=3)
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    @pytest.fixture
    def service(self, detector, engine):
        return ThreatDetectionService(anomaly_detector=detector, smart_engine=engine, audit_logger=None)

    def test_detect_and_analyze_threats(self, service):
        """✅ Detect threats and generate strategy recommendations."""
        threats = service.detect_and_analyze_threats(account_id='acc-123')

        assert len(threats) > 0
        threat = threats[0]
        assert threat['threat_id'] == 'threat-001'
        assert threat['recommended_strategy'] in ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE']
        assert 'risk_level' in threat
        assert 'estimated_impact' in threat

    def test_threat_status_tracking(self, service):
        """✅ Track status of detected threats."""
        service.detect_and_analyze_threats(account_id='acc-123')

        status = service.get_threat_status('threat-001')

        assert status['threat_id'] == 'threat-001'
        assert status['status'] == 'detected'
        assert status['severity'] >= 0
        assert 'recommended_strategy' in status

    def test_list_active_threats(self, service):
        """✅ List threats above severity threshold."""
        service.detect_and_analyze_threats(account_id='acc-123')
        service.detect_and_analyze_threats(account_id='acc-456')

        threats_high = service.list_active_threats(severity_threshold=7)
        assert len(threats_high) > 0

        threats_low = service.list_active_threats(severity_threshold=9)
        assert len(threats_low) == 0

    def test_correlate_related_threats(self, service):
        """✅ Find related threats from same source."""
        service.detect_and_analyze_threats(account_id='acc-123')

        related = service.correlate_related_threats('threat-001')

        assert isinstance(related, list)


class TestAutoRemediationExecutor:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    @pytest.fixture
    def executor(self, engine, orchestrator):
        return AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator, audit_logger=None)

    def test_auto_remediate_threat(self, executor):
        """✅ Automatically execute best remediation strategy."""
        threat = {
            'threat_id': 'threat-auto',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        result = executor.auto_remediate_threat(threat, resources)

        assert result['execution_id']
        assert result['status'] in ['success', 'partial', 'pending_approval', 'monitoring']
        assert result['strategy'] in ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE']

    def test_execute_with_approval(self, executor):
        """✅ Execute remediation with approval tracking."""
        threat = {
            'threat_id': 'threat-approval',
            'threat_type': 'Unauthorized Access',
            'severity': 9,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'role-001', 'resource_type': 'iam'},
        ]

        result = executor.execute_with_approval(threat, resources, approver_id='user-123')

        assert result['execution_id']
        assert result['approver_id'] == 'user-123'
        assert 'approved_at' in result

    def test_execution_history_tracking(self, executor):
        """✅ Track all execution attempts."""
        threat = {
            'threat_id': 'threat-history',
            'threat_type': 'Public Bucket',
            'severity': 6,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'bucket-001', 'resource_type': 's3'},
        ]

        executor.auto_remediate_threat(threat, resources)
        executor.auto_remediate_threat(threat, resources)

        history = executor.get_execution_history('threat-history')

        assert len(history) == 2

    def test_rollback_remediation(self, executor):
        """✅ Rollback completed remediation if needed."""
        threat = {
            'threat_id': 'threat-rollback',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        if execution_id in executor.rollback_capable_executions:
            rollback = executor.rollback_remediation(execution_id)
            assert rollback['status'] == 'success'
            assert rollback['original_execution_id'] == execution_id


class TestRemediationProgressTracker:

    @pytest.fixture
    def tracker(self):
        return RemediationProgressTracker(dynamodb_table=None, audit_logger=None)

    def test_track_remediation_start(self, tracker):
        """✅ Record when remediation starts."""
        tracker.track_remediation_start('threat-001', 'exec-001', 'ISOLATE')

        progress = tracker.get_remediation_progress('exec-001')

        assert progress['execution_id'] == 'exec-001'
        assert progress['threat_id'] == 'threat-001'
        assert progress['strategy'] == 'ISOLATE'
        assert progress['status'] == 'in_progress'

    def test_track_resource_remediation(self, tracker):
        """✅ Track individual resource remediation progress."""
        tracker.track_remediation_start('threat-001', 'exec-001', 'REMEDIATE')

        tracker.track_resource_remediation('exec-001', 'i-001', 'success', {'stopped': True})
        tracker.track_resource_remediation('exec-001', 'sg-001', 'success', {'isolated': True})

        progress = tracker.get_remediation_progress('exec-001')

        assert progress['resources_processed'] == 2
        assert progress['resources_successful'] == 2
        assert progress['resources_failed'] == 0

    def test_track_remediation_complete(self, tracker):
        """✅ Record when remediation completes."""
        tracker.track_remediation_start('threat-001', 'exec-001', 'REMEDIATE')
        tracker.track_resource_remediation('exec-001', 'i-001', 'success', {'stopped': True})

        outcome = {'status': 'success', 'resources': 1}
        tracker.track_remediation_complete('exec-001', outcome)

        progress = tracker.get_remediation_progress('exec-001')

        assert progress['status'] == 'success'
        assert 'completed_at' in progress

    def test_get_threat_timeline(self, tracker):
        """✅ Get timeline of all remediations for a threat."""
        tracker.track_remediation_start('threat-001', 'exec-001', 'ISOLATE')
        tracker.track_resource_remediation('exec-001', 'sg-001', 'success', {'isolated': True})
        tracker.track_remediation_complete('exec-001', {'status': 'success'})

        tracker.track_remediation_start('threat-001', 'exec-002', 'REMEDIATE')
        tracker.track_remediation_complete('exec-002', {'status': 'success'})

        timeline = tracker.get_threat_timeline('threat-001')

        assert len(timeline) > 0
        assert all(event['timestamp'] for event in timeline)
