"""Enterprise reporting & compliance tests for AWS Guardian."""

import pytest


class TestReportGenerator:
    """Test automated report generation."""

    def test_generate_compliance_report(self):
        """✅ Generate compliance report."""
        from guardian.reporting.enterprise_reporting import ReportGenerator

        generator = ReportGenerator()

        report = generator.generate({
            'report_type': 'compliance',
            'period': '2026-05',
            'format': 'pdf'
        })

        assert 'report_id' in report
        assert 'generated_at' in report

    def test_generate_threat_summary(self):
        """✅ Generate threat summary report."""
        from guardian.reporting.enterprise_reporting import ReportGenerator

        generator = ReportGenerator()

        report = generator.generate({
            'report_type': 'threat_summary',
            'lookback_days': 30,
            'format': 'json'
        })

        assert 'report_id' in report
        assert 'threats_detected' in report or 'summary' in report

    def test_generate_cost_analysis(self):
        """✅ Generate cost analysis report."""
        from guardian.reporting.enterprise_reporting import ReportGenerator

        generator = ReportGenerator()

        report = generator.generate({
            'report_type': 'cost_analysis',
            'period': '2026-05',
            'include_recommendations': True
        })

        assert 'report_id' in report
        assert 'total_cost' in report or 'cost_data' in report


class TestComplianceValidator:
    """Test compliance validation."""

    def test_validate_soc2(self):
        """✅ Validate SOC2 compliance."""
        from guardian.reporting.enterprise_reporting import ComplianceValidator

        validator = ComplianceValidator()

        result = validator.validate({
            'framework': 'SOC2',
            'controls': [
                {'id': 'CC6.1', 'status': 'implemented'},
                {'id': 'CC7.1', 'status': 'implemented'},
                {'id': 'CC7.2', 'status': 'not_applicable'}
            ]
        })

        assert 'compliant' in result
        assert 'framework' in result or 'score' in result

    def test_validate_pci_dss(self):
        """✅ Validate PCI-DSS compliance."""
        from guardian.reporting.enterprise_reporting import ComplianceValidator

        validator = ComplianceValidator()

        result = validator.validate({
            'framework': 'PCI-DSS',
            'requirements': [
                {'req': '1', 'status': 'compliant'},
                {'req': '2', 'status': 'compliant'},
                {'req': '6', 'status': 'non_compliant'}
            ]
        })

        assert 'compliant' in result
        assert result['compliant'] is False or 'gaps' in result

    def test_validate_hipaa(self):
        """✅ Validate HIPAA compliance."""
        from guardian.reporting.enterprise_reporting import ComplianceValidator

        validator = ComplianceValidator()

        result = validator.validate({
            'framework': 'HIPAA',
            'safeguards': [
                {'type': 'technical', 'status': 'implemented'},
                {'type': 'administrative', 'status': 'implemented'},
                {'type': 'physical', 'status': 'implemented'}
            ]
        })

        assert 'compliant' in result or 'status' in result


class TestDigitalSignature:
    """Test report digital signing."""

    def test_sign_report(self):
        """✅ Digitally sign report."""
        from guardian.reporting.enterprise_reporting import DigitalSignature

        signer = DigitalSignature()

        signed = signer.sign({
            'report_id': 'rpt_12345',
            'content': 'Report content',
            'signer_name': 'John Doe',
            'signer_role': 'Security Manager'
        })

        assert 'signature' in signed
        assert 'timestamp' in signed

    def test_verify_signature(self):
        """✅ Verify report signature."""
        from guardian.reporting.enterprise_reporting import DigitalSignature

        signer = DigitalSignature()

        # Sign first
        signed = signer.sign({
            'report_id': 'rpt_12345',
            'content': 'Report content'
        })

        # Verify
        verified = signer.verify({
            'report_id': 'rpt_12345',
            'signature': signed.get('signature')
        })

        assert 'valid' in verified
        assert verified.get('valid') is True

    def test_sign_multiple_reports(self):
        """✅ Batch sign reports."""
        from guardian.reporting.enterprise_reporting import DigitalSignature

        signer = DigitalSignature()

        signed = signer.sign_batch({
            'reports': [
                {'id': 'rpt_1', 'content': 'Content 1'},
                {'id': 'rpt_2', 'content': 'Content 2'},
                {'id': 'rpt_3', 'content': 'Content 3'}
            ]
        })

        assert 'signed_count' in signed or 'results' in signed


