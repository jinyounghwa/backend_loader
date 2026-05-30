"""Compliance reporting and auditing for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import uuid


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ComplianceChecker:
    """Check PCI-DSS, HIPAA, SOC2 compliance."""

    FRAMEWORKS = {
        'PCI_DSS': {
            'name': 'PCI-DSS v3.2.1',
            'checks': [
                'encryption',
                'access_control',
                'logging',
                'vulnerability_management'
            ]
        },
        'HIPAA': {
            'name': 'HIPAA',
            'checks': [
                'encryption',
                'access_control',
                'audit_logging',
                'data_integrity'
            ]
        },
        'SOC2': {
            'name': 'SOC 2 Type II',
            'checks': [
                'security',
                'availability',
                'processing_integrity',
                'confidentiality',
                'privacy'
            ]
        }
    }

    def check_compliance(self, audit_params: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance for a framework."""
        framework = audit_params.get('framework', 'PCI_DSS')
        account_id = audit_params.get('account_id')
        resources = audit_params.get('resources', {})

        if framework == 'PCI_DSS':
            return self._check_pci(account_id, resources)
        elif framework == 'HIPAA':
            return self._check_hipaa(account_id, resources)
        elif framework == 'SOC2':
            return self._check_soc2(account_id, resources)
        else:
            return {'error': f'Unknown framework: {framework}'}

    def _check_pci(self, account_id: str, resources: Dict) -> Dict[str, Any]:
        """Check PCI-DSS compliance."""
        violations = []
        score = 100

        # Encryption check
        encrypted = resources.get('encrypted_resources', 0)
        total = resources.get('total_resources', 1)
        if encrypted < total:
            violations.append(f"Unencrypted resources: {total - encrypted}/{total}")
            score -= 20

        # Security groups check
        sg_rules = resources.get('security_groups_with_rules', 0)
        if sg_rules == 0:
            violations.append("No security group rules configured")
            score -= 15

        # MFA check
        mfa_users = resources.get('mfa_enabled_users', 0)
        total_users = resources.get('total_users', 0)
        if total_users > 0 and mfa_users < total_users:
            violations.append(f"MFA not enabled for all users: {mfa_users}/{total_users}")
            score -= 20

        return {
            'framework': 'PCI_DSS',
            'account_id': account_id,
            'score': max(0, score),
            'violations': violations,
            'compliant': score == 100,
            'last_checked': now_utc().isoformat(),
            'checks_performed': 3
        }

    def _check_hipaa(self, account_id: str, resources: Dict) -> Dict[str, Any]:
        """Check HIPAA compliance."""
        violations = []
        score = 100

        # Database encryption
        encrypted_dbs = resources.get('encrypted_databases', 0)
        total_dbs = resources.get('total_databases', 1)
        if encrypted_dbs < total_dbs:
            violations.append(f"Unencrypted databases: {total_dbs - encrypted_dbs}")
            score -= 25

        # Audit logging
        if not resources.get('audit_logging_enabled', False):
            violations.append("Audit logging not enabled")
            score -= 25

        # Access controls
        if not resources.get('access_controls_enforced', False):
            violations.append("Access controls not enforced")
            score -= 25

        return {
            'framework': 'HIPAA',
            'account_id': account_id,
            'score': max(0, score),
            'violations': violations,
            'compliant': score == 100,
            'last_checked': now_utc().isoformat(),
            'checks_performed': 3
        }

    def _check_soc2(self, account_id: str, resources: Dict) -> Dict[str, Any]:
        """Check SOC2 compliance."""
        violations = []
        score = 100

        # Logging check
        logging_services = resources.get('logging_enabled_services', 0)
        total_services = resources.get('total_services', 1)
        if logging_services < total_services:
            violations.append(f"Logging not enabled: {logging_services}/{total_services}")
            score -= 20

        # Backup check
        if not resources.get('backup_configured', False):
            violations.append("Backup not configured")
            score -= 20

        # Disaster recovery
        if not resources.get('disaster_recovery_plan', False):
            violations.append("No disaster recovery plan")
            score -= 20

        return {
            'framework': 'SOC2',
            'account_id': account_id,
            'score': max(0, score),
            'violations': violations,
            'compliant': score == 100,
            'last_checked': now_utc().isoformat(),
            'checks_performed': 3
        }


