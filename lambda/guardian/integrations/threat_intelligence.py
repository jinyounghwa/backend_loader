"""Threat Intelligence integration: External threat data enrichment"""

import re
from typing import Dict, List, Optional
from datetime import datetime


class ThreatIntelligenceAPI:
    """Integrate with external threat intelligence sources."""

    def __init__(self):
        self.threat_db = {
            'ssh_bruteforce': {
                'type': 'brute_force',
                'description': 'SSH brute force attack pattern',
                'risk_score': 8,
                'mitigation': 'Restrict SSH to known IPs, enable MFA'
            },
            'sql_injection': {
                'type': 'injection',
                'description': 'SQL injection attack pattern',
                'risk_score': 9,
                'mitigation': 'Use parameterized queries, input validation'
            },
            'xss': {
                'type': 'web',
                'description': 'Cross-site scripting attack pattern',
                'risk_score': 7,
                'mitigation': 'Input sanitization, output encoding'
            },
            'dos': {
                'type': 'availability',
                'description': 'Denial of service attack',
                'risk_score': 8,
                'mitigation': 'Rate limiting, WAF, DDoS protection'
            },
            'privilege_escalation': {
                'type': 'privilege',
                'description': 'Privilege escalation attempt',
                'risk_score': 9,
                'mitigation': 'Least privilege, regular audits'
            },
            'data_exfiltration': {
                'type': 'data',
                'description': 'Unauthorized data access/exfiltration',
                'risk_score': 10,
                'mitigation': 'Encryption, DLP, access controls'
            }
        }

    def lookup_threat(self, threat_signature: str) -> Optional[Dict]:
        """Look up threat information from database."""
        if threat_signature in self.threat_db:
            return self.threat_db[threat_signature]

        # Try fuzzy matching
        for key in self.threat_db.keys():
            if key in threat_signature.lower() or threat_signature.lower() in key:
                return self.threat_db[key]

        return None

    def match_pattern(self, data: Dict) -> Optional[Dict]:
        """Match threat pattern from data."""
        threat_type = data.get('type', '').lower()

        # Pattern matching
        patterns = {
            'auth_failure': r'(ssh|login|auth).*(failed|denied|rejected)',
            'privilege_escalation': r'(sudo|permission|denied|unauthorized)',
            'data_access': r'(read|write|access|query).*(database|file|s3)',
            'network': r'(connection|port|protocol|firewall)'
        }

        for pattern_name, pattern_regex in patterns.items():
            if re.search(pattern_regex, threat_type):
                return {
                    'pattern': pattern_name,
                    'confidence': 0.7,
                    'matched_type': threat_type
                }

        return None

    def enrich_threat(self, threat: Dict) -> Dict:
        """Enrich threat with intelligence data."""
        enrichment = {
            'threat_intel': None,
            'pattern_match': None,
            'risk_score': 5,
            'recommendations': []
        }

        # Look up in threat database
        threat_signature = threat.get('signature', threat.get('type', ''))
        intel = self.lookup_threat(threat_signature)

        if intel:
            enrichment['threat_intel'] = intel
            enrichment['risk_score'] = intel.get('risk_score', 5)
            enrichment['recommendations'].append(intel.get('mitigation', ''))

        # Try pattern matching
        pattern = self.match_pattern(threat)
        if pattern:
            enrichment['pattern_match'] = pattern
            enrichment['risk_score'] = max(enrichment['risk_score'], 6)

        return enrichment


class ThreatCorrelationEngine:
    """Correlate multiple threats to identify campaigns."""

    def __init__(self):
        self.threat_history: List[Dict] = []

    def add_threat(self, threat: Dict) -> None:
        """Add threat to history."""
        threat_with_time = {**threat, 'added_at': datetime.utcnow().isoformat()}
        self.threat_history.append(threat_with_time)

    def find_related_threats(self, threat: Dict, time_window_hours: int = 24) -> List[Dict]:
        """Find related threats within time window."""
        threat_type = threat.get('type')
        source = threat.get('source')

        related = []
        for t in self.threat_history:
            # Match by type or source
            if (t.get('type') == threat_type or t.get('source') == source):
                related.append(t)

        return related

    def correlate_threats(self, threats: List[Dict]) -> Dict:
        """Correlate threats to identify patterns/campaigns."""
        if not threats:
            return {
                'correlation_found': False,
                'campaign': None,
                'threat_count': 0
            }

        # Count threat types
        threat_types = {}
        for threat in threats:
            t_type = threat.get('type', 'unknown')
            threat_types[t_type] = threat_types.get(t_type, 0) + 1

        # If multiple threats of same type, might be a campaign
        if max(threat_types.values()) > 2:
            most_common = max(threat_types.items(), key=lambda x: x[1])
            return {
                'correlation_found': True,
                'campaign': f'potential_{most_common[0]}_campaign',
                'threat_count': most_common[1],
                'threat_type': most_common[0],
                'confidence': 0.7
            }

        return {
            'correlation_found': False,
            'campaign': None,
            'threat_count': len(threats)
        }


class ThreatValidation:
    """Validate threat authenticity and severity."""

    def __init__(self):
        self.false_positive_patterns = [
            'test',
            'demo',
            'staging',
            'development',
            'experiment'
        ]

    def is_false_positive(self, threat: Dict) -> bool:
        """Check if threat is likely a false positive."""
        threat_description = str(threat).lower()

        for fp_pattern in self.false_positive_patterns:
            if fp_pattern in threat_description:
                return True

        return False

    def validate_threat(self, threat: Dict) -> Dict:
        """Validate threat and return validation result."""
        is_fp = self.is_false_positive(threat)

        return {
            'is_valid': not is_fp,
            'is_false_positive': is_fp,
            'confidence': 0.85 if is_fp else 0.9,
            'validation_status': 'false_positive' if is_fp else 'valid'
        }


class ThreatIntelligencePipeline:
    """Complete threat intelligence pipeline."""

    def __init__(self):
        self.api = ThreatIntelligenceAPI()
        self.correlator = ThreatCorrelationEngine()
        self.validator = ThreatValidation()

    def process_threat(self, threat: Dict) -> Dict:
        """Process threat through intelligence pipeline."""
        # Validate threat
        validation = self.validator.validate_threat(threat)

        if validation['is_false_positive']:
            return {
                'threat': threat,
                'validation': validation,
                'enrichment': None,
                'action': 'ignore'
            }

        # Enrich with intelligence
        enrichment = self.api.enrich_threat(threat)

        # Add to history for correlation
        self.correlator.add_threat(threat)

        # Check for correlations
        related = self.correlator.find_related_threats(threat)
        correlation = self.correlator.correlate_threats(related)

        return {
            'threat': threat,
            'validation': validation,
            'enrichment': enrichment,
            'correlation': correlation,
            'action': 'escalate' if correlation['correlation_found'] else 'notify',
            'processed_at': datetime.utcnow().isoformat()
        }
