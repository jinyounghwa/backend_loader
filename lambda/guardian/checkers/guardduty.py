"""GuardDuty checker for threat detection."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from guardian.checkers.base import BaseChecker, CheckResult

logger = logging.getLogger(__name__)


class GuardDutyChecker(BaseChecker):

    SEVERITY_MAP = {
        'CRITICAL': 7.0,
        'HIGH': 4.0,
        'MEDIUM': 2.0,
        'LOW': 0.1
    }

    def __init__(self, clients: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(clients, config)
        self.guardduty = clients.get('guardduty')
        self.ec2 = clients.get('ec2')
        self.lookback_hours = config.get('guardduty_lookback_hours', 24)

    def check(self) -> CheckResult:
        """Check for GuardDuty threats."""
        self._log_check_start('GuardDuty')

        try:
            # Get active GuardDuty findings
            findings = self._get_active_findings()

            if not findings:
                self._log_check_end('GuardDuty', 'INFO')
                return CheckResult.info(
                    'GuardDuty Check',
                    'No active security threats detected'
                )

            # Analyze findings by severity
            high_severity = [f for f in findings if f['severity'] >= 7.0]
            med_severity = [f for f in findings if 4.0 <= f['severity'] < 7.0]

            overall_severity = self._determine_severity(findings)
            self._log_check_end('GuardDuty', overall_severity)

            return CheckResult(
                severity=overall_severity,
                title='Security Threats Detected',
                message=f'GuardDuty found {len(findings)} threat(s) - High: {len(high_severity)}, Medium: {len(med_severity)}',
                details={
                    'high_severity': high_severity[:5],  # Top 5
                    'medium_severity': med_severity[:5],
                    'total': len(findings)
                },
                suggested_action=self._get_remediation_suggestion(findings)
            )

        except Exception as e:
            self._log_error('GuardDuty', e)
            return CheckResult.error(
                'GuardDuty Check Failed',
                f'Failed to check GuardDuty: {str(e)}'
            )

    def _get_active_findings(self) -> List[Dict[str, Any]]:
        """Get active GuardDuty findings."""
        if not self.guardduty:
            return []

        findings = []

        try:
            # List detectors first
            detectors = self.guardduty.list_detectors()
            if not detectors.get('DetectorIds'):
                return []

            detector_id = detectors['DetectorIds'][0]

            # List findings
            response = self.guardduty.list_findings(
                DetectorId=detector_id,
                FindingCriteria={
                    'Criterion': {
                        'updatedAt': {
                            'Gte': int((datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)).timestamp() * 1000)
                        },
                        'severity': {
                            'Gte': 4  # Medium and above
                        }
                    }
                }
            )

            if response.get('FindingIds'):
                # Get finding details
                findings_response = self.guardduty.get_findings(
                    DetectorId=detector_id,
                    FindingIds=response['FindingIds'][:20]  # Limit to 20
                )

                for finding in findings_response.get('Findings', []):
                    findings.append({
                        'id': finding.get('Id'),
                        'type': finding.get('Type'),
                        'severity': float(finding.get('Severity', 0)),
                        'title': finding.get('Title'),
                        'description': finding.get('Description'),
                        'resource_type': finding.get('Resource', {}).get('ResourceType'),
                        'resource_id': finding.get('Resource', {}).get('InstanceDetails', {}).get('InstanceId'),
                        'updated_at': finding.get('UpdatedAt')
                    })

        except Exception as e:
            logger.warning(f"Error fetching GuardDuty findings: {str(e)}")

        return findings

    def _determine_severity(self, findings: List[Dict[str, Any]]) -> str:
        """Determine overall severity from findings."""
        if not findings:
            return 'INFO'

        max_severity = max(f['severity'] for f in findings)

        if max_severity >= 7.0:
            return 'CRITICAL'
        elif max_severity >= 4.0:
            return 'HIGH'
        else:
            return 'MEDIUM'

    def _get_remediation_suggestion(self, findings: List[Dict[str, Any]]) -> str:
        """Get remediation suggestions based on finding types."""
        threat_types = set()
        for finding in findings:
            threat_type = finding.get('type', '')
            if threat_type:
                # Extract both category (before :) and detail (after /)
                category = threat_type.split(':')[0] if ':' in threat_type else ''
                detail = threat_type.split('/')[-1] if '/' in threat_type else threat_type
                if category:
                    threat_types.add(category)
                if detail:
                    threat_types.add(detail)

        suggestions = []

        if 'RDPBruteForce' in threat_types:
            suggestions.append('Restrict RDP access (port 3389) in Security Groups')

        if 'SSHBruteForce' in threat_types:
            suggestions.append('Restrict SSH access (port 22) in Security Groups')

        if 'CryptoCurrency' in threat_types:
            suggestions.append('Terminate compromised instance and investigate')

        if 'Spambot' in threat_types:
            suggestions.append('Stop instance immediately and review for malware')

        if 'UnauthorizedAccess' in threat_types:
            suggestions.append('Review IAM policies and access logs')

        if not suggestions:
            suggestions.append('Review GuardDuty findings and take appropriate action')

        return ' | '.join(suggestions)
