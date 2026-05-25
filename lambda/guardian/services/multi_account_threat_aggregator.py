from typing import Dict, List
from datetime import datetime


class MultiAccountThreatAggregator:
    def __init__(self, threat_detection_services=None, audit_logger=None):
        self.threat_services = threat_detection_services or {}
        self.audit = audit_logger
        self.aggregated_threats = []

    def register_account(self, account_id: str, threat_service) -> None:
        self.threat_services[account_id] = threat_service

    def detect_threats_all_accounts(self, lookback_minutes=60) -> List[Dict]:
        all_threats = []

        for account_id, service in self.threat_services.items():
            threats = service.detect_and_analyze_threats(
                account_id=account_id,
                lookback_minutes=lookback_minutes
            )
            all_threats.extend(threats)

        self.aggregated_threats = all_threats
        return all_threats

    def get_threats_by_account(self, account_id: str) -> List[Dict]:
        return [t for t in self.aggregated_threats if t.get('account_id') == account_id]

    def identify_cross_account_threats(self) -> List[Dict]:
        cross_account_threats = []
        threat_patterns = {}

        for threat in self.aggregated_threats:
            threat_key = threat.get('threat_type')
            if threat_key not in threat_patterns:
                threat_patterns[threat_key] = []
            threat_patterns[threat_key].append(threat)

        for threat_type, threats in threat_patterns.items():
            accounts = set(t.get('account_id') for t in threats)
            if len(accounts) > 1:
                cross_account_threats.extend(threats)

        return cross_account_threats

    def correlate_threats_across_accounts(self) -> List[Dict]:
        correlated = []
        threat_map = {}

        for threat in self.aggregated_threats:
            threat_type = threat.get('threat_type')
            if threat_type not in threat_map:
                threat_map[threat_type] = []
            threat_map[threat_type].append(threat)

        for threat_type, threats in threat_map.items():
            if len(threats) > 1:
                for threat in threats:
                    threat['correlation_group'] = threat_type
                    threat['correlated_count'] = len(threats)
                    correlated.append(threat)

        return correlated

    def get_threat_distribution(self) -> Dict:
        distribution = {
            'total_threats': len(self.aggregated_threats),
            'by_account': {},
            'by_severity': {},
            'by_type': {},
        }

        for threat in self.aggregated_threats:
            account = threat.get('account_id', 'unknown')
            severity = threat.get('severity', 0)
            threat_type = threat.get('threat_type', 'unknown')

            if account not in distribution['by_account']:
                distribution['by_account'][account] = 0
            distribution['by_account'][account] += 1

            severity_level = 'low' if severity < 4 else 'medium' if severity < 7 else 'high' if severity < 9 else 'critical'
            if severity_level not in distribution['by_severity']:
                distribution['by_severity'][severity_level] = 0
            distribution['by_severity'][severity_level] += 1

            if threat_type not in distribution['by_type']:
                distribution['by_type'][threat_type] = 0
            distribution['by_type'][threat_type] += 1

        return distribution
