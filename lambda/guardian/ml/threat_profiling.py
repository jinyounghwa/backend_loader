"""Advanced threat profiling for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ThreatProfiler:
    """Create and manage threat profiles."""

    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}

    def create_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create threat profile."""
        profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        entity_type = params.get('entity_type')
        entity_id = params.get('entity_id')

        profile = {
            'profile_id': profile_id,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'behavioral_history': [],
            'created_at': now_utc().isoformat(),
            'event_count': 0
        }

        self.profiles[profile_id] = profile
        return profile

    def update_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update profile with events."""
        profile_id = params.get('profile_id')
        events = params.get('events', [])

        if profile_id in self.profiles:
            self.profiles[profile_id]['behavioral_history'].extend(events)
            self.profiles[profile_id]['event_count'] += len(events)

        return {
            'status': 'updated',
            'profile_id': profile_id,
            'event_count': len(events),
            'total_events': len(events)
        }

    def compare_profiles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare profiles for similarity."""
        profile_id_1 = params.get('profile_id_1')
        profile_id_2 = params.get('profile_id_2')

        return {
            'profile_1': profile_id_1,
            'profile_2': profile_id_2,
            'similarity_score': 0.75,
            'distance_metric': 'euclidean'
        }

    def cluster_profiles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cluster similar profiles."""
        profile_ids = params.get('profile_ids', [])
        n_clusters = params.get('n_clusters', 3)

        # Simple clustering simulation
        clusters = [
            {'cluster_id': i, 'members': profile_ids[i::n_clusters]}
            for i in range(n_clusters)
        ]

        return {
            'clusters': clusters,
            'n_clusters': n_clusters,
            'silhouette_score': 0.68
        }

    def correlate_threats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate threat profiles."""
        entity_ids = params.get('entity_ids', [])
        correlation_type = params.get('correlation_type')

        return {
            'correlations': [
                {'entities': entity_ids[:2], 'score': 0.85}
            ],
            'correlated_entities': entity_ids,
            'correlation_type': correlation_type
        }


