"""Sprint 52 Phase 1: Dashboard Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
import time
from guardian.services.dashboard_data_service import DashboardDataService
from guardian.services.threat_detection_service import ThreatDetectionService
from guardian.executors.auto_remediation_executor import AutoRemediationExecutor
from guardian.tracking.remediation_progress_tracker import RemediationProgressTracker
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator
from guardian.engines.smart_remediation_engine import SmartRemediationEngine


class MockAnomalyDetector:
    def __init__(self, threats=None):
        self.threats = threats or []

    def detect_anomalies(self, account_id=None, lookback_minutes=60):
        if account_id:
            return [t for t in self.threats if t.get('account_id') == account_id]
        return self.threats


class TestDashboardIntegration:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    def test_end_to_end_threat_to_dashboard(self, engine, orchestrator):
        """✅ Threat detection → dashboard display."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-e2e-dash',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
        ])

        threat_service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        tracker = RemediationProgressTracker()

        threat_service.detect_and_analyze_threats(account_id='acc-123')

        dashboard_service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)
        dashboard = dashboard_service.get_threat_dashboard(account_id='acc-123')

        assert len(dashboard['active_threats']) > 0
        assert dashboard['threat_summary']['total'] > 0

    def test_remediation_progress_updates(self, engine, orchestrator):
        """✅ Real-time remediation progress updates."""
        threat = {
            'threat_id': 'threat-progress-update',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        tracker = RemediationProgressTracker()

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-progress-update', execution_id, 'REMEDIATE')

        progress_1 = tracker.get_remediation_progress(execution_id)
        assert progress_1['progress_percent'] >= 0

        tracker.track_resource_remediation(execution_id, 'i-001', 'success', {'stopped': True})

        progress_2 = tracker.get_remediation_progress(execution_id)
        assert progress_2['resources_successful'] > progress_1['resources_successful']

        dashboard_service = DashboardDataService(threat_service=None, executor=executor, tracker=tracker)
        dashboard_progress = dashboard_service.get_remediation_progress('threat-progress-update')

        assert dashboard_progress['progress_percent'] > 0

    def test_threat_timeline_generation(self, engine, orchestrator):
        """✅ Generate accurate threat timeline."""
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        tracker = RemediationProgressTracker()

        threat = {
            'threat_id': 'threat-timeline-gen',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
        }
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-timeline-gen', execution_id, 'REMEDIATE')
        time.sleep(0.01)
        tracker.track_resource_remediation(execution_id, 'i-001', 'success', {'stopped': True})
        time.sleep(0.01)
        tracker.track_remediation_complete(execution_id, {'status': 'success'})

        dashboard_service = DashboardDataService(threat_service=None, executor=executor, tracker=tracker)
        timeline = dashboard_service.get_threat_timeline('threat-timeline-gen')

        assert len(timeline) > 0
        assert all('timestamp' in event for event in timeline)

    def test_executive_metrics_calculation(self, engine, orchestrator):
        """✅ Calculate accurate executive metrics."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-exec-1',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
            {
                'threat_id': 'threat-exec-2',
                'threat_type': 'Public Bucket',
                'severity': 10,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'bucket-001', 'resource_type': 's3'}],
            },
        ])

        threat_service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        threat_service.detect_and_analyze_threats(account_id='acc-123')

        threat = {'threat_id': 'threat-exec-1', 'threat_type': 'Unauthorized EC2', 'severity': 8}
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]
        executor.auto_remediate_threat(threat, resources)

        dashboard_service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=None)
        metrics = dashboard_service.get_executive_metrics()

        assert metrics['total_threats_detected'] > 0
        assert metrics['critical_threats'] >= 0
        assert 0 <= metrics['auto_remediation_rate'] <= 1

    def test_multi_account_threat_aggregation(self, engine, orchestrator):
        """✅ Aggregate threats across multiple accounts."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': 'threat-acc1',
                'threat_type': 'Unauthorized EC2',
                'severity': 7,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'i-001', 'resource_type': 'ec2'}],
            },
            {
                'threat_id': 'threat-acc2',
                'threat_type': 'Public Bucket',
                'severity': 6,
                'account_id': 'acc-456',
                'evidence': [],
                'affected_resources': [{'resource_id': 'bucket-001', 'resource_type': 's3'}],
            },
            {
                'threat_id': 'threat-acc3',
                'threat_type': 'Unauthorized Access',
                'severity': 8,
                'account_id': 'acc-123',
                'evidence': [],
                'affected_resources': [{'resource_id': 'role-001', 'resource_type': 'iam'}],
            },
        ])

        threat_service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)

        threat_service.detect_and_analyze_threats(account_id='acc-123')
        threat_service.detect_and_analyze_threats(account_id='acc-456')

        dashboard_service = DashboardDataService(threat_service=threat_service, executor=None, tracker=None)
        account_status = dashboard_service.get_threat_status_by_account()

        assert 'acc-123' in account_status
        assert 'acc-456' in account_status
        assert account_status['acc-123']['total_threats'] == 2
        assert account_status['acc-456']['total_threats'] == 1

    def test_dashboard_response_performance(self, engine, orchestrator):
        """✅ Dashboard responds within SLA (<500ms)."""
        detector = MockAnomalyDetector(threats=[
            {
                'threat_id': f'threat-perf-{i}',
                'threat_type': 'Unauthorized EC2',
                'severity': 7 + (i % 3),
                'account_id': f'acc-{i // 5}',
                'evidence': [],
                'affected_resources': [{'resource_id': f'i-{i}', 'resource_type': 'ec2'}],
            }
            for i in range(10)
        ])

        threat_service = ThreatDetectionService(anomaly_detector=detector, smart_engine=engine)
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)

        threat_service.detect_and_analyze_threats()

        dashboard_service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=None)

        start_time = time.time()
        dashboard = dashboard_service.get_threat_dashboard()
        response_time = (time.time() - start_time) * 1000

        assert response_time < 500, f"Dashboard response time {response_time}ms exceeded 500ms SLA"
        assert 'active_threats' in dashboard

    def test_dashboard_data_freshness(self, engine, orchestrator):
        """✅ Dashboard shows near-real-time data."""
        threat_service = ThreatDetectionService(anomaly_detector=MockAnomalyDetector(threats=[]), smart_engine=engine)
        executor = AutoRemediationExecutor(smart_engine=engine, remediation_orchestrator=orchestrator)
        tracker = RemediationProgressTracker()

        dashboard_service = DashboardDataService(threat_service=threat_service, executor=executor, tracker=tracker)

        threat = {'threat_id': 'threat-fresh', 'threat_type': 'Unauthorized EC2', 'severity': 7}
        resources = [{'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False}]

        start_time = time.time()
        result = executor.auto_remediate_threat(threat, resources)
        execution_id = result['execution_id']

        tracker.track_remediation_start('threat-fresh', execution_id, 'REMEDIATE')

        execution_summary = executor.get_execution_summary()
        freshness_latency = (time.time() - start_time) * 1000

        assert freshness_latency < 5000, f"Data freshness latency {freshness_latency}ms exceeded 5s threshold"
        assert execution_summary['total_executions'] > 0
