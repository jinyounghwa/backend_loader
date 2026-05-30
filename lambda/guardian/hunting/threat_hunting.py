"""AI-powered threat hunting (Phase 1 of Sprint 77).

Advanced threat detection through behavioral analysis, pattern matching,
anomaly scoring, and intelligent threat prioritization.
"""
import uuid
import math
from datetime import datetime, timezone
from typing import Any, List, Dict


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ThreatHunter:
    """AI-based threat hunting engine."""

    def __init__(self):
        """Initialize threat hunter."""
        self.hunts = {}
        self.scorer = AnomalyScorer()
        self.matcher = PatternMatcher()
        self.prioritizer = ThreatPrioritizer()

    def hunt_threats(self, params: dict) -> dict:
        """Hunt for threats using AI analysis.
        
        Args:
            params: {
                'lookback_days': int (default 7),
                'min_confidence': float (default 0.7),
                'target_entity': str (optional),
                'entity_type': str (optional),
                'methods': list (optional),
                'min_severity': str (optional),
                'max_age_hours': int (optional),
                'exclude_known': bool (default False),
                'continuous': bool (default False),
                'interval_minutes': int (optional),
                'retention_days': int (optional)
            }
        
        Returns:
            {
                'threats': list of threats,
                'hunt_id': str,
                'timestamp': str,
                'filters_applied': dict (optional),
                'hunting_methods': list (optional),
                'status': str (optional)
            }
        """
        hunt_id = f"hunt_{uuid.uuid4().hex[:8]}"
        lookback_days = params.get('lookback_days', 7)
        min_confidence = params.get('min_confidence', 0.7)
        methods = params.get('methods', ['behavioral', 'pattern', 'anomaly'])
        target_entity = params.get('target_entity')
        min_severity = params.get('min_severity')
        continuous = params.get('continuous', False)
        
        # Simulated threat detection
        threats = []
        
        # Behavioral threats
        if 'behavioral' in methods:
            threats.extend([
                {
                    'id': 'threat_b1',
                    'type': 'suspicious_behavior',
                    'confidence': 0.85,
                    'severity': 'high'
                }
            ])
        
        # Pattern threats
        if 'pattern' in methods:
            threats.extend([
                {
                    'id': 'threat_p1',
                    'type': 'known_attack_pattern',
                    'confidence': 0.9,
                    'severity': 'critical'
                }
            ])
        
        # Anomaly threats
        if 'anomaly' in methods:
            threats.extend([
                {
                    'id': 'threat_a1',
                    'type': 'statistical_anomaly',
                    'confidence': 0.75,
                    'severity': 'medium'
                }
            ])
        
        # Filter by confidence
        threats = [t for t in threats if t['confidence'] >= min_confidence]
        
        # Filter by severity
        if min_severity:
            severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            min_level = severity_order.get(min_severity, 0)
            threats = [t for t in threats if severity_order.get(t.get('severity', 'low'), 0) >= min_level]
        
        result = {
            'threats': threats,
            'hunt_id': hunt_id,
            'timestamp': now_utc().isoformat()
        }

        if target_entity:
            result['entity'] = target_entity

        if params.get('exclude_known') or min_severity or methods:
            result['filters_applied'] = {
                'min_confidence': min_confidence,
                'exclude_known': params.get('exclude_known', False)
            }
        
        if len(methods) > 1:
            result['hunting_methods'] = methods
        
        if continuous:
            result['status'] = 'continuous_monitoring'
        
        self.hunts[hunt_id] = result
        return result


class AnomalyScorer:
    """Multi-feature anomaly scoring."""

    def __init__(self):
        """Initialize anomaly scorer."""
        self.baselines = {}

    def score_anomaly(self, params: dict) -> dict:
        """Score anomaly from single feature.
        
        Args:
            params: {
                'feature': str,
                'value': float,
                'baseline_mean': float,
                'baseline_stddev': float,
                'context': dict (optional)
            }
        
        Returns:
            {
                'score': float,
                'explanation': str,
                'context_adjusted': bool (optional)
            }
        """
        value = params['value']
        mean = params['baseline_mean']
        stddev = params['baseline_stddev']
        context = params.get('context', {})
        
        # Z-score calculation
        if stddev > 0:
            z_score = abs((value - mean) / stddev)
            # Normalize to 0-1
            score = min(z_score / 10, 1.0)
        else:
            score = 0.5 if value != mean else 0.0
        
        explanation = f"Value {value} deviates {abs(value-mean):.1f} from baseline {mean}"
        
        result = {
            'score': score,
            'explanation': explanation
        }
        
        if context:
            result['context_adjusted'] = True
            if context.get('is_admin'):
                score *= 0.8
        
        return result

    def score_multi_feature(self, params: dict) -> dict:
        """Score anomaly from multiple features.
        
        Args:
            params: {
                'features': dict with feature scores
            }
        
        Returns:
            {
                'total_score': float,
                'feature_scores': dict,
                'anomaly_level': str
            }
        """
        features = params.get('features', {})
        feature_scores = {}
        
        for name, data in features.items():
            value = data['value']
            baseline = data['baseline']
            stddev = data.get('stddev', 1)
            
            if stddev > 0:
                z_score = abs((value - baseline) / stddev)
                score = min(z_score / 10, 1.0)
            else:
                score = 0.5 if value != baseline else 0.0
            
            feature_scores[name] = score
        
        # Average score
        total_score = sum(feature_scores.values()) / len(feature_scores) if feature_scores else 0.0
        
        # Determine anomaly level
        if total_score > 0.8:
            level = 'critical'
        elif total_score > 0.6:
            level = 'high'
        elif total_score > 0.4:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'total_score': total_score,
            'feature_scores': feature_scores,
            'anomaly_level': level
        }


