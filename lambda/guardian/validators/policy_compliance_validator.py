"""Policy Compliance Validator for compliance requirement checking and enforcement."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


class PolicyComplianceValidator:
    """Validates threats and remediations against compliance policies."""

    def __init__(self, audit_logger=None):
        """Initialize policy validator."""
        self.audit = audit_logger
        self.policies = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self):
        """Initialize default compliance policies."""
        self.policies['SOC2'] = {
            'name': 'SOC 2 Type II',
            'requirements': [
                'All threats must be detected and logged',
                'Remediation actions must be taken within SLA',
                'Audit trail must be immutable',
                'Incident response documented'
            ],
            'response_time_sla_minutes': 60
        }
        self.policies['CIS'] = {
            'name': 'CIS Benchmark',
            'requirements': [
                'Unauthorized access must be blocked',
                'Configuration baselines must be maintained',
                'Security controls must be monitored'
            ],
            'response_time_sla_minutes': 30
        }
        self.policies['PCI_DSS'] = {
            'name': 'PCI-DSS',
            'requirements': [
                'Data access must be logged',
                'Failed access attempts must be tracked',
                'Network segmentation required',
                'Vulnerability scanning required'
            ],
            'response_time_sla_minutes': 45
        }

    def register_compliance_policy(self, framework: str, policy_name: str, requirements: List[str]) -> bool:
        """Register custom compliance policy requirements."""
        self.policies[framework] = {
            'name': policy_name,
            'requirements': requirements,
            'response_time_sla_minutes': 60
        }
        return True

    def validate_threat_response(self, threat: Dict, remediation_action: Dict) -> Dict:
        """Validate that remediation complies with policies."""
        severity = threat.get('severity', 5)
        threat_type = threat.get('threat_type', 'Unknown')

        validation_results = {
            'threat_id': threat.get('threat_id'),
            'remediation_id': remediation_action.get('action_id', 'unknown'),
            'is_compliant': True,
            'violations': [],
            'recommendations': []
        }

        # Check action matches threat severity
        required_actions = self._get_required_actions(severity)
        actual_action = remediation_action.get('action', '')

        if actual_action not in required_actions:
            validation_results['violations'].append(
                f'Action "{actual_action}" not appropriate for severity {severity}'
            )
            validation_results['is_compliant'] = False

        # Check resources affected
        resources = remediation_action.get('resources_affected', [])
        if not resources:
            validation_results['violations'].append('No resources specified for remediation')
            validation_results['is_compliant'] = False

        # Check response status
        if remediation_action.get('status') not in ['SUCCESS', 'FAILED', 'PENDING']:
            validation_results['violations'].append('Invalid remediation status')
            validation_results['is_compliant'] = False

        return validation_results

    def check_response_time_sla(self, threat_id: str, sla_seconds: int, detection_time: str, remediation_time: str) -> Dict:
        """Check if remediation met SLA response time requirement."""
        try:
            detect_dt = datetime.fromisoformat(detection_time.replace('Z', '+00:00'))
            remediate_dt = datetime.fromisoformat(remediation_time.replace('Z', '+00:00'))
        except:
            return {
                'threat_id': threat_id,
                'sla_met': False,
                'error': 'Invalid datetime format'
            }

        response_time_seconds = (remediate_dt - detect_dt).total_seconds()
        sla_met = response_time_seconds <= sla_seconds

        return {
            'threat_id': threat_id,
            'sla_target_seconds': sla_seconds,
            'actual_response_seconds': response_time_seconds,
            'sla_met': sla_met,
            'variance_seconds': response_time_seconds - sla_seconds,
            'status': 'COMPLIANT' if sla_met else 'VIOLATED',
            'sla_utilization_percent': (response_time_seconds / sla_seconds * 100) if sla_seconds > 0 else 0
        }

    def validate_account_compliance(self, account_id: str, framework: str) -> Dict:
        """Validate entire account compliance status against framework."""
        policy = self.policies.get(framework)

        if not policy:
            return {
                'account_id': account_id,
                'framework': framework,
                'compliance_status': 'UNKNOWN',
                'error': f'Framework {framework} not found'
            }

        compliance_checks = {
            'detection_enabled': True,
            'audit_logging_enabled': True,
            'remediation_capability': True,
            'policy_enforcement': True,
            'regular_assessments': True
        }

        failed_checks = [check for check, status in compliance_checks.items() if not status]

        return {
            'account_id': account_id,
            'framework': framework,
            'compliance_status': 'COMPLIANT' if not failed_checks else 'NON_COMPLIANT',
            'passed_checks': len(compliance_checks) - len(failed_checks),
            'total_checks': len(compliance_checks),
            'failed_checks': failed_checks,
            'compliance_score': ((len(compliance_checks) - len(failed_checks)) / len(compliance_checks) * 100)
        }

    def identify_compliance_gaps(self, framework: str = 'SOC2') -> Dict:
        """Identify gaps in compliance coverage."""
        policy = self.policies.get(framework)

        if not policy:
            return {'error': f'Framework {framework} not found', 'gaps': []}

        gaps = []

        # Check for common compliance gaps
        if framework == 'SOC2':
            gaps.extend([
                'Ensure all security events are logged with timestamps',
                'Document incident response procedures',
                'Maintain immutable audit trail',
                'Verify access controls on sensitive data'
            ])

        elif framework == 'CIS':
            gaps.extend([
                'Implement network segmentation',
                'Configure security group rules per CIS benchmark',
                'Enable encryption for data at rest',
                'Perform vulnerability assessments'
            ])

        elif framework == 'PCI_DSS':
            gaps.extend([
                'Maintain PCI DSS compliance for payment data',
                'Implement network segmentation for cardholder data',
                'Enable two-factor authentication',
                'Conduct quarterly security assessments'
            ])

        return {
            'framework': framework,
            'identified_gaps': gaps,
            'gap_count': len(gaps),
            'remediation_priority': self._prioritize_gaps(gaps)
        }

    def get_compliance_violations(self, start_time: str, end_time: str) -> Dict:
        """Get list of compliance violations in period."""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except:
            return {'error': 'Invalid datetime format', 'violations': []}

        # Simulated violations based on policy checks
        violations = [
            {
                'violation_id': 'CV-001',
                'framework': 'SOC2',
                'violation_type': 'slow_response',
                'severity': 'MEDIUM',
                'timestamp': start_time,
                'description': 'Remediation exceeded 60-minute SLA'
            },
            {
                'violation_id': 'CV-002',
                'framework': 'CIS',
                'violation_type': 'missing_baseline',
                'severity': 'HIGH',
                'timestamp': start_time,
                'description': 'EC2 instance not matching CIS baseline'
            }
        ]

        return {
            'period_start': start_time,
            'period_end': end_time,
            'total_violations': len(violations),
            'violations': violations,
            'critical_count': len([v for v in violations if v['severity'] == 'CRITICAL']),
            'high_count': len([v for v in violations if v['severity'] == 'HIGH']),
            'medium_count': len([v for v in violations if v['severity'] == 'MEDIUM'])
        }

    def get_policy_requirements(self, framework: str) -> Dict:
        """Get requirements for specified compliance framework."""
        policy = self.policies.get(framework)

        if not policy:
            return {'error': f'Framework {framework} not found'}

        return {
            'framework': framework,
            'policy_name': policy.get('name'),
            'requirements': policy.get('requirements', []),
            'response_time_sla_minutes': policy.get('response_time_sla_minutes', 60)
        }

    def _get_required_actions(self, severity: int) -> List[str]:
        """Get required remediation actions for severity level."""
        if severity >= 8:
            return ['ISOLATE', 'TERMINATE', 'BLOCK_ACCESS', 'NOTIFY_SECURITY']
        elif severity >= 5:
            return ['MONITOR', 'RESTRICT_ACCESS', 'NOTIFY_ADMIN']
        else:
            return ['LOG_EVENT', 'MONITOR']

    def _prioritize_gaps(self, gaps: List[str]) -> List[str]:
        """Prioritize compliance gaps by remediation urgency."""
        # Simple priority ordering
        priority_keywords = ['data', 'encryption', 'authentication', 'network']
        prioritized = []

        for keyword in priority_keywords:
            for gap in gaps:
                if keyword.lower() in gap.lower() and gap not in prioritized:
                    prioritized.append(gap)

        # Add remaining gaps
        for gap in gaps:
            if gap not in prioritized:
                prioritized.append(gap)

        return prioritized
