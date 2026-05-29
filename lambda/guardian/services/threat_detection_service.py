from typing import Dict, List
from datetime import datetime, timezone


class ThreatDetectionService:
    def __init__(self, anomaly_detector=None, smart_engine=None, audit_logger=None):
        self.detector = anomaly_detector
        self.engine = smart_engine
        self.audit = audit_logger
        self.active_threats = []
        self.threat_correlations = {}

    def detect_and_analyze_threats(self, account_id=None, lookback_minutes=60) -> List[Dict]:
        if not self.detector:
            return []

        threats = self.detector.detect_anomalies(account_id=account_id, lookback_minutes=lookback_minutes)
        analyzed_threats = []

        for threat in threats:
            threat_data = {
                'threat_id': threat.get('threat_id', threat.get('rule_id', 'unknown')),
                'threat_type': threat.get('threat_type', 'Unknown'),
                'severity': threat.get('severity', 5),
                'account_id': threat.get('account_id', account_id),
                'detected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'evidence': threat.get('evidence', []),
                'status': 'detected',
            }

            resources = threat.get('affected_resources', [])
            if self.engine:
                strategy_result = self.engine.select_remediation_strategy(threat_data, resources)
                threat_data['recommended_strategy'] = strategy_result.get('selected_strategy')
                threat_data['safe_to_execute'] = strategy_result.get('safe_to_execute', True)
                threat_data['risk_level'] = strategy_result.get('risk_level')
                threat_data['estimated_impact'] = strategy_result.get('estimated_impact')

            analyzed_threats.append(threat_data)
            self.active_threats.append(threat_data)

        return analyzed_threats

    def get_threat_status(self, threat_id: str) -> Dict:
        for threat in self.active_threats:
            if threat.get('threat_id') == threat_id:
                return {
                    'threat_id': threat_id,
                    'detected_at': threat.get('detected_at'),
                    'severity': threat.get('severity'),
                    'status': threat.get('status', 'detected'),
                    'recommended_strategy': threat.get('recommended_strategy'),
                    'remediation_executed': threat.get('remediation_executed', False),
                }

        return {
            'threat_id': threat_id,
            'status': 'not_found',
        }

    def list_active_threats(self, account_id=None, severity_threshold=5) -> List[Dict]:
        filtered_threats = []
        for threat in self.active_threats:
            if threat.get('status') != 'resolved':
                if severity_threshold and threat.get('severity', 0) < severity_threshold:
                    continue
                if account_id and threat.get('account_id') != account_id:
                    continue
                filtered_threats.append({
                    'threat_id': threat.get('threat_id'),
                    'severity': threat.get('severity'),
                    'threat_type': threat.get('threat_type'),
                    'detected_at': threat.get('detected_at'),
                    'status': threat.get('status'),
                    'account_id': threat.get('account_id'),
                })

        return filtered_threats

    def correlate_related_threats(self, threat_id: str) -> List[Dict]:
        primary_threat = None
        for threat in self.active_threats:
            if threat.get('threat_id') == threat_id:
                primary_threat = threat
                break

        if not primary_threat:
            return []

        related_threats = []
        primary_account = primary_threat.get('account_id')
        primary_time = primary_threat.get('detected_at')

        for threat in self.active_threats:
            if threat.get('threat_id') == threat_id:
                continue

            same_account = threat.get('account_id') == primary_account
            same_type = threat.get('threat_type') == primary_threat.get('threat_type')

            if same_account or same_type:
                related_threats.append({
                    'threat_id': threat.get('threat_id'),
                    'severity': threat.get('severity'),
                    'threat_type': threat.get('threat_type'),
                    'correlation_reason': 'same_account' if same_account else 'same_type',
                })

        return related_threats

    def mark_threat_remediated(self, threat_id: str, strategy_used: str, success: bool) -> None:
        for threat in self.active_threats:
            if threat.get('threat_id') == threat_id:
                threat['remediation_executed'] = True
                threat['remediation_strategy'] = strategy_used
                threat['remediation_success'] = success
                threat['status'] = 'resolved' if success else 'remediation_failed'
                threat['remediated_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                break

    def get_threat_summary(self) -> Dict:
        total_threats = len(self.active_threats)
        by_status = {}
        by_severity = {}

        for threat in self.active_threats:
            status = threat.get('status', 'unknown')
            severity = threat.get('severity', 0)

            by_status[status] = by_status.get(status, 0) + 1

            severity_level = 'low' if severity < 4 else 'medium' if severity < 7 else 'high' if severity < 9 else 'critical'
            by_severity[severity_level] = by_severity.get(severity_level, 0) + 1

        return {
            'total_threats_detected': total_threats,
            'threats_by_status': by_status,
            'threats_by_severity': by_severity,
            'active_unresolved': sum(1 for t in self.active_threats if t.get('status') != 'resolved'),
        }