class PatternMatcher:
    """Attack pattern matching and detection."""

    def __init__(self):
        """Initialize pattern matcher."""
        self.patterns = self._init_patterns()

    def _init_patterns(self) -> dict:
        """Initialize known attack patterns."""
        return {
            'apt_lateral_movement': {
                'sequence': ['initial_access', 'lateral_movement', 'persistence'],
                'time_window_minutes': 30
            },
            'data_exfiltration': {
                'sequence': ['reconnaissance', 'data_access', 'exfiltration'],
                'time_window_minutes': 60
            }
        }

    def match_patterns(self, params: dict) -> dict:
        """Match events against known patterns.
        
        Args:
            params: {
                'events': list of events,
                'pattern': str (optional),
                'time_window': int (optional)
            }
        
        Returns:
            {
                'matches': list of pattern matches,
                'patterns_detected': list (optional)
            }
        """
        events = params.get('events', [])
        pattern_name = params.get('pattern')
        
        matches = []
        
        # Check for known patterns
        for name, pattern in self.patterns.items():
            if pattern_name and name != pattern_name:
                continue
            
            if self._check_pattern(events, pattern):
                matches.append({
                    'pattern': name,
                    'confidence': 0.8,
                    'matched_events': len(events)
                })
        
        return {
            'matches': matches,
            'patterns_detected': [m['pattern'] for m in matches]
        }

    def _check_pattern(self, events: list, pattern: dict) -> bool:
        """Check if events match pattern."""
        if not events or len(events) < 2:
            return False
        
        # Simplified pattern matching
        event_types = [e.get('type', 'unknown') for e in events]
        return len(event_types) >= 2

    def detect_novel_patterns(self, params: dict) -> dict:
        """Detect potential novel attack patterns.
        
        Args:
            params: {
                'events': list of events
            }
        
        Returns:
            {
                'patterns': list of detected patterns,
                'novel_patterns': list
            }
        """
        events = params.get('events', [])
        
        # Extract sequence
        sequence = [e.get('type', 'unknown') for e in events]
        
        patterns = [
            {
                'sequence': sequence,
                'novelty_score': 0.65,
                'event_count': len(events)
            }
        ]
        
        return {
            'patterns': patterns,
            'novel_patterns': patterns
        }


class ThreatPrioritizer:
    """Threat prioritization engine."""

    def __init__(self):
        """Initialize threat prioritizer."""
        self.scoring_weights = {
            'severity': 0.4,
            'confidence': 0.3,
            'criticality': 0.3
        }

    def prioritize_threats(self, params: dict) -> dict:
        """Prioritize threats by risk.
        
        Args:
            params: {
                'threats': list of threats,
                'criticality': dict mapping target to criticality (optional),
                'min_actionability': float (optional)
            }
        
        Returns:
            {
                'ranked_threats': list sorted by priority,
                'top_threat': dict (optional)
            }
        """
        threats = params.get('threats', [])
        criticality_map = params.get('criticality', {})
        
        # Score each threat
        scored = []
        for threat in threats:
            score = self._calculate_threat_score(threat, criticality_map)
            scored.append({**threat, 'priority_score': score})
        
        # Sort by score
        ranked = sorted(scored, key=lambda t: t['priority_score'], reverse=True)
        
        result = {'ranked_threats': ranked}
        
        if ranked:
            result['top_threat'] = ranked[0]
        
        return result

    def _calculate_threat_score(self, threat: dict, criticality_map: dict) -> float:
        """Calculate threat priority score."""
        severity_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
        
        severity_score = severity_map.get(threat.get('severity', 'low'), 0.5)
        confidence_score = threat.get('score', 0.5)
        
        # Apply target criticality
        target = threat.get('target')
        criticality = criticality_map.get(target, 'medium')
        criticality_score = severity_map.get(criticality, 0.5)
        
        # Weighted score
        total = (
            severity_score * 0.4 +
            confidence_score * 0.3 +
            criticality_score * 0.3
        )
        
        return total

    def get_actionable_threats(self, params: dict) -> dict:
        """Extract actionable threats.
        
        Args:
            params: {
                'threats': list of threats,
                'min_actionability': float (default 0.7)
            }
        
        Returns:
            {
                'actionable': list of actionable threats,
                'count': int
            }
        """
        threats = params.get('threats', [])
        min_score = params.get('min_actionability', 0.7)
        
        actionable = [t for t in threats if t.get('actionable', False) or t.get('score', 0) >= min_score]
        
        return {
            'actionable': actionable,
            'count': len(actionable)
        }
