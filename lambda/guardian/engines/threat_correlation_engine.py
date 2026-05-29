"""Threat Correlation Engine for intelligent threat grouping and pattern detection."""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta, timezone
import uuid


class ThreatCorrelationEngine:
    """Engine for correlating threats and detecting attack patterns."""

    def __init__(self, threat_service=None, audit_logger=None):
        """Initialize threat correlation engine."""
        self.threat_service = threat_service
        self.audit = audit_logger
        self.correlation_groups = []
        self.detected_patterns = []

    def correlate_threats_by_type(self, threats: List[Dict]) -> List[Dict]:
        """Group threats by type and severity."""
        groups = {}

        for threat in threats:
            threat_type = threat.get('threat_type', 'unknown')
            if threat_type not in groups:
                groups[threat_type] = {
                    'threat_type': threat_type,
                    'threats': [],
                    'count': 0,
                    'max_severity': 0,
                    'min_severity': 10,
                    'threat_ids': []
                }

            groups[threat_type]['threats'].append(threat)
            groups[threat_type]['count'] += 1
            groups[threat_type]['threat_ids'].append(threat.get('threat_id'))
            severity = threat.get('severity', 5)
            groups[threat_type]['max_severity'] = max(groups[threat_type]['max_severity'], severity)
            groups[threat_type]['min_severity'] = min(groups[threat_type]['min_severity'], severity)

        return list(groups.values())

    def detect_attack_chains(self, threats: List[Dict], time_window_minutes=60) -> List[Dict]:
        """Detect sequential attack patterns (kill chain)."""
        chains = []

        threats_sorted = sorted(
            threats,
            key=lambda t: t.get('detected_at', datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        )

        window_start = None
        chain_threats = []

        for threat in threats_sorted:
            detected_at = threat.get('detected_at')
            if isinstance(detected_at, str):
                detected_at = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))

            if window_start is None:
                window_start = detected_at
                chain_threats = [threat]
            elif (detected_at - window_start).total_seconds() <= time_window_minutes * 60:
                chain_threats.append(threat)
            else:
                if len(chain_threats) > 1:
                    chains.append({
                        'chain_id': str(uuid.uuid4()),
                        'threats': chain_threats,
                        'count': len(chain_threats),
                        'span_minutes': time_window_minutes,
                        'progression': self._calculate_kill_chain_progression(chain_threats)
                    })
                window_start = detected_at
                chain_threats = [threat]

        if len(chain_threats) > 1:
            chains.append({
                'chain_id': str(uuid.uuid4()),
                'threats': chain_threats,
                'count': len(chain_threats),
                'span_minutes': time_window_minutes,
                'progression': self._calculate_kill_chain_progression(chain_threats)
            })

        return chains

    def cluster_threats(self, threats: List[Dict], similarity_threshold=0.7) -> List[Dict]:
        """ML-based clustering: group similar threats together."""
        if not threats:
            return []

        clusters = []
        clustered = set()

        for i, threat1 in enumerate(threats):
            if i in clustered:
                continue

            cluster = [threat1]
            clustered.add(i)

            for j, threat2 in enumerate(threats[i+1:], start=i+1):
                if j in clustered:
                    continue

                similarity = self.calculate_threat_similarity(threat1, threat2)
                if similarity >= similarity_threshold:
                    cluster.append(threat2)
                    clustered.add(j)

            if cluster:
                clusters.append({
                    'cluster_id': str(uuid.uuid4()),
                    'threats': cluster,
                    'count': len(cluster),
                    'avg_similarity': sum(
                        self.calculate_threat_similarity(threat1, threat2)
                        for threat1 in cluster
                        for threat2 in cluster
                        if threat1.get('threat_id') != threat2.get('threat_id')
                    ) / max(1, len(cluster) * (len(cluster) - 1)),
                    'centroid_threat_type': cluster[0].get('threat_type'),
                    'centroid_severity': sum(t.get('severity', 5) for t in cluster) / len(cluster)
                })

        return clusters

    def calculate_threat_similarity(self, threat1: Dict, threat2: Dict) -> float:
        """
        Calculate similarity between two threats (0-1).
        Factors: threat_type, severity, account_id, timeframe, evidence patterns
        """
        score = 0.0
        weights = {
            'threat_type': 0.4,
            'severity': 0.2,
            'account': 0.15,
            'evidence': 0.15,
            'time': 0.1
        }

        # Threat type similarity (40%)
        if threat1.get('threat_type') == threat2.get('threat_type'):
            score += weights['threat_type']

        # Severity similarity (20%)
        sev1 = threat1.get('severity', 5)
        sev2 = threat2.get('severity', 5)
        severity_diff = abs(sev1 - sev2) / 10.0
        score += weights['severity'] * (1.0 - severity_diff)

        # Account similarity (15%)
        if threat1.get('account_id') == threat2.get('account_id'):
            score += weights['account']

        # Evidence pattern similarity (15%)
        evidence1 = set(threat1.get('evidence', []))
        evidence2 = set(threat2.get('evidence', []))
        if evidence1 or evidence2:
            intersection = len(evidence1 & evidence2)
            union = len(evidence1 | evidence2)
            if union > 0:
                score += weights['evidence'] * (intersection / union)

        # Time similarity (10%) - within 1 hour
        time1 = threat1.get('detected_at')
        time2 = threat2.get('detected_at')
        if time1 and time2:
            if isinstance(time1, str):
                time1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
            if isinstance(time2, str):
                time2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
            time_diff = abs((time1 - time2).total_seconds())
            if time_diff <= 3600:
                score += weights['time'] * (1.0 - (time_diff / 3600.0))

        return min(1.0, score)

    def identify_attack_patterns(self, threats: List[Dict]) -> List[Dict]:
        """Identify known attack patterns (ATT&CK framework)."""
        patterns = []
        threat_types = [t.get('threat_type') for t in threats]

        # Pattern: Lateral movement (multiple threat types across accounts)
        accounts = set(t.get('account_id') for t in threats)
        lateral_movement_types = {'Lateral Movement', 'Credential Compromise', 'Unauthorized Access'}
        matching_types = [t for t in threat_types if t in lateral_movement_types]

        if len(accounts) > 1 and len(matching_types) >= 2:
            patterns.append({
                'pattern_name': 'Lateral Movement Attack',
                'framework': 'MITRE ATT&CK',
                'tactic': 'Lateral Movement',
                'confidence': 0.85,
                'matching_threats': [t.get('threat_id') for t in threats if t.get('threat_type') in lateral_movement_types]
            })

        # Pattern: Privilege escalation
        escalation_types = {'Unauthorized Access', 'IAM Role Abuse', 'Privilege Escalation'}
        if any(t in escalation_types for t in threat_types):
            patterns.append({
                'pattern_name': 'Privilege Escalation Attack',
                'framework': 'MITRE ATT&CK',
                'tactic': 'Privilege Escalation',
                'confidence': 0.75,
                'matching_threats': [t.get('threat_id') for t in threats if t.get('threat_type') in escalation_types]
            })

        # Pattern: Data exfiltration
        exfil_types = {'Public Bucket', 'Unauthorized S3 Access', 'Data Export'}
        high_severity = [t for t in threats if t.get('severity', 0) >= 8]
        if any(t.get('threat_type') in exfil_types for t in high_severity):
            patterns.append({
                'pattern_name': 'Data Exfiltration Attack',
                'framework': 'MITRE ATT&CK',
                'tactic': 'Exfiltration',
                'confidence': 0.80,
                'matching_threats': [t.get('threat_id') for t in threats if t.get('threat_type') in exfil_types]
            })

        self.detected_patterns.extend(patterns)
        return patterns

    def get_correlation_summary(self) -> Dict:
        """Get summary of all correlation groups."""
        return {
            'total_correlation_groups': len(self.correlation_groups),
            'total_patterns_detected': len(self.detected_patterns),
            'correlation_groups': self.correlation_groups,
            'detected_patterns': self.detected_patterns
        }

    def _calculate_kill_chain_progression(self, threats: List[Dict]) -> Dict:
        """Calculate kill chain progression stages."""
        stages = {
            'reconnaissance': [],
            'exploitation': [],
            'persistence': [],
            'privilege_escalation': [],
            'lateral_movement': [],
            'exfiltration': []
        }

        threat_type_mapping = {
            'Reconnaissance': 'reconnaissance',
            'Unauthorized Access': 'exploitation',
            'Persistence': 'persistence',
            'Privilege Escalation': 'privilege_escalation',
            'Lateral Movement': 'lateral_movement',
            'Public Bucket': 'exfiltration',
            'Data Export': 'exfiltration'
        }

        for threat in threats:
            threat_type = threat.get('threat_type', '')
            for key, stage in threat_type_mapping.items():
                if key in threat_type:
                    stages[stage].append(threat.get('threat_id'))
                    break

        return {
            'stages': stages,
            'max_stage': max((k for k, v in stages.items() if v), default='unknown'),
            'stage_count': sum(1 for v in stages.values() if v)
        }
