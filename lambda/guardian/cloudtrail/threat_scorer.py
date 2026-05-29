"""Threat scoring engine for CloudTrail anomalies."""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ThreatScorer:
    """Calculate threat severity scores for detected anomalies."""

    def __init__(self):
        """Initialize threat scorer."""
        self.pattern_weights = {
            'unauthorized_region': 7,
            'mass_deletion': 9,
            'permission_escalation': 8,
            'auth_anomaly': 6,
            'cost_spike_trigger': 5,
            'suspicious_api_pattern': 4,
        }

    def calculate_threat_score(
        self, pattern_detections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall threat score from detections.
        
        Args:
            pattern_detections: List of pattern detections
            
        Returns:
            Threat score details
        """
        if not pattern_detections:
            return {
                'score': 0,
                'severity': 'LOW',
                'details': 'No threats detected',
            }
        
        total_score = 0
        max_score = 0
        weighted_count = 0
        
        for detection in pattern_detections:
            pattern = detection.get('pattern')
            weight = self.pattern_weights.get(pattern, 5)
            
            # Weight multiplied by detection count
            score = weight * 10
            total_score += score
            max_score = max(max_score, score)
            weighted_count += 1
        
        # Normalize to 0-100 scale
        avg_score = total_score / len(pattern_detections) if pattern_detections else 0
        normalized_score = min(int(avg_score), 100)
        
        if normalized_score >= 80:
            severity = 'CRITICAL'
        elif normalized_score >= 60:
            severity = 'HIGH'
        elif normalized_score >= 40:
            severity = 'MEDIUM'
        elif normalized_score >= 20:
            severity = 'LOW'
        else:
            severity = 'INFO'
        
        return {
            'score': normalized_score,
            'severity': severity,
            'max_pattern_score': max_score,
            'pattern_count': len(pattern_detections),
            'weighted_count': weighted_count,
        }

    def score_event(self, event: Dict[str, Any]) -> int:
        """Score individual event for threat level.
        
        Args:
            event: CloudTrail event
            
        Returns:
            Threat score (0-100)
        """
        score = 0
        
        # Check for failed operations
        if event.get('error_code'):
            score += 10
        
        # Check for IAM operations
        if event.get('event_source') == 'iam.amazonaws.com':
            score += 15
        
        # Check for deletion operations
        if 'Delete' in event.get('event_name', ''):
            score += 20
        
        # Check for unusual source IPs (simplified)
        source_ip = event.get('source_ip', '')
        if not source_ip.startswith(('10.', '172.', '192.')):
            score += 5
        
        return min(score, 100)

    def categorize_threat(
        self, score: int
    ) -> Dict[str, Any]:
        """Categorize threat based on score.
        
        Args:
            score: Threat score (0-100)
            
        Returns:
            Threat categorization
        """
        if score >= 80:
            return {
                'level': 'CRITICAL',
                'action': 'BLOCK_AND_ALERT',
                'confidence': 'HIGH',
            }
        elif score >= 60:
            return {
                'level': 'HIGH',
                'action': 'ALERT',
                'confidence': 'HIGH',
            }
        elif score >= 40:
            return {
                'level': 'MEDIUM',
                'action': 'NOTIFY',
                'confidence': 'MEDIUM',
            }
        elif score >= 20:
            return {
                'level': 'LOW',
                'action': 'LOG',
                'confidence': 'MEDIUM',
            }
        else:
            return {
                'level': 'INFO',
                'action': 'RECORD',
                'confidence': 'LOW',
            }
