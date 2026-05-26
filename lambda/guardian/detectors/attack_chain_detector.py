"""Attack Chain Detector for multi-stage attack progression analysis."""

from typing import List, Dict
from datetime import datetime
import uuid


class AttackChainDetector:
    """Detects multi-stage attack patterns and kill chain progression."""

    def __init__(self, audit_logger=None):
        """Initialize attack chain detector."""
        self.audit = audit_logger
        self.detected_chains = []

    def detect_kill_chain(self, threats: List[Dict], time_window_minutes=60) -> List[Dict]:
        """
        Detect multi-stage attack patterns:
        1. Reconnaissance → 2. Exploitation → 3. Persistence →
        4. Privilege Escalation → 5. Lateral Movement → 6. Data Exfiltration
        """
        chains = []
        threat_types = [t.get('threat_type', '') for t in threats]

        # Map threat types to kill chain stages
        stage_mappings = {
            'reconnaissance': ['Reconnaissance', 'Scanning', 'Probing'],
            'exploitation': ['Unauthorized Access', 'Exploitation', 'Vulnerability'],
            'persistence': ['Persistence', 'Backdoor', 'Malware'],
            'privilege_escalation': ['Privilege Escalation', 'IAM Role Abuse'],
            'lateral_movement': ['Lateral Movement', 'Credential Compromise', 'Cross-Account Access'],
            'exfiltration': ['Data Exfiltration', 'Public Bucket', 'Data Export', 'Unauthorized S3 Access']
        }

        detected_stages = {}
        for stage, keywords in stage_mappings.items():
            matching_threats = [t for t in threats if any(kw in t.get('threat_type', '') for kw in keywords)]
            if matching_threats:
                detected_stages[stage] = matching_threats

        if detected_stages:
            chains.append({
                'chain_id': str(uuid.uuid4()),
                'detected_stages': list(detected_stages.keys()),
                'stage_details': detected_stages,
                'stage_count': len(detected_stages),
                'max_stage_index': self._get_max_stage_index(detected_stages),
                'total_threats_in_chain': sum(len(threats) for threats in detected_stages.values()),
                'progression': self._calculate_progression(detected_stages)
            })

        self.detected_chains.extend(chains)
        return chains

    def identify_reconnaissance_phase(self, threats: List[Dict]) -> List[Dict]:
        """Identify initial reconnaissance threats."""
        recon_keywords = ['Reconnaissance', 'Scanning', 'Probing', 'Port Scan', 'Service Enumeration']
        recon_threats = [
            t for t in threats
            if any(kw in t.get('threat_type', '') for kw in recon_keywords)
        ]
        return recon_threats

    def identify_exploitation_phase(self, threats: List[Dict]) -> List[Dict]:
        """Identify exploitation attempts."""
        exploit_keywords = ['Unauthorized Access', 'Exploitation', 'Vulnerability', 'Unauthorized Login', 'Failed Auth']
        exploit_threats = [
            t for t in threats
            if any(kw in t.get('threat_type', '') for kw in exploit_keywords)
        ]
        return exploit_threats

    def identify_lateral_movement(self, threats: List[Dict], account_ids: List[str]) -> List[Dict]:
        """Identify lateral movement across accounts."""
        lateral_keywords = ['Lateral Movement', 'Credential Compromise', 'Cross-Account', 'Cross-Account Access']
        lateral_threats = [
            t for t in threats
            if any(kw in t.get('threat_type', '') for kw in lateral_keywords)
        ]

        # Filter by multiple accounts (indicates cross-account movement)
        multi_account_threats = [
            t for t in lateral_threats
            if len(set(threat.get('account_id') for threat in [t] + threats)) > 1
        ]

        return multi_account_threats if multi_account_threats else lateral_threats

    def calculate_kill_chain_progression(self, threats: List[Dict]) -> Dict:
        """Determine how far attacker has progressed."""
        stages = [
            'reconnaissance',
            'exploitation',
            'persistence',
            'privilege_escalation',
            'lateral_movement',
            'exfiltration'
        ]

        stage_keywords = {
            'reconnaissance': ['Reconnaissance', 'Scanning', 'Probing'],
            'exploitation': ['Unauthorized Access', 'Exploitation', 'Vulnerability'],
            'persistence': ['Persistence', 'Backdoor', 'Malware'],
            'privilege_escalation': ['Privilege Escalation', 'IAM Role Abuse'],
            'lateral_movement': ['Lateral Movement', 'Credential Compromise'],
            'exfiltration': ['Data Exfiltration', 'Public Bucket', 'Data Export']
        }

        progression = []
        for stage in stages:
            keywords = stage_keywords[stage]
            stage_threats = [
                t for t in threats
                if any(kw in t.get('threat_type', '') for kw in keywords)
            ]
            if stage_threats:
                progression.append(stage)

        return {
            'current_stage': progression[-1] if progression else 'unknown',
            'stages_completed': progression,
            'stage_count': len(progression),
            'progression_percentage': (len(progression) / len(stages)) * 100,
            'threat_count_by_stage': {
                stage: len([
                    t for t in threats
                    if any(kw in t.get('threat_type', '') for kw in stage_keywords[stage])
                ])
                for stage in stages
            }
        }

    def estimate_compromise_probability(self, chain: Dict) -> float:
        """Estimate likelihood of successful compromise."""
        if not chain:
            return 0.0

        base_probability = 0.5
        stage_count = chain.get('stage_count', 0)
        max_stage_index = chain.get('max_stage_index', 0)

        # Increase probability based on progression through kill chain
        progression_boost = (max_stage_index / 5.0) * 0.3  # Max +0.3
        stage_boost = (stage_count / 6.0) * 0.2  # Max +0.2

        total_threats = chain.get('total_threats_in_chain', 1)
        threat_boost = min((total_threats / 10.0) * 0.1, 0.1)  # Max +0.1

        probability = min(base_probability + progression_boost + stage_boost + threat_boost, 0.95)

        return probability

    def _get_max_stage_index(self, detected_stages: Dict) -> int:
        """Get highest stage index in the kill chain."""
        stage_order = [
            'reconnaissance',
            'exploitation',
            'persistence',
            'privilege_escalation',
            'lateral_movement',
            'exfiltration'
        ]

        max_index = -1
        for stage in detected_stages.keys():
            if stage in stage_order:
                max_index = max(max_index, stage_order.index(stage))

        return max_index

    def _calculate_progression(self, detected_stages: Dict) -> str:
        """Calculate human-readable progression description."""
        stage_order = [
            'reconnaissance',
            'exploitation',
            'persistence',
            'privilege_escalation',
            'lateral_movement',
            'exfiltration'
        ]

        ordered_stages = []
        for stage in stage_order:
            if stage in detected_stages:
                ordered_stages.append(stage)

        if not ordered_stages:
            return 'Unknown progression'

        stage_descriptions = {
            'reconnaissance': 'Attacker gathering information',
            'exploitation': 'Attacker exploiting vulnerabilities',
            'persistence': 'Attacker establishing persistence',
            'privilege_escalation': 'Attacker escalating privileges',
            'lateral_movement': 'Attacker moving across systems',
            'exfiltration': 'Attacker exfiltrating data'
        }

        return ' → '.join(stage_descriptions.get(stage, stage) for stage in ordered_stages)