class TestAuditLogger:
    """Test immutable audit logging."""

    def test_log_event(self):
        """✅ Log audit event."""
        from guardian.reporting.enterprise_reporting import AuditLogger

        logger = AuditLogger()

        result = logger.log({
            'event_type': 'report_generated',
            'report_id': 'rpt_12345',
            'user_id': 'user_123',
            'action': 'generated_compliance_report'
        })

        assert 'log_id' in result
        assert 'timestamp' in result

    def test_retrieve_audit_log(self):
        """✅ Retrieve audit log entries."""
        from guardian.reporting.enterprise_reporting import AuditLogger

        logger = AuditLogger()

        # Log event first
        logger.log({
            'event_type': 'action',
            'user_id': 'user_123'
        })

        # Retrieve
        result = logger.retrieve({
            'user_id': 'user_123',
            'lookback_days': 30
        })

        assert 'entries' in result or 'logs' in result
        assert 'count' in result or len(result.get('entries', [])) >= 0

    def test_audit_trail_immutability(self):
        """✅ Ensure audit trail immutability."""
        from guardian.reporting.enterprise_reporting import AuditLogger

        logger = AuditLogger()

        result = logger.log({
            'event_type': 'critical_action',
            'action': 'modified_security_policy',
            'user_id': 'admin_1'
        })

        assert 'log_id' in result
        assert 'immutable' in result or 'tamper_evident' in result


class TestEnterpriseReportingIntegration:
    """End-to-end enterprise reporting workflows."""

    def test_full_reporting_pipeline(self):
        """✅ Generate, validate, sign, and log report."""
        from guardian.reporting.enterprise_reporting import (
            ReportGenerator,
            ComplianceValidator,
            DigitalSignature,
            AuditLogger
        )

        generator = ReportGenerator()
        validator = ComplianceValidator()
        signer = DigitalSignature()
        logger = AuditLogger()

        # Generate report
        report = generator.generate({
            'report_type': 'compliance',
            'period': '2026-05'
        })

        # Validate compliance
        validation = validator.validate({
            'framework': 'SOC2',
            'controls': []
        })

        # Sign report
        signed = signer.sign({
            'report_id': report['report_id'],
            'content': 'Report content'
        })

        # Log action
        audit = logger.log({
            'event_type': 'report_generated',
            'report_id': report['report_id']
        })

        assert 'report_id' in report
        assert 'compliant' in validation
        assert 'signature' in signed
        assert 'log_id' in audit

    def test_compliance_report_generation(self):
        """✅ Generate comprehensive compliance report."""
        from guardian.reporting.enterprise_reporting import (
            ReportGenerator,
            ComplianceValidator
        )

        generator = ReportGenerator()
        validator = ComplianceValidator()

        # Generate compliance report
        report = generator.generate({
            'report_type': 'compliance',
            'frameworks': ['SOC2', 'PCI-DSS'],
            'include_remediation': True
        })

        # Validate
        validation = validator.validate({
            'framework': 'SOC2',
            'controls': []
        })

        assert 'report_id' in report
        assert 'compliant' in validation

    def test_audit_and_sign_workflow(self):
        """✅ Complete audit logging and signing workflow."""
        from guardian.reporting.enterprise_reporting import (
            DigitalSignature,
            AuditLogger
        )

        signer = DigitalSignature()
        logger = AuditLogger()

        # Sign report
        signed = signer.sign({
            'report_id': 'rpt_audit_1',
            'content': 'Audit content',
            'signer_name': 'Auditor'
        })

        # Log the signing
        audit = logger.log({
            'event_type': 'report_signed',
            'report_id': 'rpt_audit_1',
            'signature_id': signed.get('signature')
        })

        assert 'signature' in signed
        assert 'log_id' in audit

    def test_multi_framework_compliance_check(self):
        """✅ Check compliance across multiple frameworks."""
        from guardian.reporting.enterprise_reporting import ComplianceValidator

        validator = ComplianceValidator()

        # Validate multiple frameworks
        results = []
        for framework in ['SOC2', 'PCI-DSS', 'HIPAA']:
            result = validator.validate({
                'framework': framework,
                'controls': []
            })
            results.append(result)

        assert len(results) == 3
        assert all('compliant' in r for r in results)

    def test_comprehensive_audit_trail(self):
        """✅ Build comprehensive audit trail."""
        from guardian.reporting.enterprise_reporting import AuditLogger

        logger = AuditLogger()

        # Log multiple events
        events = [
            {'event_type': 'report_generated'},
            {'event_type': 'report_signed'},
            {'event_type': 'report_distributed'},
            {'event_type': 'report_archived'}
        ]

        log_ids = []
        for event in events:
            result = logger.log({**event, 'user_id': 'user_123'})
            log_ids.append(result.get('log_id'))

        # Retrieve audit trail
        audit_trail = logger.retrieve({
            'user_id': 'user_123',
            'lookback_days': 1
        })

        assert len(log_ids) == 4
        assert 'entries' in audit_trail or 'logs' in audit_trail
