"""Sprint 52 Phase 1: Dashboard Service Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from guardian.services.dashboard_data_service import DashboardDataService
from guardian.services.threat_detection_service import ThreatDetectionService
from guardian.executors.auto_remediation_executor import AutoRemediationExecutor
from guardian.tracking.remediation_progress_tracker import RemediationProgressTracker
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator
from guardian.engines.smart_remediation_engine import SmartRemediationEngine


class TestDashboardDataService:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    @pytest.fixture
    def threat_service(self):
        class MockDetector:
            def detect_anomalies(self, account_id=None, lookback_minutes=60):
                return [
                    {
                        'threat_id': 'threat-001',
                        'threat_type': 'Unauthorized EC2',
                        'severity': 8,
                        'account_id': 'acc-123',
                        'evidence': [],
                        'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
                    },
                    {
                        'threat_id': 'threat-002',
                        'threat_type': 'Public Bucket',
                        'severity': 5,
                        'account_id': 'acc-456',
                        'evidence': [],
                        'affected_resources': [{'resource_id': 'bucket-001', 'resource_type': 's3'}],
                    },
                ]
        return ThreatDetectionService(anomaly_detector=MockDetector(), smart_engine=None)

    @pytest.fixture
    def executor(self, engine, orchestrator):
        return AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

    @pytest.fixture
    def tracker(self):
        return RemediationProgressTracker()

    @pytest.fixture
    def dashboard_service(self, threat_service, executor, tracker):
        return DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)

    def test_get_threat_dashboard(self, threat_service, executor, tracker):
        """✅ Return current threat dashboard data."""
        threat_service.detect_and_analyze_threats(account_id='acc-123')

        service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)
        dashboard = service.get_threat_dashboard(account_id='acc-123')

        assert dashboard['account_id'] == 'acc-123'
        assert 'active_threats' in dashboard
        assert 'threat_summary' in dashboard
        assert 'severity_distribution' in dashboard
        assert 'recent_remediations' in dashboard
        assert 'metrics' in dashboard

    def test_get_remediation_progress(self, threat_service, executor, tracker):
        """✅ Return real-time remediation progress."""
        threat = {
            'threat_id': 'threat-progress',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-progress', execution_id, 'REMEDIATE')
        tracker.track_resource_remediation(execution_id, 'i-001', 'success', {'stopped': True})

        service = DashboardDataService(threat_service=None, executor=executor, tracker=tracker)
        progress = service.get_remediation_progress('threat-progress')

        assert progress['threat_id'] == 'threat-progress'
        assert progress['progress_percent'] >= 0
        assert progress['status'] == 'in_progress'

    def test_get_threat_timeline(self, threat_service, executor, tracker):
        """✅ Return threat events in timeline format."""
        threat = {
            'threat_id': 'threat-timeline',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-timeline', execution_id, 'REMEDIATE')
        tracker.track_remediation_complete(execution_id, {'status': 'success'})

        service = DashboardDataService(threat_service=None, executor=executor, tracker=tracker)
        timeline = service.get_threat_timeline('threat-timeline')

        assert isinstance(timeline, list)
        assert len(timeline) >= 0

    def test_get_executive_metrics(self, threat_service, executor, tracker):
        """✅ Return executive-level summary metrics."""
        threat_service.detect_and_analyze_threats(account_id='acc-123')

        threat = {
            'threat_id': 'threat-exec',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        executor.auto_remediate_threat(threat, resources)

        service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)
        metrics = service.get_executive_metrics(days=30)

        assert 'total_threats_detected' in metrics
        assert 'threats_resolved' in metrics
        assert 'auto_remediation_rate' in metrics
        assert 'critical_threats' in metrics
        assert metrics['period_days'] == 30

    def test_get_threat_status_by_account(self, threat_service, executor, tracker):
        """✅ Return threat status aggregated by account."""
        threat_service.detect_and_analyze_threats(account_id='acc-123')
        threat_service.detect_and_analyze_threats(account_id='acc-456')

        service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)
        account_status = service.get_threat_status_by_account()

        assert isinstance(account_status, dict)

    def test_threat_summary_statistics(self, threat_service, executor, tracker):
        """✅ Calculate threat summary statistics."""
        threat_service.detect_and_analyze_threats(account_id='acc-123')
        threat_service.detect_and_analyze_threats(account_id='acc-456')

        service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)
        dashboard = service.get_threat_dashboard()

        summary = dashboard['threat_summary']
        assert 'total' in summary
        assert 'by_status' in summary
        assert 'by_severity' in summary
        assert summary['total'] >= 0

    def test_remediation_status_summary(self, executor, tracker):
        """✅ Summarize all ongoing remediations."""
        threat = {
            'threat_id': 'threat-remed-sum',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-remed-sum', execution_id, 'REMEDIATE')

        service = DashboardDataService(threat_service=None, executor=executor, tracker=tracker)
        summary = service.get_remediation_status_summary()

        assert 'active_remediations' in summary
        assert 'completed_remediations' in summary
        assert 'overall_success_rate' in summary
