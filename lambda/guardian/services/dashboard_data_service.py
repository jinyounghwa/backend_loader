from typing import Dict, List
from datetime import datetime, timedelta


class DashboardDataService:
    def __init__(self, threat_service=None, executor=None, tracker=None, audit_logger=None):
        self.threat_service = threat_service
        self.executor = executor
        self.tracker = tracker
        self.audit = audit_logger
        self._cache = {}
        self._cache_timestamp = {}

    def get_threat_dashboard(self, account_id=None, cache_ttl_seconds=30) -> Dict:
        cache_key = f"threat_dashboard_{account_id}"

        if cache_key in self._cache and self._is_cache_valid(cache_key, cache_ttl_seconds):
            return self._cache[cache_key]

        active_threats = []
        if self.threat_service:
            active_threats = self.threat_service.list_active_threats(
                account_id=account_id, severity_threshold=0
            )

        threat_summary = self._calculate_threat_summary(active_threats)
        recent_remediations = self._get_recent_remediations(5)

        dashboard_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'account_id': account_id,
            'active_threats': active_threats,
            'threat_summary': threat_summary,
            'severity_distribution': self._calculate_severity_distribution(active_threats),
            'recent_remediations': recent_remediations,
            'metrics': self._calculate_dashboard_metrics(),
        }

        self._cache[cache_key] = dashboard_data
        self._cache_timestamp[cache_key] = datetime.utcnow()

        return dashboard_data

    def get_remediation_progress(self, threat_id: str) -> Dict:
        if not self.tracker:
            return {
                'threat_id': threat_id,
                'status': 'not_available',
            }

        execution_history = self.executor.get_execution_history(threat_id) if self.executor else []

        if not execution_history:
            return {
                'threat_id': threat_id,
                'status': 'not_found',
            }

        latest_execution_id = execution_history[-1].get('execution_id')
        progress = self.tracker.get_remediation_progress(latest_execution_id)

        return {
            'threat_id': threat_id,
            'execution_id': latest_execution_id,
            'progress_percent': progress.get('progress_percent', 0),
            'status': progress.get('status', 'unknown'),
            'resources_processed': progress.get('resources_processed', 0),
            'resources_successful': progress.get('resources_successful', 0),
            'resources_failed': progress.get('resources_failed', 0),
            'started_at': progress.get('started_at'),
            'last_update': progress.get('last_update'),
        }

    def get_threat_timeline(self, threat_id: str, hours: int = 24) -> List[Dict]:
        if not self.tracker:
            return []

        timeline = self.tracker.get_threat_timeline(threat_id)

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_timeline = []

        for event in timeline:
            event_time_str = event.get('timestamp', '')
            try:
                event_time = datetime.fromisoformat(event_time_str)
                if event_time >= cutoff_time:
                    filtered_timeline.append(event)
            except (ValueError, TypeError):
                filtered_timeline.append(event)

        return filtered_timeline

    def get_executive_metrics(self, days: int = 30) -> Dict:
        if not self.threat_service or not self.executor:
            return {
                'total_threats_detected': 0,
                'threats_resolved': 0,
                'auto_remediation_rate': 0.0,
                'average_response_time': 0.0,
                'critical_threats': 0,
            }

        threat_summary = self.threat_service.get_threat_summary()
        execution_summary = self.executor.get_execution_summary()

        total_detected = threat_summary.get('total_threats_detected', 0)
        resolved = sum(threat_summary.get('threats_by_status', {}).get(status, 0)
                      for status in ['resolved', 'remediation_complete'])

        auto_remediation_count = execution_summary.get('successful_auto_remediations', 0)
        auto_remediation_rate = (
            auto_remediation_count / execution_summary.get('total_executions', 1)
            if execution_summary.get('total_executions', 0) > 0
            else 0.0
        )

        critical_threats = threat_summary.get('threats_by_severity', {}).get('critical', 0)

        return {
            'total_threats_detected': total_detected,
            'threats_resolved': resolved,
            'threats_pending': threat_summary.get('active_unresolved', 0),
            'auto_remediation_rate': auto_remediation_rate,
            'successful_auto_remediations': auto_remediation_count,
            'critical_threats': critical_threats,
            'period_days': days,
        }

    def get_threat_status_by_account(self) -> Dict:
        if not self.threat_service:
            return {}

        all_threats = self.threat_service.list_active_threats(severity_threshold=0)
        account_summary = {}

        for threat in all_threats:
            account_id = threat.get('account_id', 'unknown')
            if account_id not in account_summary:
                account_summary[account_id] = {
                    'total_threats': 0,
                    'by_severity': {},
                    'by_status': {},
                }

            account_summary[account_id]['total_threats'] += 1

            severity = threat.get('severity', 0)
            severity_level = (
                'low' if severity < 4
                else 'medium' if severity < 7
                else 'high' if severity < 9
                else 'critical'
            )
            account_summary[account_id]['by_severity'][severity_level] = (
                account_summary[account_id]['by_severity'].get(severity_level, 0) + 1
            )

            status = threat.get('status', 'unknown')
            account_summary[account_id]['by_status'][status] = (
                account_summary[account_id]['by_status'].get(status, 0) + 1
            )

        return account_summary

    def get_remediation_status_summary(self) -> Dict:
        if not self.tracker:
            return {
                'active_remediations': 0,
                'completed_remediations': 0,
                'overall_success_rate': 0.0,
            }

        progress_summary = self.tracker.get_progress_summary()

        return {
            'active_remediations': progress_summary.get('active_remediations', 0),
            'completed_remediations': progress_summary.get('completed_remediations', 0),
            'total_resources_processed': progress_summary.get('total_resources_processed', 0),
            'total_resources_successful': progress_summary.get('total_resources_successful', 0),
            'total_resources_failed': progress_summary.get('total_resources_failed', 0),
            'overall_success_rate': progress_summary.get('overall_success_rate', 0.0),
        }

    def _calculate_threat_summary(self, threats: List[Dict]) -> Dict:
        total = len(threats)
        by_status = {}
        by_severity = {}

        for threat in threats:
            status = threat.get('status', 'unknown')
            severity = threat.get('severity', 0)

            by_status[status] = by_status.get(status, 0) + 1

            severity_level = (
                'low' if severity < 4
                else 'medium' if severity < 7
                else 'high' if severity < 9
                else 'critical'
            )
            by_severity[severity_level] = by_severity.get(severity_level, 0) + 1

        return {
            'total': total,
            'by_status': by_status,
            'by_severity': by_severity,
        }

    def _calculate_severity_distribution(self, threats: List[Dict]) -> Dict:
        distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}

        for threat in threats:
            severity = threat.get('severity', 0)
            if severity < 4:
                distribution['low'] += 1
            elif severity < 7:
                distribution['medium'] += 1
            elif severity < 9:
                distribution['high'] += 1
            else:
                distribution['critical'] += 1

        return distribution

    def _get_recent_remediations(self, limit: int = 5) -> List[Dict]:
        if not self.executor:
            return []

        history = self.executor.get_execution_history()
        sorted_history = sorted(
            history,
            key=lambda x: x.get('started_at', ''),
            reverse=True
        )

        recent = []
        for execution in sorted_history[:limit]:
            recent.append({
                'execution_id': execution.get('execution_id'),
                'threat_id': execution.get('threat_id'),
                'strategy': execution.get('strategy'),
                'status': execution.get('status'),
                'started_at': execution.get('started_at'),
            })

        return recent

    def _calculate_dashboard_metrics(self) -> Dict:
        if not self.executor:
            return {}

        execution_summary = self.executor.get_execution_summary()

        return {
            'total_executions': execution_summary.get('total_executions', 0),
            'successful_auto_remediations': execution_summary.get('successful_auto_remediations', 0),
            'auto_remediation_success_rate': execution_summary.get('auto_remediation_success_rate', 0.0),
        }

    def _is_cache_valid(self, cache_key: str, ttl_seconds: int) -> bool:
        if cache_key not in self._cache_timestamp:
            return False

        age = datetime.utcnow() - self._cache_timestamp[cache_key]
        return age.total_seconds() < ttl_seconds