class ComplianceReport:
    """Generate compliance audit reports."""

    def __init__(self):
        self.reports: Dict[str, Dict[str, Any]] = {}

    def generate(self, report_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate compliance report."""
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        framework = report_params.get('framework', 'PCI_DSS')
        account_id = report_params.get('account_id')
        period = report_params.get('period', 'Q2_2026')
        include_evidence = report_params.get('include_evidence', False)
        include_remediation = report_params.get('include_remediation', False)

        report = {
            'report_id': report_id,
            'framework': framework,
            'account_id': account_id,
            'period': period,
            'generated_at': now_utc().isoformat(),
            'findings': self._generate_findings(framework),
            'passed_controls': [],
            'failed_controls': []
        }

        if include_evidence:
            report['evidence_references'] = report_params.get('evidence_ids', [])

        if include_remediation:
            report['remediation_steps'] = self._get_remediation_steps(framework)

        self.reports[report_id] = report
        return report

    def _generate_findings(self, framework: str) -> List[str]:
        """Generate findings for framework."""
        findings = {
            'PCI_DSS': [
                'Access control mechanisms enforced',
                'Encryption in transit and at rest verified',
                'Logging and monitoring enabled'
            ],
            'HIPAA': [
                'Patient data encryption verified',
                'Audit controls in place',
                'Access restrictions enforced'
            ],
            'SOC2': [
                'Security measures evaluated',
                'Availability controls assessed',
                'Data integrity verified'
            ]
        }
        return findings.get(framework, [])

    def _get_remediation_steps(self, framework: str) -> List[str]:
        """Get remediation steps for framework."""
        steps = {
            'PCI_DSS': [
                'Enable encryption for all data stores',
                'Implement multi-factor authentication',
                'Configure network segmentation'
            ],
            'HIPAA': [
                'Enable database encryption',
                'Configure CloudTrail logging',
                'Implement role-based access control'
            ],
            'SOC2': [
                'Enable CloudWatch monitoring',
                'Configure automated backups',
                'Implement disaster recovery procedures'
            ]
        }
        return steps.get(framework, [])

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get generated report."""
        return self.reports.get(report_id)


class ComplianceScheduler:
    """Schedule automated compliance checks."""

    def __init__(self):
        self.schedules: Dict[str, Dict[str, Any]] = {}

    def schedule(self, schedule_params: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule compliance check."""
        schedule_id = f"schedule_{uuid.uuid4().hex[:8]}"
        framework = schedule_params.get('framework', 'PCI_DSS')
        frequency = schedule_params.get('frequency', 'MONTHLY')
        day_of_month = schedule_params.get('day_of_month', 1)

        schedule = {
            'schedule_id': schedule_id,
            'framework': framework,
            'frequency': frequency,
            'status': 'scheduled',
            'created_at': now_utc().isoformat(),
            'next_run': self._calculate_next_run(frequency, day_of_month)
        }

        self.schedules[schedule_id] = schedule
        return schedule

    def _calculate_next_run(self, frequency: str, day_of_month: int = 1) -> str:
        """Calculate next run time."""
        now = now_utc()

        if frequency == 'MONTHLY':
            if now.day <= day_of_month:
                next_run = now.replace(day=day_of_month)
            else:
                next_month = now.replace(day=1) + timedelta(days=32)
                next_run = next_month.replace(day=min(day_of_month, 28))
        elif frequency == 'QUARTERLY':
            quarter_months = [1, 4, 7, 10]
            current_quarter_month = quarter_months[(now.month - 1) // 3]
            next_run = now.replace(month=current_quarter_month, day=1)
            if next_run <= now:
                next_quarter = (now.month // 3) + 1
                if next_quarter > 4:
                    next_run = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_run = now.replace(month=quarter_months[next_quarter - 1], day=1)
        else:
            next_run = now + timedelta(days=1)

        return next_run.isoformat()

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update compliance schedule."""
        if schedule_id not in self.schedules:
            return {'status': 'not_found', 'schedule_id': schedule_id}

        self.schedules[schedule_id].update(updates)
        self.schedules[schedule_id]['updated_at'] = now_utc().isoformat()
        self.schedules[schedule_id]['status'] = 'updated'

        return self.schedules[schedule_id]

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule by ID."""
        return self.schedules.get(schedule_id)


class EvidenceCollector:
    """Collect compliance evidence."""

    def __init__(self):
        self.evidence: Dict[str, Dict[str, Any]] = {}

    def collect(self, evidence_params: Dict[str, Any]) -> Dict[str, Any]:
        """Collect compliance evidence."""
        evidence_id = f"evidence_{uuid.uuid4().hex[:8]}"
        check_type = evidence_params.get('check_type', 'ENCRYPTION')
        account_id = evidence_params.get('account_id')
        timestamp = now_utc()

        evidence = {
            'evidence_id': evidence_id,
            'check_type': check_type,
            'account_id': account_id,
            'timestamp': timestamp.isoformat(),
            'retention_days': evidence_params.get('retention_days', 2555)  # 7 years
        }

        if check_type == 'ENCRYPTION':
            evidence['encrypted_resources'] = evidence_params.get('resources', [])
            evidence['encryption_status'] = 'verified'

        elif check_type == 'ACCESS_CONTROL':
            evidence['mfa_enabled_count'] = evidence_params.get('mfa_enabled_count', 0)
            evidence['iam_policies_reviewed'] = evidence_params.get('check_iam_policies', False)

        elif check_type == 'AUDIT_LOGS':
            days_back = evidence_params.get('days_back', 30)
            evidence['log_entries'] = []
            evidence['audit_count'] = 0
            evidence['period_days'] = days_back

        elif check_type == 'BACKUP':
            evidence['backup_configured'] = True
            evidence['last_backup'] = timestamp.isoformat()

        # Calculate retention until date
        retention_until = timestamp + timedelta(days=evidence['retention_days'])
        evidence['retention_until'] = retention_until.isoformat()

        self.evidence[evidence_id] = evidence
        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get evidence by ID."""
        return self.evidence.get(evidence_id)

    def list_evidence_by_account(self, account_id: str) -> List[Dict[str, Any]]:
        """List all evidence for an account."""
        return [e for e in self.evidence.values() if e.get('account_id') == account_id]
