"""Sprint 55 Phase 1: Audit Trail and Compliance Tests (9 backend tests)"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.services.audit_trail_service import AuditTrailService
from guardian.reports.compliance_report_generator import ComplianceReportGenerator
from guardian.validators.policy_compliance_validator import PolicyComplianceValidator


class TestAuditTrailService:
    """Audit trail logging and event tracking tests."""

    def test_log_threat_detection(self):
        """✅ Log threat detection with evidence."""
        audit = AuditTrailService()

        threat = {
            'threat_id': 'THREAT-AUDIT-001',
            'threat_type': 'Unauthorized Access',
            'severity': 8,
            'account_id': 'prod-acct'
        }

        event_id = audit.log_threat_detection(threat, 'detector-1', ['ssh_scan', 'port_probe'])

        assert event_id is not None
        assert len(audit.events) == 1
        assert audit.events[0]['threat_id'] == 'THREAT-AUDIT-001'
        assert audit.events[0]['event_type'] == 'THREAT_DETECTION'
        assert 'ssh_scan' in audit.events[0]['evidence']

    def test_log_remediation_action(self):
        """✅ Log remediation execution."""
        audit = AuditTrailService()

        event_id = audit.log_remediation_action(
            'THREAT-001',
            'ISOLATE_INSTANCE',
            'SUCCESS',
            ['i-12345', 'i-67890']
        )

        assert event_id is not None
        assert len(audit.events) == 1
        assert audit.events[0]['event_type'] == 'REMEDIATION_ACTION'
        assert audit.events[0]['status'] == 'SUCCESS'
        assert audit.events[0]['resource_count'] == 2

    def test_log_policy_enforcement(self):
        """✅ Log policy enforcement decision."""
        audit = AuditTrailService()

        event_id = audit.log_policy_enforcement(
            'acct-123',
            'CIS-EC2-Security',
            'VIOLATION'
        )

        assert event_id is not None
        assert len(audit.events) == 1
        assert audit.events[0]['event_type'] == 'POLICY_ENFORCEMENT'
        assert audit.events[0]['decision'] == 'VIOLATION'


class TestComplianceReportGenerator:
    """Compliance report generation tests."""

    def test_generate_soc2_report(self):
        """✅ Generate SOC 2 compliance report."""
        audit = AuditTrailService()
        generator = ComplianceReportGenerator(audit_service=audit)

        # Log some events
        audit.log_threat_detection(
            {'threat_id': 'T-001', 'threat_type': 'Lateral Movement', 'severity': 8},
            'detector-1',
            ['evidence']
        )
        audit.log_remediation_action('T-001', 'ISOLATE', 'SUCCESS', ['i-123'])

        report = generator.generate_soc2_report(period_days=30)

        assert report['report_type'] == 'SOC2_TYPE_II'
        assert 'metrics' in report
        assert 'remediation_success_rate' in report['metrics']
        assert report['metrics']['compliance_status'] in ['COMPLIANT', 'NON_COMPLIANT']

    def test_generate_cis_report(self):
        """✅ Generate CIS benchmark report."""
        audit = AuditTrailService()
        generator = ComplianceReportGenerator(audit_service=audit)

        report = generator.generate_cis_report(period_days=30)

        assert report['report_type'] == 'CIS_BENCHMARK'
        assert 'metrics' in report
        assert 'overall_cis_score' in report['metrics']
        assert 0 <= report['metrics']['overall_cis_score'] <= 100

    def test_generate_pci_dss_report(self):
        """✅ Generate PCI-DSS report."""
        audit = AuditTrailService()
        generator = ComplianceReportGenerator(audit_service=audit)

        report = generator.generate_pci_dss_report(period_days=30)

        assert report['report_type'] == 'PCI_DSS'
        assert 'metrics' in report
        assert 'pci_compliance_level' in report['metrics']


class TestPolicyComplianceValidator:
    """Policy compliance validation tests."""

    def test_validate_threat_response(self):
        """✅ Validate remediation compliance."""
        validator = PolicyComplianceValidator()

        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Lateral Movement',
            'severity': 9
        }

        remediation = {
            'action_id': 'REM-001',
            'action': 'ISOLATE',
            'status': 'SUCCESS',
            'resources_affected': ['i-123']
        }

        result = validator.validate_threat_response(threat, remediation)

        assert result['is_compliant'] is not None
        assert 'threat_id' in result
        assert 'violations' in result

    def test_check_response_time_sla(self):
        """✅ Check SLA compliance."""
        validator = PolicyComplianceValidator()

        base_time = datetime.now(timezone.utc).replace(tzinfo=None)
        detection_time = base_time.isoformat()
        remediation_time = (base_time + timedelta(minutes=30)).isoformat()

        result = validator.check_response_time_sla(
            'THREAT-001',
            3600,  # 60-minute SLA in seconds
            detection_time,
            remediation_time
        )

        assert result['sla_met'] is True
        assert result['status'] == 'COMPLIANT'
        assert 'actual_response_seconds' in result

    def test_identify_compliance_gaps(self):
        """✅ Identify compliance gaps."""
        validator = PolicyComplianceValidator()

        result = validator.identify_compliance_gaps(framework='SOC2')

        assert 'identified_gaps' in result
        assert result['gap_count'] >= 0
        assert 'remediation_priority' in result
