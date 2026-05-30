"""GuardDuty integration and threat correlation."""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json


class GuardDutyEventCollector:
    """Collect and normalize GuardDuty findings."""

    THREAT_TYPE_MAPPING = {
        'Recon': 'RECON',
        'UnauthorizedAccess': 'UNAUTHORIZED_ACCESS',
        'CryptoCurrency': 'MALWARE',
        'Trojan': 'MALWARE',
        'PenTest': 'PEN_TEST',
        'Persistence': 'PERSISTENCE',
    }

    def collect(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Collect and normalize a GuardDuty finding."""
        finding_id = finding.get('Id', '')
        finding_type = finding.get('Type', '')
        severity = finding.get('Severity', 0)
        updated_at = finding.get('UpdatedAt')

        # Extract threat type from finding type
        threat_type = self._extract_threat_type(finding_type)

        # Extract resource ID
        resource_id = self._extract_resource_id(finding)

        return {
            'finding_id': finding_id,
            'finding_type': finding_type,
            'threat_type': threat_type,
            'severity_score': severity,
            'resource_id': resource_id,
            'timestamp': updated_at,
            'raw_finding': finding
        }

    def _extract_threat_type(self, finding_type: str) -> str:
        """Extract threat type from GuardDuty finding type."""
        for prefix, threat_type in self.THREAT_TYPE_MAPPING.items():
            if prefix in finding_type:
                return threat_type
        return 'UNKNOWN'

    def _extract_resource_id(self, finding: Dict[str, Any]) -> Optional[str]:
        """Extract resource ID from finding."""
        # Check for EC2 instance
        instance_id = finding.get('Resource', {}).get('InstanceDetails', {}).get('InstanceId')
        if instance_id:
            return instance_id

        # Check for IAM user
        principal_id = finding.get('Principal', {}).get('AWSAccountId')
        if principal_id:
            return principal_id

        # Check for other resources
        return None


class ThreatSeverityClassifier:
    """Classify threat severity."""

    def classify(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Classify finding severity."""
        severity = finding.get('Severity', 0)
        finding_type = finding.get('Type', '')

        if severity >= 7.0:
            level = 'CRITICAL'
            risk_score = min(100, 80 + (severity - 7.0) * 5)
        elif severity >= 5.0:
            level = 'HIGH'
            risk_score = min(80, 60 + (severity - 5.0) * 10)
        elif severity >= 3.0:
            level = 'MEDIUM'
            risk_score = min(60, 40 + (severity - 3.0) * 10)
        else:
            level = 'LOW'
            risk_score = min(40, severity * 13)

        return {
            'severity_level': level,
            'severity_score': severity,
            'risk_score': risk_score,
            'finding_type': finding_type
        }


class ThreatCorrelationEngine:
    """Correlate multiple threat signals."""

    def correlate(self, cloudtrail_signals: List[Dict[str, Any]],
                  guardduty_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate CloudTrail and GuardDuty signals."""
        if not cloudtrail_signals or not guardduty_signals:
            return {
                'is_correlated': False,
                'correlation_score': 0,
                'result_type': 'INDEPENDENT'
            }

        # Look for matching IPs and time windows
        correlation_score = 0

        for ct_signal in cloudtrail_signals:
            ct_ip = ct_signal.get('sourceIPAddress')
            ct_time = self._parse_timestamp(ct_signal.get('timestamp'))

            for gd_signal in guardduty_signals:
                gd_ip = gd_signal.get('SourceIP')
                gd_time = self._parse_timestamp(gd_signal.get('Timestamp'))

                # Check if IPs match
                if ct_ip and gd_ip and ct_ip == gd_ip:
                    # Check time proximity (within 10 minutes)
                    if ct_time and gd_time:
                        time_diff = abs((ct_time - gd_time).total_seconds())
                        if time_diff < 600:  # 10 minutes
                            correlation_score = 85

        is_correlated = correlation_score > 70

        return {
            'is_correlated': is_correlated,
            'correlation_score': correlation_score,
            'result_type': 'CAMPAIGN' if is_correlated else 'INDEPENDENT'
        }

    def correlate_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate multiple signals of same type."""
        if len(signals) < 2:
            return {'is_campaign': False, 'affected_resources': 1}

        # Extract threat types and resources
        threat_types = set()
        resources = set()
        times = []

        for signal in signals:
            threat_types.add(signal.get('Type'))
            resource = signal.get('Resource', {}).get('InstanceDetails', {}).get('InstanceId')
            if resource:
                resources.add(resource)

            ts = self._parse_timestamp(signal.get('Timestamp'))
            if ts:
                times.append(ts)

        # If same threat type on multiple resources within short timeframe
        is_campaign = False
        if len(threat_types) == 1 and len(resources) > 2:
            if times:
                time_span = (max(times) - min(times)).total_seconds()
                if time_span < 3600:  # Within 1 hour
                    is_campaign = True

        return {
            'is_campaign': is_campaign,
            'affected_resources': len(resources),
            'threat_types': list(threat_types),
            'signal_count': len(signals)
        }

    def detect_attack_pattern(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect multi-stage attack patterns."""
        if not signals:
            return {'is_attack': False}

        signal_types = [s.get('signal_type') for s in signals]

        # Privilege escalation pattern: IAM + Unauthorized + Exfiltration
        if (any('IAM' in t for t in signal_types) and
            any('UNAUTHORIZED' in t for t in signal_types) and
            any('EXFILTRATION' in t for t in signal_types)):
            return {
                'is_attack': True,
                'attack_pattern': 'privilege_escalation',
                'stages': len(signal_types),
                'confidence': 0.95
            }

        # Recon + lateral movement
        if any('RECON' in t for t in signal_types) and any('MOVEMENT' in t for t in signal_types):
            return {
                'is_attack': True,
                'attack_pattern': 'lateral_movement',
                'stages': len(signal_types),
                'confidence': 0.85
            }

        # General multi-stage attack
        if len(signal_types) >= 3:
            return {
                'is_attack': True,
                'attack_pattern': 'multi_stage_attack',
                'stages': len(signal_types),
                'confidence': 0.75
            }

        return {'is_attack': False}

    def _parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None
