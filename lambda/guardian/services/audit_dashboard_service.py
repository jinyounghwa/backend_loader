"""Audit Dashboard Service for real-time compliance metrics and visualization."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class AuditDashboardService:
    """Provides real-time dashboard data for audit trail and compliance metrics."""

    def __init__(self, audit_service=None, report_generator=None):
        """Initialize audit dashboard service."""
        self.audit = audit_service
        self.reports = report_generator

    def get_audit_timeline(self, threat_id: str) -> Dict:
        """Get chronological timeline for threat lifecycle from detection to resolution."""
        if not self.audit:
            return {'error': 'Audit service not configured', 'events': []}

        threat_events = self.audit.get_threat_audit_chain(threat_id)

        timeline = {
            'threat_id': threat_id,
            'event_count': len(threat_events),
            'timeline_start': threat_events[0]['timestamp'] if threat_events else None,
            'timeline_end': threat_events[-1]['timestamp'] if threat_events else None,
            'events': []
        }

        for event in threat_events:
            timeline['events'].append({
                'timestamp': event['timestamp'],
                'event_type': event['event_type'],
                'action': event.get('action', event.get('detector_id')),
                'status': event.get('status'),
                'details': event
            })

        return timeline

    def get_compliance_metrics(self, framework: str = 'SOC2') -> Dict:
        """Get real-time compliance metrics for specified framework."""
        if not self.reports:
            return {
                'framework': framework,
                'compliance_score': 0,
                'status': 'UNKNOWN',
                'metrics': {}
            }

        latest_report = self._find_latest_report(framework)

        if not latest_report:
            return {
                'framework': framework,
                'compliance_score': 0,
                'status': 'NO_REPORTS',
                'metrics': {}
            }

        metrics = latest_report.get('metrics', {})
        compliance_score = self._calculate_score(metrics)

        return {
            'framework': framework,
            'compliance_score': compliance_score,
            'status': metrics.get('compliance_status', 'UNKNOWN'),
            'last_updated': latest_report.get('generated_date'),
            'metrics': metrics,
            'trend': 'improving' if compliance_score > 85 else 'declining'
        }

    def get_remediation_effectiveness(self) -> Dict:
        """Calculate remediation success rates and efficiency metrics."""
        if not self.audit:
            return {'error': 'Audit service not configured'}

        # Get remediation events from past 30 days
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)

        events = self.audit.get_audit_trail(
            start_time.isoformat(),
            end_time.isoformat()
        )

        remediation_events = [e for e in events if e.get('event_type') == 'REMEDIATION_ACTION']
        threat_events = [e for e in events if e.get('event_type') == 'THREAT_DETECTION']

        successful = len([e for e in remediation_events if e.get('status') == 'SUCCESS'])
        failed = len([e for e in remediation_events if e.get('status') == 'FAILED'])
        success_rate = (successful / len(remediation_events) * 100) if remediation_events else 0

        return {
            'total_threats': len(threat_events),
            'total_remediations': len(remediation_events),
            'successful_remediations': successful,
            'failed_remediations': failed,
            'success_rate': success_rate,
            'average_resources_per_remediation': (
                sum(len(e.get('resources_affected', [])) for e in remediation_events) / len(remediation_events)
                if remediation_events else 0
            ),
            'period_days': 30,
            'effectiveness_grade': self._calculate_grade(success_rate)
        }

    def get_policy_violation_summary(self) -> Dict:
        """Summarize policy violations by account and type."""
        if not self.audit:
            return {'error': 'Audit service not configured', 'violations': {}}

        events = self.audit.get_audit_trail(
            (datetime.utcnow() - timedelta(days=30)).isoformat(),
            datetime.utcnow().isoformat()
        )

        policy_events = [e for e in events if e.get('event_type') == 'POLICY_ENFORCEMENT']

        violations_by_account = defaultdict(int)
        violations_by_policy = defaultdict(int)

        for event in policy_events:
            if event.get('decision') == 'VIOLATION':
                account = event.get('account_id', 'unknown')
                policy = event.get('policy_name', 'unknown')
                violations_by_account[account] += 1
                violations_by_policy[policy] += 1

        return {
            'total_violations': len([e for e in policy_events if e.get('decision') == 'VIOLATION']),
            'total_policy_checks': len(policy_events),
            'violations_by_account': dict(violations_by_account),
            'violations_by_policy': dict(violations_by_policy),
            'compliance_rate': (
                (len(policy_events) - len([e for e in policy_events if e.get('decision') == 'VIOLATION']))
                / len(policy_events) * 100
            ) if policy_events else 0
        }

    def get_audit_activity_heatmap(self, period_days: int = 7) -> Dict:
        """Get activity heatmap showing when threats are most common (hour of day)."""
        if not self.audit:
            return {'error': 'Audit service not configured', 'heatmap': {}}

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)

        events = self.audit.get_audit_trail(
            start_time.isoformat(),
            end_time.isoformat()
        )

        # Count events by hour of day
        hourly_counts = defaultdict(int)
        for event in events:
            try:
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                hour = event_time.hour
                hourly_counts[hour] += 1
            except:
                pass

        # Fill in missing hours with 0
        heatmap = {hour: hourly_counts.get(hour, 0) for hour in range(24)}

        peak_hour = max(heatmap, key=heatmap.get) if heatmap else 0
        peak_activity = heatmap.get(peak_hour, 0)

        return {
            'period_days': period_days,
            'hourly_activity': heatmap,
            'peak_hour': peak_hour,
            'peak_activity_count': peak_activity,
            'total_events': len(events)
        }

    def get_user_activity_summary(self, user_id: Optional[str] = None) -> Dict:
        """Get user action summary by user or aggregate of all users."""
        if not self.audit:
            return {'error': 'Audit service not configured', 'users': {}}

        if user_id:
            actions = self.audit.get_user_action_history(user_id)
            return {
                'user_id': user_id,
                'action_count': len(actions),
                'actions': [
                    {
                        'action': a.get('action'),
                        'target': a.get('target'),
                        'timestamp': a.get('timestamp')
                    }
                    for a in actions
                ]
            }
        else:
            # Aggregate all user actions
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            events = self.audit.get_audit_trail(
                start_time.isoformat(),
                end_time.isoformat()
            )

            user_actions = defaultdict(list)
            for event in events:
                if event.get('event_type') == 'USER_ACTION':
                    user_id = event.get('user_id', 'unknown')
                    user_actions[user_id].append(event)

            return {
                'total_users': len(user_actions),
                'period_days': 30,
                'users': {
                    uid: {
                        'action_count': len(actions),
                        'actions': [a.get('action') for a in actions]
                    }
                    for uid, actions in user_actions.items()
                }
            }

    def get_threat_response_metrics(self) -> Dict:
        """Calculate MTTR (Mean Time To Remediate) and remediation efficiency."""
        if not self.audit:
            return {'error': 'Audit service not configured'}

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)

        events = self.audit.get_audit_trail(
            start_time.isoformat(),
            end_time.isoformat()
        )

        threat_events = [e for e in events if e.get('event_type') == 'THREAT_DETECTION']
        remediation_events = [e for e in events if e.get('event_type') == 'REMEDIATION_ACTION']

        # Calculate MTTR
        response_times = []
        for threat in threat_events:
            threat_id = threat.get('threat_id')
            remediations = [r for r in remediation_events if r.get('threat_id') == threat_id]
            if remediations:
                threat_time = datetime.fromisoformat(threat['timestamp'].replace('Z', '+00:00'))
                remediation_time = datetime.fromisoformat(remediations[0]['timestamp'].replace('Z', '+00:00'))
                time_diff = (remediation_time - threat_time).total_seconds() / 60  # in minutes
                response_times.append(time_diff)

        avg_mttr = sum(response_times) / len(response_times) if response_times else 0

        return {
            'total_threats': len(threat_events),
            'total_remediations': len(remediation_events),
            'threats_remediated': len([t for t in threat_events if any(r.get('threat_id') == t.get('threat_id') for r in remediation_events)]),
            'mean_time_to_remediate_minutes': avg_mttr,
            'median_response_time': self._calculate_median(response_times) if response_times else 0,
            'sla_compliance_target_minutes': 60,
            'sla_compliance_rate': (
                len([t for t in response_times if t <= 60]) / len(response_times) * 100
                if response_times else 0
            ),
            'efficiency_grade': self._calculate_efficiency_grade(avg_mttr)
        }

    def _find_latest_report(self, framework: str) -> Optional[Dict]:
        """Find most recent report for specified framework."""
        if not self.reports or not self.reports.reports:
            return None
        matching = [r for r in self.reports.reports if framework in r.get('report_type', '')]
        return matching[-1] if matching else None

    def _calculate_score(self, metrics: Dict) -> float:
        """Calculate compliance score from metrics."""
        values = [v for v in metrics.values() if isinstance(v, (int, float))]
        return sum(values) / len(values) if values else 0

    def _calculate_grade(self, success_rate: float) -> str:
        """Convert success rate to letter grade."""
        if success_rate >= 95:
            return 'A'
        elif success_rate >= 85:
            return 'B'
        elif success_rate >= 75:
            return 'C'
        else:
            return 'D'

    def _calculate_efficiency_grade(self, mttr: float) -> str:
        """Convert MTTR to efficiency grade."""
        if mttr <= 15:
            return 'EXCELLENT'
        elif mttr <= 30:
            return 'GOOD'
        elif mttr <= 60:
            return 'ACCEPTABLE'
        else:
            return 'NEEDS_IMPROVEMENT'

    def _calculate_median(self, values: List[float]) -> float:
        """Calculate median of values."""
        if not values:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        return sorted_values[n//2]
