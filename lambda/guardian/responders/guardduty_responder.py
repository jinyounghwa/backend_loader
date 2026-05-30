"""GuardDuty response and threat mitigation."""

from typing import Dict, List, Any, Optional


class GuardDutyAutoResponder:
    """Automatically respond to GuardDuty findings."""

    SEVERITY_THRESHOLDS = {
        'CRITICAL': 8.0,
        'HIGH': 5.0,
        'MEDIUM': 3.0,
        'LOW': 0.0
    }

    CRITICAL_THREAT_TYPES = [
        'Trojan',
        'Persistence',
        'PrivilegeEscalation',
        'DefenseEvasion',
        'Exfiltration'
    ]

    def respond(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automated response to finding."""
        finding_type = finding.get('Type', '')
        severity = finding.get('Severity', 0)
        resource_id = finding.get('Resource', {}).get('InstanceDetails', {}).get('InstanceId')

        # Determine severity level
        severity_level = self._get_severity_level(severity)

        # Determine action based on severity and threat type
        action = self._determine_action(finding_type, severity, severity_level)

        reason = self._get_reason(finding_type, severity)

        return {
            'action': action,
            'target': resource_id,
            'severity': severity_level,
            'finding_type': finding_type,
            'reason': reason,
            'timestamp': finding.get('UpdatedAt'),
            'finding_id': finding.get('Id')
        }

    def _get_severity_level(self, severity: float) -> str:
        """Map severity score to level."""
        if severity >= self.SEVERITY_THRESHOLDS['CRITICAL']:
            return 'CRITICAL'
        elif severity >= self.SEVERITY_THRESHOLDS['HIGH']:
            return 'HIGH'
        elif severity >= self.SEVERITY_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _determine_action(self, finding_type: str, severity: float, severity_level: str) -> str:
        """Determine response action."""
        # Critical threats: isolate
        if severity_level == 'CRITICAL':
            return 'ISOLATE'

        # High severity malware: isolate
        if severity_level == 'HIGH' and any(threat in finding_type for threat in ['Trojan', 'Persistence']):
            return 'ISOLATE'

        # High severity unauthorized access: alert/block
        if severity_level == 'HIGH' and 'UnauthorizedAccess' in finding_type:
            return 'ISOLATE'

        # Medium and below: alert
        return 'ALERT'

    def _get_reason(self, finding_type: str, severity: float) -> str:
        """Get reason for response."""
        if 'Trojan' in finding_type or 'CryptoCurrency' in finding_type:
            return 'critical_malware_detected'
        elif 'UnauthorizedAccess' in finding_type:
            return 'unauthorized_access_detected'
        elif 'Recon' in finding_type:
            return 'reconnaissance_detected'
        elif severity >= 7.0:
            return 'critical_threat_detected'
        else:
            return 'threat_detected'


class ResponseOrchestrator:
    """Orchestrate multi-step responses to threats."""

    def create_response_plan(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive response plan."""
        threat_type = threat.get('type', '')
        severity = threat.get('severity', 0)
        resource = threat.get('resource', '')

        actions = []
        priority = 'LOW'

        # Determine priority
        if severity >= 8.0:
            priority = 'CRITICAL'
        elif severity >= 5.0:
            priority = 'HIGH'
        elif severity >= 3.0:
            priority = 'MEDIUM'

        # Build response plan based on threat type
        if threat_type == 'MALWARE':
            actions = [
                'ISOLATE_RESOURCE',
                'COLLECT_FORENSICS',
                'NOTIFY_SECURITY_TEAM',
                'REVOKE_CREDENTIALS',
                'SCAN_RELATED_RESOURCES'
            ]
        elif threat_type == 'DATA_EXFILTRATION':
            actions = [
                'REVOKE_CREDENTIALS',
                'BLOCK_DESTINATION_IP',
                'ISOLATE_RESOURCE',
                'AUDIT_DATA_ACCESS',
                'NOTIFY_SECURITY_TEAM',
                'NOTIFY_DATA_OWNER'
            ]
        elif threat_type == 'UNAUTHORIZED_ACCESS':
            actions = [
                'REVOKE_SESSION',
                'ALERT_SECURITY_TEAM',
                'ENABLE_MFA',
                'RESET_CREDENTIALS'
            ]
        elif threat_type == 'RECON':
            actions = [
                'ALERT_SECURITY_TEAM',
                'ENABLE_ENHANCED_LOGGING',
                'REVIEW_NETWORK_RULES'
            ]
        else:
            actions = [
                'ALERT',
                'NOTIFY_SECURITY_TEAM'
            ]

        return {
            'threat_id': threat.get('threat_id'),
            'resource': resource,
            'priority': priority,
            'actions': actions,
            'estimated_time_minutes': len(actions) * 5,
            'requires_approval': priority in ['CRITICAL', 'HIGH']
        }

    def execute_response(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute response plan."""
        actions = plan.get('actions', [])
        results = {}

        for action in actions:
            results[action] = {
                'status': 'EXECUTED',
                'timestamp': '2026-05-30T10:00:00Z'
            }

        return {
            'plan_id': plan.get('threat_id'),
            'status': 'COMPLETED',
            'actions_executed': len(results),
            'results': results
        }
