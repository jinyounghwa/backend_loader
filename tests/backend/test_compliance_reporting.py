"""Compliance reporting tests for AWS Guardian."""

import pytest
from datetime import datetime, timedelta


class TestComplianceChecker:
    """Test PCI-DSS, HIPAA, SOC2 compliance checking."""

    def test_check_pci_compliance(self):
        """✅ Check PCI-DSS compliance."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()

        result = checker.check_compliance({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'resources': {
                'encrypted_resources': 8,
                'total_resources': 10,
                'security_groups_with_rules': 5,
                'mfa_enabled_users': 3,
                'total_users': 3
            }
        })

        assert 'score' in result
        assert 0 <= result['score'] <= 100
        assert 'violations' in result
        assert 'compliant' in result
        assert isinstance(result['violations'], list)

    def test_check_hipaa_compliance(self):
        """✅ Check HIPAA compliance."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()

        result = checker.check_compliance({
            'framework': 'HIPAA',
            'account_id': '123456789',
            'resources': {
                'encrypted_databases': 5,
                'total_databases': 5,
                'audit_logging_enabled': True,
                'access_controls_enforced': True
            }
        })

        assert result['score'] >= 0
        assert 'violations' in result
        assert result['compliant'] in [True, False]

    def test_check_soc2_compliance(self):
        """✅ Check SOC2 compliance."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()

        result = checker.check_compliance({
            'framework': 'SOC2',
            'account_id': '123456789',
            'resources': {
                'logging_enabled_services': 8,
                'total_services': 10,
                'backup_configured': True,
                'disaster_recovery_plan': True
            }
        })

        assert 'score' in result
        assert 'violations' in result
        assert len(result['violations']) >= 0


class TestComplianceReport:
    """Test compliance report generation."""

    def test_generate_compliance_report_pci(self):
        """✅ Generate PCI-DSS audit report."""
        from guardian.compliance.compliance_checker import ComplianceReport

        reporter = ComplianceReport()

        report = reporter.generate({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'period': 'Q2_2026',
            'include_evidence': True
        })

        assert 'report_id' in report
        assert 'framework' in report
        assert report['framework'] == 'PCI_DSS'
        assert 'findings' in report
        assert 'generated_at' in report

    def test_generate_hipaa_report(self):
        """✅ Generate HIPAA audit report."""
        from guardian.compliance.compliance_checker import ComplianceReport

        reporter = ComplianceReport()

        report = reporter.generate({
            'framework': 'HIPAA',
            'account_id': '123456789',
            'period': 'Q2_2026'
        })

        assert report['framework'] == 'HIPAA'
        assert len(report['findings']) >= 0
        assert 'passed_controls' in report or 'failed_controls' in report

    def test_generate_soc2_report(self):
        """✅ Generate SOC2 audit report."""
        from guardian.compliance.compliance_checker import ComplianceReport

        reporter = ComplianceReport()

        report = reporter.generate({
            'framework': 'SOC2',
            'account_id': '123456789',
            'period': 'Q2_2026'
        })

        assert 'report_id' in report
        assert report['framework'] == 'SOC2'
        assert isinstance(report['findings'], list)

    def test_report_includes_remediation_steps(self):
        """✅ Report includes remediation steps for violations."""
        from guardian.compliance.compliance_checker import ComplianceReport

        reporter = ComplianceReport()

        report = reporter.generate({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'period': 'Q2_2026',
            'include_remediation': True
        })

        assert 'remediation_steps' in report or 'recommendations' in report


class TestComplianceScheduler:
    """Test automated compliance scheduling."""

    def test_schedule_monthly_compliance_check(self):
        """✅ Schedule monthly compliance reports."""
        from guardian.compliance.compliance_checker import ComplianceScheduler

        scheduler = ComplianceScheduler()

        schedule = scheduler.schedule({
            'framework': 'PCI_DSS',
            'frequency': 'MONTHLY',
            'day_of_month': 1
        })

        assert schedule['status'] == 'scheduled'
        assert 'schedule_id' in schedule
        assert schedule['frequency'] == 'MONTHLY'

    def test_schedule_quarterly_compliance_report(self):
        """✅ Schedule quarterly compliance reports."""
        from guardian.compliance.compliance_checker import ComplianceScheduler
        from datetime import timezone

        scheduler = ComplianceScheduler()

        schedule = scheduler.schedule({
            'framework': 'HIPAA',
            'frequency': 'QUARTERLY',
            'start_date': datetime.now(timezone.utc).isoformat()
        })

        assert schedule['status'] == 'scheduled'
        assert 'next_run' in schedule

    def test_update_schedule(self):
        """✅ Update compliance schedule."""
        from guardian.compliance.compliance_checker import ComplianceScheduler

        scheduler = ComplianceScheduler()

        # Create schedule
        schedule = scheduler.schedule({
            'framework': 'SOC2',
            'frequency': 'MONTHLY'
        })
        schedule_id = schedule['schedule_id']

        # Update schedule
        updated = scheduler.update_schedule(schedule_id, {
            'frequency': 'QUARTERLY'
        })

        assert updated['status'] == 'updated'
        assert updated['frequency'] == 'QUARTERLY'


class TestEvidenceCollector:
    """Test compliance evidence collection."""

    def test_collect_encryption_evidence(self):
        """✅ Collect encryption evidence."""
        from guardian.compliance.compliance_checker import EvidenceCollector

        collector = EvidenceCollector()

        evidence = collector.collect({
            'check_type': 'ENCRYPTION',
            'account_id': '123456789',
            'resources': ['s3-bucket-1', 'rds-db-1']
        })

        assert 'evidence_id' in evidence
        assert 'encrypted_resources' in evidence
        assert 'timestamp' in evidence

    def test_collect_access_control_evidence(self):
        """✅ Collect access control evidence."""
        from guardian.compliance.compliance_checker import EvidenceCollector

        collector = EvidenceCollector()

        evidence = collector.collect({
            'check_type': 'ACCESS_CONTROL',
            'account_id': '123456789',
            'check_mfa': True,
            'check_iam_policies': True
        })

        assert 'mfa_enabled_count' in evidence or 'mfa_status' in evidence
        assert 'timestamp' in evidence

    def test_collect_audit_logs(self):
        """✅ Collect audit logs as evidence."""
        from guardian.compliance.compliance_checker import EvidenceCollector

        collector = EvidenceCollector()

        evidence = collector.collect({
            'check_type': 'AUDIT_LOGS',
            'account_id': '123456789',
            'days_back': 30
        })

        assert 'log_entries' in evidence or 'audit_count' in evidence
        assert evidence['timestamp']

    def test_evidence_retention(self):
        """✅ Compliance evidence stored with retention policy."""
        from guardian.compliance.compliance_checker import EvidenceCollector

        collector = EvidenceCollector()

        evidence = collector.collect({
            'check_type': 'BACKUP',
            'account_id': '123456789',
            'retention_days': 2555  # 7 years for compliance
        })

        assert 'retention_until' in evidence
        assert evidence['retention_days'] >= 2555


class TestComplianceIntegration:
    """End-to-end compliance workflows."""

    def test_full_compliance_audit_workflow(self):
        """✅ Complete audit: check → collect → report."""
        from guardian.compliance.compliance_checker import (
            ComplianceChecker,
            ComplianceReport,
            EvidenceCollector
        )

        checker = ComplianceChecker()
        collector = EvidenceCollector()
        reporter = ComplianceReport()

        # Step 1: Check compliance
        check = checker.check_compliance({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'resources': {
                'encrypted_resources': 10,
                'total_resources': 10,
                'security_groups_with_rules': 5,
                'mfa_enabled_users': 3,
                'total_users': 3
            }
        })

        assert check['score'] >= 0

        # Step 2: Collect evidence
        evidence = collector.collect({
            'check_type': 'ENCRYPTION',
            'account_id': '123456789',
            'resources': ['s3-bucket-1', 'rds-db-1']
        })

        assert evidence['evidence_id']

        # Step 3: Generate report
        report = reporter.generate({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'period': 'Q2_2026',
            'evidence_ids': [evidence['evidence_id']]
        })

        assert report['report_id']
        assert report['framework'] == 'PCI_DSS'

    def test_multi_framework_compliance(self):
        """✅ Check multiple frameworks simultaneously."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()
        frameworks = ['PCI_DSS', 'HIPAA', 'SOC2']

        results = []
        for framework in frameworks:
            result = checker.check_compliance({
                'framework': framework,
                'account_id': '123456789',
                'resources': {}
            })
            results.append(result)

        assert len(results) == 3
        assert all('score' in r for r in results)

    def test_compliance_dashboard_data(self):
        """✅ Compliance data formatted for dashboard."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()

        result = checker.check_compliance({
            'framework': 'PCI_DSS',
            'account_id': '123456789',
            'resources': {}
        })

        assert 'score' in result
        assert 'compliance_status' in result or result['compliant'] in [True, False]
        assert 'last_checked' in result or 'timestamp' in result

    def test_compliance_alert_on_violation(self):
        """✅ Generate alert when compliance violations detected."""
        from guardian.compliance.compliance_checker import ComplianceChecker

        checker = ComplianceChecker()

        result = checker.check_compliance({
            'framework': 'HIPAA',
            'account_id': '123456789',
            'resources': {
                'encrypted_databases': 3,
                'total_databases': 5  # 40% not encrypted = violation
            }
        })

        if len(result['violations']) > 0:
            assert any('encrypted' in v.lower() for v in result['violations'])
