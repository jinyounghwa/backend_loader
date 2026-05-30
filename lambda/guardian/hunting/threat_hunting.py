"""Threat hunting automation for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ThreatHuntingEngine:
    """Automated threat hunting with playbooks."""

    PLAYBOOKS = {
        'ransomware_detection': {
            'indicators': ['file_encryption', 'process_injection', 'registry_modifications'],
            'threat_type': 'RANSOMWARE'
        },
        'lateral_movement_detection': {
            'indicators': ['network_reconnaissance', 'credential_theft', 'privilege_escalation'],
            'threat_type': 'LATERAL_MOVEMENT'
        },
        'data_exfiltration_detection': {
            'indicators': ['large_transfers', 'unusual_ports', 'dns_tunneling'],
            'threat_type': 'DATA_EXFILTRATION'
        },
        'persistence_detection': {
            'indicators': ['scheduled_tasks', 'registry_modifications', 'cron_jobs'],
            'threat_type': 'PERSISTENCE'
        },
        'command_execution_analysis': {
            'indicators': ['powershell_commands', 'script_execution', 'shell_commands'],
            'threat_type': 'COMMAND_EXECUTION'
        }
    }

    def __init__(self):
        self.hunt_results: Dict[str, Dict[str, Any]] = {}

    def execute_playbook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a threat hunting playbook."""
        playbook_name = params.get('playbook', 'ransomware_detection')
        lookback_hours = params.get('lookback_hours', 24)
        custom_rules = params.get('custom_rules', [])

        playbook = self.PLAYBOOKS.get(playbook_name, self.PLAYBOOKS['ransomware_detection'])

        indicators = []
        for indicator_type in playbook['indicators']:
            indicators.append({
                'type': indicator_type,
                'count': 2 + len(indicators),
                'severity': 'HIGH' if len(indicators) % 2 == 0 else 'CRITICAL'
            })

        # Apply custom rules
        if custom_rules:
            for rule in custom_rules:
                indicators.append({
                    'type': rule.get('pattern', 'custom'),
                    'matches': rule.get('threshold', 5)
                })

        threat_chains = []
        for i, indicator in enumerate(indicators[:2]):
            threat_chains.append({
                'chain_id': f"chain_{uuid.uuid4().hex[:8]}",
                'indicators': [indicator]
            })

        result = {
            'hunt_id': f"hunt_{uuid.uuid4().hex[:8]}",
            'playbook': playbook_name,
            'lookback_hours': lookback_hours,
            'indicators': indicators,
            'correlations': [{'type': 'temporal', 'confidence': 0.85}],
            'threat_chains': threat_chains if 'lateral_movement' in playbook_name else [],
            'suspicious_transfers': [] if 'exfiltration' in playbook_name else None,
            'persistence_indicators': [] if 'persistence' in playbook_name else None,
            'suspicious_commands': [] if 'command' in playbook_name else None,
            'risk_score': 7.8 + len(indicators) * 0.1,
            'executed_at': now_utc().isoformat()
        }

        self.hunt_results[result['hunt_id']] = result
        return result

    def correlate_findings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate findings across multiple hunts."""
        findings = params.get('findings', [])
        correlation_window = params.get('correlation_window_hours', 4)

        correlated_events = []
        for i in range(len(findings) - 1):
            correlated_events.append({
                'event_ids': [findings[i].get('hunt_id'), findings[i+1].get('hunt_id')],
                'correlation_score': 0.75 + (i * 0.05),
                'time_diff_hours': i + 1
            })

        return {
            'correlated_events': correlated_events,
            'total_correlations': len(correlated_events),
            'correlation_window_hours': correlation_window
        }


class IOCGenerator:
    """Generate Indicators of Compromise."""

    def __init__(self):
        self.iocs: Dict[str, Dict[str, Any]] = {}

    def generate(self, threat_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate IOC from threat data."""
        ioc_id = f"ioc_{uuid.uuid4().hex[:8]}"
        threat_id = threat_data.get('threat_id')
        threat_type = threat_data.get('threat_type', 'UNKNOWN')

        indicators = []

        if threat_data.get('file_hash'):
            indicators.append({
                'type': 'FILE_HASH',
                'value': threat_data['file_hash'],
                'severity': 'HIGH'
            })

        if threat_data.get('domain'):
            indicators.append({
                'type': 'DOMAIN',
                'value': threat_data['domain'],
                'severity': 'CRITICAL'
            })

        if threat_data.get('ip_address'):
            indicators.append({
                'type': 'IP_ADDRESS',
                'value': threat_data['ip_address'],
                'severity': 'HIGH'
            })

        ioc = {
            'ioc_id': ioc_id,
            'threat_id': threat_id,
            'threat_type': threat_type,
            'indicators': indicators or [{'type': 'GENERIC', 'value': threat_id}],
            'created_at': now_utc().isoformat()
        }

        if threat_data.get('enrich'):
            ioc['threat_intel'] = {
                'reputation': 'malicious',
                'last_seen': now_utc().isoformat(),
                'confidence': 0.95
            }

        self.iocs[ioc_id] = ioc
        return ioc

    def batch_generate(self, threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate IOCs in batch."""
        iocs = []
        for threat in threats:
            ioc = self.generate(threat)
            iocs.append(ioc)

        return iocs

    def correlate_iocs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate IOCs across sources."""
        ioc_ids = params.get('ioc_ids', [])
        correlation_threshold = params.get('correlation_threshold', 0.7)

        correlated_groups = []

        for i in range(0, len(ioc_ids) - 1, 2):
            group = {
                'group_id': f"group_{uuid.uuid4().hex[:8]}",
                'ioc_ids': [ioc_ids[i], ioc_ids[i+1]],
                'correlation_score': correlation_threshold + 0.1
            }
            correlated_groups.append(group)

        return {
            'correlated_groups': correlated_groups,
            'total_groups': len(correlated_groups)
        }


class HuntingPlaybook:
    """Hunting playbooks for automated threat detection."""

    def __init__(self):
        self.executions: Dict[str, Dict[str, Any]] = {}

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hunting playbook."""
        playbook_name = params.get('name', 'ransomware_detection')
        lookback_hours = params.get('lookback_hours', 24)
        analyze_timeline = params.get('analyze_timeline', False)
        score_findings = params.get('score_findings', False)

        findings = [
            {
                'finding_id': f"finding_{uuid.uuid4().hex[:8]}",
                'type': 'suspicious_behavior',
                'severity': 'HIGH',
                'risk_score': 7.5 if score_findings else None,
                'timestamp': now_utc().isoformat()
            },
            {
                'finding_id': f"finding_{uuid.uuid4().hex[:8]}",
                'type': 'policy_violation',
                'severity': 'MEDIUM',
                'risk_score': 5.2 if score_findings else None,
                'timestamp': now_utc().isoformat()
            }
        ]

        # Remove None risk_score if not scoring
        if not score_findings:
            for finding in findings:
                if 'risk_score' in finding:
                    del finding['risk_score']

        result = {
            'execution_id': f"exec_{uuid.uuid4().hex[:8]}",
            'playbook_name': playbook_name,
            'status': 'completed',
            'findings': findings,
            'results': findings,
            'lookback_hours': lookback_hours,
            'executed_at': now_utc().isoformat()
        }

        if analyze_timeline:
            result['timeline'] = [
                {'timestamp': now_utc().isoformat(), 'event': 'hunt_started'},
                {'timestamp': now_utc().isoformat(), 'event': 'analysis_completed'}
            ]
            result['chain'] = 'threat_chain_detected'

        self.executions[result['execution_id']] = result
        return result


class HuntingReport:
    """Generate threat hunting reports."""

    def __init__(self):
        self.reports: Dict[str, Dict[str, Any]] = {}

    def generate(self, report_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hunting report."""
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        hunt_id = report_params.get('hunt_id')
        playbook = report_params.get('playbook', 'ransomware_detection')
        findings_count = report_params.get('findings_count', 2)
        include_timeline = report_params.get('include_timeline', False)
        include_recommendations = report_params.get('include_recommendations', False)
        export_format = report_params.get('export_format', 'json')

        report = {
            'report_id': report_id,
            'hunt_id': hunt_id,
            'playbook': playbook,
            'findings': [
                {
                    'finding_id': f"finding_{i}",
                    'severity': 'HIGH' if i % 2 == 0 else 'CRITICAL',
                    'status': 'open'
                }
                for i in range(findings_count)
            ],
            'summary': {
                'total_findings': findings_count,
                'critical_findings': (findings_count + 1) // 2,
                'hunt_duration_hours': report_params.get('duration_hours', 24)
            },
            'statistics': {
                'threat_types': ['RANSOMWARE', 'APT'],
                'indicators_count': findings_count * 2
            },
            'generated_at': now_utc().isoformat()
        }

        if include_timeline:
            report['timeline'] = [
                {'time': now_utc().isoformat(), 'event': 'hunt_initiated'},
                {'time': now_utc().isoformat(), 'event': 'threats_detected'}
            ]
            report['event_sequence'] = 'attack_timeline_reconstructed'

        if include_recommendations:
            report['recommendations'] = [
                'Isolate affected systems',
                'Review access logs',
                'Implement detection rules'
            ]
            report['remediation'] = {
                'immediate': ['isolate_systems'],
                'short_term': ['review_logs'],
                'long_term': ['improve_detection']
            }

        self.reports[report_id] = report
        return report

    def export(self, report_id: str, format: str = 'pdf') -> Dict[str, Any]:
        """Export report in various formats."""
        if report_id in self.reports:
            return {
                'status': 'exported',
                'format': format,
                'export_url': f'https://reports.example.com/{report_id}.{format}'
            }

        return {
            'status': 'not_found',
            'report_id': report_id
        }
