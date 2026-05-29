"""Sprint 55 Phase 1: Audit Compliance Integration Tests (7 integration tests)"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.services.audit_trail_service import AuditTrailService
from guardian.reports.compliance_report_generator import ComplianceReportGenerator
from guardian.services.audit_dashboard_service import AuditDashboardService
from guardian.validators.policy_compliance_validator import PolicyComplianceValidator


class TestAuditComplianceIntegration:
    """End-to-end audit and compliance integration tests."""

    def test_end_to_end_audit_trail_lifecycle(self):
        """✅ Complete threat → remediation → audit trail."""
        audit = AuditTrailService()

        # Step 1: Log threat detection
        threat_id = audit.log_threat_detection(
            {'threat_id': 'E2E-THREAT-001', 'threat_type': 'Unauthorized Access', 'severity': 8},
            'detector-prod',
            ['failed_auth', 'api_key_exposure']
        )

        # Step 2: Log remediation
        audit.log_remediation_action(
            'E2E-THREAT-001',
            'BLOCK_USER',
            'SUCCESS',
            ['user-suspicious-001']
        )

        # Step 3: Verify audit trail
        trail = audit.get_threat_audit_chain('E2E-THREAT-001')

        assert len(trail) == 2
        assert trail[0]['event_type'] == 'THREAT_DETECTION'
        assert trail[1]['event_type'] == 'REMEDIATION_ACTION'

    def test_threat_audit_chain_accuracy(self):
        """✅ Verify complete audit chain for threat."""
        audit = AuditTrailService()

        # Log multiple events for same threat
        threat_id = 'CHAIN-THREAT-001'

        audit.log_threat_detection(
            {'threat_id': threat_id, 'threat_type': 'Lateral Movement', 'severity': 9},
            'detector-1',
            ['ssh_scan']
        )

        audit.log_policy_enforcement('acct-1', 'DENY_CROSS_ACCOUNT', 'APPLIED')

        audit.log_remediation_action(
            threat_id,
            'ISOLATE_INSTANCE',
            'SUCCESS',
            ['i-compromised']
        )

        # Retrieve chain
        chain = audit.get_threat_audit_chain(threat_id)

        assert len(chain) >= 2
        assert chain[0]['threat_id'] == threat_id
        assert any(e['event_type'] == 'THREAT_DETECTION' for e in chain)
        assert any(e['event_type'] == 'REMEDIATION_ACTION' for e in chain)

    def test_compliance_report_generation_soc2(self):
        """✅ Generate and validate SOC 2 report."""
        audit = AuditTrailService()
        generator = ComplianceReportGenerator(audit_service=audit)

        # Create audit events
        for i in range(5):
            audit.log_threat_detection(
                {'threat_id': f'T-{i:03d}', 'threat_type': 'Unauthorized Access', 'severity': 7},
                f'detector-{i}',
                ['evidence']
            )
            audit.log_remediation_action(
                f'T-{i:03d}',
                'BLOCK_ACCESS',
                'SUCCESS',
                [f'user-{i}']
            )

        # Generate SOC2 report
        report = generator.generate_soc2_report(period_days=30)

        assert report['report_type'] == 'SOC2_TYPE_II'
        assert report['metrics']['threat_count'] == 5
        assert report['metrics']['remediation_actions'] == 5
        assert report['metrics']['successful_remediations'] == 5
        assert report['metrics']['compliance_status'] in ['COMPLIANT', 'NON_COMPLIANT']

    def test_compliance_metrics_real_time_update(self):
        """✅ Real-time compliance metric updates."""
        audit = AuditTrailService()
        generator = ComplianceReportGenerator(audit_service=audit)
        dashboard = AuditDashboardService(audit_service=audit, report_generator=generator)

        # Initial report
        report1 = generator.generate_soc2_report()
        metrics1 = dashboard.get_compliance_metrics(framework='SOC2')

        assert metrics1['compliance_score'] >= 0

        # Log new events
        audit.log_threat_detection(
            {'threat_id': 'NEW-THREAT', 'threat_type': 'Data Exfiltration', 'severity': 10},
            'detector-new',
            ['s3_export']
        )

        # Get updated metrics
        metrics2 = dashboard.get_compliance_metrics(framework='SOC2')

        assert 'last_updated' in metrics2
        assert metrics2['framework'] == 'SOC2'

    def test_policy_violation_detection_and_logging(self):
        """✅ Detect and log policy violations."""
        audit = AuditTrailService()

        # Log policy violation
        audit.log_policy_enforcement(
            'prod-acct-001',
            'CIS-S3-PublicAccess',
            'VIOLATION'
        )

        # Log policy compliance
        audit.log_policy_enforcement(
            'prod-acct-001',
            'CIS-EC2-Security',
            'COMPLIANT'
        )

        # Query and verify
        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        start_time = end_time - timedelta(hours=1)
        events = audit.get_audit_trail(start_time.isoformat(), end_time.isoformat())

        policy_events = [e for e in events if e['event_type'] == 'POLICY_ENFORCEMENT']
        violations = [e for e in policy_events if e['decision'] == 'VIOLATION']

        assert len(violations) >= 1
        assert violations[0]['policy_name'] == 'CIS-S3-PublicAccess'

    def test_audit_timeline_visualization_data(self):
        """✅ Generate audit timeline for UI visualization."""
        audit = AuditTrailService()

        threat_id = 'TIMELINE-THREAT-001'

        # Create threat lifecycle
        audit.log_threat_detection(
            {'threat_id': threat_id, 'threat_type': 'Reconnaissance', 'severity': 3},
            'detector-1',
            ['port_scan']
        )

        audit.log_remediation_action(threat_id, 'MONITOR', 'SUCCESS', ['monitoring-enabled'])

        # Get timeline
        timeline = audit.get_threat_timeline(threat_id)

        assert timeline['threat_id'] == threat_id
        assert timeline['total_events'] == 2
        assert 'THREAT_DETECTION' in timeline['event_types']
        assert 'REMEDIATION_ACTION' in timeline['event_types']

    def test_multi_account_audit_aggregation(self):
        """✅ Aggregate audit trails across accounts."""
        audit = AuditTrailService()

        # Log events across multiple accounts
        accounts = ['acct-prod-1', 'acct-dev-1', 'acct-staging-1']

        for account in accounts:
            audit.log_threat_detection(
                {
                    'threat_id': f'THREAT-{account}',
                    'threat_type': 'Unauthorized Access',
                    'severity': 7,
                    'account_id': account
                },
                f'detector-{account}',
                ['evidence']
            )

        # Query all events
        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        start_time = end_time - timedelta(hours=1)
        events = audit.get_audit_trail(start_time.isoformat(), end_time.isoformat())

        threat_events = [e for e in events if e['event_type'] == 'THREAT_DETECTION']
        unique_accounts = set(e['account_id'] for e in threat_events)

        assert len(threat_events) == 3
        assert len(unique_accounts) == 3
        assert all(account in unique_accounts for account in accounts)
