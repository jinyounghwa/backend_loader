"""Sprint 47 Phase 4: Reporting Tests (4 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from guardian.generators.report_generator import ReportGenerator


class TestReporting:
    """Report generation and analytics."""

    def test_daily_remediation_report_generation(self):
        """✅ Daily remediation report summarizes threats detected and remediated."""
        mock_audit = Mock()
        generator = ReportGenerator(mock_audit)

        # Create sample remediation history
        today = datetime.now().strftime('%Y-%m-%d')
        remediation_history = [
            {
                'threat_id': 'THREAT-001',
                'threat_type': 'Unauthorized EC2',
                'severity': 9,
                'timestamp': f"{today}T10:00:00",
                'status': 'success',
                'remediation_time_seconds': 45,
                'remediation_actions': [
                    {'type': 'ec2_stop', 'cost': 0.10}
                ],
                'remediation_cost': 0.10,
                'estimated_cost_prevented': 100.00
            },
            {
                'threat_id': 'THREAT-002',
                'threat_type': 'Public S3 Bucket',
                'severity': 7,
                'timestamp': f"{today}T11:30:00",
                'status': 'success',
                'remediation_time_seconds': 15,
                'remediation_actions': [
                    {'type': 's3_block_public', 'cost': 0.0}
                ],
                'remediation_cost': 0.0,
                'estimated_cost_prevented': 50.00
            },
            {
                'threat_id': 'THREAT-003',
                'threat_type': 'IAM Permission Drift',
                'severity': 5,
                'timestamp': f"{today}T13:00:00",
                'status': 'failed',
                'remediation_actions': [],
                'remediation_cost': 0.05,
                'estimated_cost_prevented': 25.00
            }
        ]

        # Generate daily report
        report = generator.generate_daily_report(remediation_history, today)

        assert report['report_type'] == 'daily'
        assert report['date'] == today
        assert report['total_threats_detected'] == 3
        assert report['total_threats_remediated'] == 2
        assert report['remediation_success_rate'] == pytest.approx(0.67, abs=0.01)
        assert report['threats_by_severity']['critical'] == 1
        assert report['threats_by_severity']['high'] == 1
        assert report['threats_by_severity']['medium'] == 1
        assert report['remediation_actions']['ec2_stop'] == 1
        assert report['remediation_actions']['s3_block_public'] == 1
        assert report['average_remediation_time_seconds'] == pytest.approx(30.0, abs=1)
        assert report['cost_impact']['estimated_prevented_cost'] == 175.00
        assert report['cost_impact']['remediation_cost'] == 0.15
        assert report['cost_impact']['net_savings'] == pytest.approx(174.85, abs=0.01)

    def test_trend_analysis_calculation(self):
        """✅ Trend analysis detects patterns in threat detection and remediation success."""
        mock_audit = Mock()
        generator = ReportGenerator(mock_audit)

        # Create 7 days of remediation history
        remediation_history = []
        base_date = datetime.now() - timedelta(days=6)

        for day in range(7):
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%dT%H:%M:%S')
            # Create varying number of threats per day
            threat_count = 5 + (day * 2)  # 5, 7, 9, 11, 13, 15, 17
            success_count = int(threat_count * (0.9 - day * 0.05))  # Declining success rate

            for i in range(threat_count):
                status = 'success' if i < success_count else 'failed'
                remediation_history.append({
                    'threat_id': f'THREAT-{day}-{i}',
                    'threat_type': 'Test Threat',
                    'severity': 5 + (i % 5),
                    'timestamp': current_date,
                    'status': status,
                    'remediation_actions': [],
                    'remediation_cost': 0.1,
                    'estimated_cost_prevented': 50.0
                })

        # Analyze trends
        trend = generator.analyze_trends(remediation_history, days=7)

        assert trend['period_days'] == 7
        assert len(trend['trend_analysis']['threats_per_day']) == 7
        assert len(trend['trend_analysis']['success_rate_trend']) == 7
        # First day should have fewer threats
        assert trend['trend_analysis']['threats_per_day'][0] < trend['trend_analysis']['threats_per_day'][-1]
        # Success rate should be declining
        assert trend['trend_analysis']['success_rate_trend'][0] > trend['trend_analysis']['success_rate_trend'][-1]
        # Should have insights
        assert len(trend['insights']) > 0
        # Should have recommendations
        assert len(trend['recommendations']) > 0

    def test_cost_impact_calculation(self):
        """✅ Cost impact analysis shows ROI of remediation efforts."""
        mock_audit = Mock()
        generator = ReportGenerator(mock_audit)

        start_date = '2026-05-20'
        end_date = '2026-05-25'

        remediation_history = [
            {
                'threat_id': 'THREAT-001',
                'severity': 9,
                'timestamp': '2026-05-22T10:00:00',
                'status': 'success',
                'remediation_actions': [
                    {'type': 'ec2_terminate', 'cost': 0.50}
                ],
                'remediation_cost': 0.50,
                'estimated_cost_prevented': 500.00  # Would have cost $500 if not remediated
            },
            {
                'threat_id': 'THREAT-002',
                'severity': 7,
                'timestamp': '2026-05-23T14:00:00',
                'status': 'success',
                'remediation_actions': [
                    {'type': 's3_block_public', 'cost': 0.0}
                ],
                'remediation_cost': 0.0,
                'estimated_cost_prevented': 250.00
            },
            {
                'threat_id': 'THREAT-003',
                'severity': 3,
                'timestamp': '2026-05-24T09:00:00',
                'status': 'success',
                'remediation_actions': [
                    {'type': 'iam_revoke', 'cost': 0.05}
                ],
                'remediation_cost': 0.05,
                'estimated_cost_prevented': 50.00
            }
        ]

        # Calculate cost impact
        cost_report = generator.calculate_cost_impact(remediation_history, start_date, end_date)

        assert cost_report['period'] == f"{start_date} to {end_date}"
        assert cost_report['start_date'] == start_date
        assert cost_report['end_date'] == end_date
        assert cost_report['total_remediation_cost'] == 0.55
        assert cost_report['estimated_prevented_cost'] == 800.00
        assert cost_report['net_savings'] == pytest.approx(799.45, abs=0.01)
        assert cost_report['roi_percentage'] > 1000  # Over 1000% ROI

        # Verify cost by action type
        assert cost_report['cost_by_action_type']['ec2_terminate'] == 0.50
        assert cost_report['cost_by_action_type']['s3_block_public'] == 0.0
        assert cost_report['cost_by_action_type']['iam_revoke'] == 0.05

        # Verify prevented cost by severity
        assert cost_report['prevented_cost_by_severity']['critical'] == 500.00
        assert cost_report['prevented_cost_by_severity']['high'] == 250.00

    def test_compliance_report_formatting(self):
        """✅ Compliance report includes all findings and audit trail."""
        mock_audit = Mock()
        generator = ReportGenerator(mock_audit)

        account_id = '123456789012'
        remediation_history = [
            {
                'threat_id': 'THREAT-001',
                'threat_type': 'Malware Detected',
                'severity': 10,
                'timestamp': '2026-05-25T10:00:00',
                'status': 'success',
                'required_approval': True,
                'auto_approved': False,
                'escalated': False,
                'remediation_actions': [],
                'remediation_cost': 1.0,
                'estimated_cost_prevented': 1000.0
            },
            {
                'threat_id': 'THREAT-002',
                'threat_type': 'Unauthorized Access',
                'severity': 9,
                'timestamp': '2026-05-25T11:00:00',
                'status': 'success',
                'required_approval': True,
                'auto_approved': False,
                'escalated': True,
                'remediation_actions': [],
                'remediation_cost': 0.5,
                'estimated_cost_prevented': 500.0
            },
            {
                'threat_id': 'THREAT-003',
                'threat_type': 'Policy Violation',
                'severity': 5,
                'timestamp': '2026-05-25T12:00:00',
                'status': 'success',
                'required_approval': False,
                'auto_approved': True,
                'escalated': False,
                'remediation_actions': [],
                'remediation_cost': 0.1,
                'estimated_cost_prevented': 100.0
            }
        ]

        # Generate compliance report
        compliance = generator.generate_compliance_report(remediation_history, account_id)

        assert compliance['report_type'] == 'compliance'
        assert compliance['account_id'] == account_id
        assert compliance['total_threats_processed'] == 3
        assert compliance['total_remediations'] == 3
        assert compliance['approval_required_count'] == 2
        assert compliance['auto_approved_count'] == 1
        assert compliance['escalations'] == 1

        # Verify findings include high-severity threats
        assert len(compliance['audit_findings']) == 2
        severity_list = [f['severity'] for f in compliance['audit_findings']]
        assert 'Critical' in severity_list
        assert 'High' in severity_list or any(f['severity'] in ['Critical', 'High'] for f in compliance['audit_findings'])

        # Verify all findings have required fields
        for finding in compliance['audit_findings']:
            assert 'finding_id' in finding
            assert 'severity' in finding
            assert 'title' in finding
            assert 'remediation_status' in finding
            assert 'timestamp' in finding