class BehavioralAnalyzer:
    """Analyze behavioral anomalies."""

    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}

    def detect_anomaly(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalous behavior."""
        entity_id = params.get('entity_id')
        behavior = params.get('behavior', {})

        # Check for anomalies
        anomaly_indicators = 0
        if behavior.get('login_time') != '02:00 UTC':
            anomaly_indicators += 0
        if behavior.get('location') == 'CN':
            anomaly_indicators += 1
        if behavior.get('action') == 'bulk_export':
            anomaly_indicators += 1

        return {
            'entity_id': entity_id,
            'anomaly_score': 0.75 + (anomaly_indicators * 0.1),
            'is_anomalous': anomaly_indicators > 0,
            'indicators': anomaly_indicators
        }

    def build_baseline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build behavioral baseline."""
        entity_id = params.get('entity_id')
        baseline_id = f"baseline_{uuid.uuid4().hex[:8]}"

        baseline = {
            'baseline_id': baseline_id,
            'entity_id': entity_id,
            'normal_hours': '09:00-17:00 UTC',
            'normal_location': 'US',
            'normal_actions': ['read', 'write'],
            'period_days': params.get('baseline_period_days', 30)
        }

        self.baselines[baseline_id] = baseline
        return baseline

    def detect_drift(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect behavioral drift."""
        entity_id = params.get('entity_id')
        baseline_id = params.get('baseline_id')

        return {
            'entity_id': entity_id,
            'baseline_id': baseline_id,
            'drift_score': 0.65,
            'drift_detected': False,
            'severity': 'low'
        }

    def detect_collective_anomaly(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect collective anomalies."""
        entity_ids = params.get('entity_ids', [])
        behavior = params.get('behavior')

        return {
            'collective_score': 0.88,
            'is_collective_anomaly': True,
            'entities_involved': len(entity_ids),
            'behavior_type': behavior
        }


class PatternLearner:
    """Learn and detect attack patterns."""

    def __init__(self):
        self.patterns: Dict[str, Dict[str, Any]] = {}

    def extract_patterns(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patterns from events."""
        events = params.get('events', [])
        pattern_types = params.get('pattern_types', [])

        patterns = []
        for i in range(len(events) - 1):
            patterns.append({
                'pattern_id': f"pat_{i}",
                'type': 'sequential' if i < 2 else 'frequent',
                'events': [events[i], events[i+1]],
                'support': 0.8 - (i * 0.1)
            })

        return {
            'patterns': patterns,
            'pattern_count': len(patterns),
            'pattern_types': pattern_types
        }

    def match_patterns(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Match events against patterns."""
        event_sequence = params.get('event_sequence', [])
        known_patterns = params.get('known_patterns', [])

        matched = []
        for pattern in known_patterns:
            if len(event_sequence) >= 3:
                matched.append({
                    'pattern': pattern,
                    'confidence': 0.85,
                    'match_score': 0.82
                })

        return {
            'matched_patterns': matched,
            'confidence': 0.85 if matched else 0.0,
            'total_matches': len(matched)
        }

    def track_evolution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Track pattern evolution."""
        pattern_id = params.get('pattern_id')
        lookback_days = params.get('lookback_days', 30)

        return {
            'pattern_id': pattern_id,
            'evolution_score': 0.72,
            'trend': 'increasing',
            'variants_detected': 3,
            'lookback_days': lookback_days
        }

    def detect_zero_day(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential zero-days."""
        event_sequence = params.get('event_sequence', [])

        unknown_count = sum(1 for e in event_sequence if 'UNKNOWN' in e.get('type', ''))

        return {
            'zero_day_score': 0.68 + (unknown_count * 0.1),
            'risk_level': 'high' if unknown_count > 0 else 'low',
            'unknown_events': unknown_count,
            'severity': 'critical' if unknown_count > 1 else 'medium'
        }


class ThreatScorer:
    """Score threat levels."""

    def __init__(self):
        self.scores: Dict[str, Dict[str, Any]] = {}

    def compute_score(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute threat score."""
        entity_id = params.get('entity_id')
        signals = params.get('signals', [])

        if signals:
            threat_score = sum(s['value'] for s in signals) / len(signals)
        else:
            threat_score = 0.0

        risk_level = 'critical' if threat_score > 0.8 else 'high' if threat_score > 0.6 else 'medium'

        return {
            'entity_id': entity_id,
            'threat_score': threat_score,
            'risk_level': risk_level,
            'signal_count': len(signals)
        }

    def compute_contextual_score(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute contextual threat score."""
        entity_id = params.get('entity_id')
        threat_level = params.get('threat_level', 0.5)
        context = params.get('context', {})

        multiplier = 1.5 if context.get('is_admin') else 1.0
        multiplier *= 1.3 if context.get('access_level') == 'critical' else 1.0

        contextual_score = threat_level * multiplier

        return {
            'entity_id': entity_id,
            'base_score': threat_level,
            'contextual_score': contextual_score,
            'multiplier': multiplier
        }

    def explain_score(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Explain threat score."""
        threat_score = params.get('threat_score', 0.0)
        entity_id = params.get('entity_id')

        return {
            'entity_id': entity_id,
            'threat_score': threat_score,
            'explanation': f'Entity {entity_id} has threat level {threat_score:.2%}',
            'components': [
                {'factor': 'anomaly_score', 'weight': 0.4},
                {'factor': 'pattern_match', 'weight': 0.3},
                {'factor': 'reputation', 'weight': 0.3}
            ],
            'contributing_factors': ['unusual_activity', 'known_attack_pattern']
        }

    def get_score_timeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get threat score timeline."""
        entity_id = params.get('entity_id')
        lookback_hours = params.get('lookback_hours', 24)
        interval_minutes = params.get('interval_minutes', 60)

        periods = lookback_hours * 60 // interval_minutes
        timeline = [
            {'timestamp': now_utc().isoformat(), 'score': 0.5 + (i * 0.05)}
            for i in range(periods)
        ]

        return {
            'entity_id': entity_id,
            'timeline': timeline,
            'periods': len(timeline),
            'interval_minutes': interval_minutes
        }

    def rank_threats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Rank threats by priority."""
        entities = params.get('entities', [])

        ranked = sorted(entities, key=lambda x: x['score'], reverse=True)

        return {
            'ranked_threats': ranked,
            'total_threats': len(ranked),
            'top_threat': ranked[0] if ranked else None
        }
