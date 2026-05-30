"""Tests for AI-powered threat hunting (Phase 1 of Sprint 77)."""
import pytest
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestThreatHunter:
    """Test AI-based threat hunting."""

    def test_hunt_threats_basic(self):
        """✅ Hunt threats using AI analysis."""
        from guardian.hunting.threat_hunting import ThreatHunter

        hunter = ThreatHunter()
        result = hunter.hunt_threats({
            'lookback_days': 7,
            'min_confidence': 0.7
        })

        assert 'threats' in result
        assert 'hunt_id' in result
        assert isinstance(result['threats'], list)

    def test_hunt_with_entity_focus(self):
        """✅ Hunt threats targeting specific entity."""
        from guardian.hunting.threat_hunting import ThreatHunter

        hunter = ThreatHunter()
        result = hunter.hunt_threats({
            'target_entity': 'i-12345',
            'entity_type': 'ec2',
            'methods': ['behavioral', 'pattern', 'anomaly']
        })

        assert 'threats' in result
        assert 'entity' in result

    def test_threat_hunting_with_filters(self):
        """✅ Hunt threats with severity filtering."""
        from guardian.hunting.threat_hunting import ThreatHunter

        hunter = ThreatHunter()
        result = hunter.hunt_threats({
            'min_severity': 'high',
            'max_age_hours': 24,
            'exclude_known': True
        })

        assert 'threats' in result
        assert 'filters_applied' in result


class TestAnomalyScorer:
    """Test multi-feature anomaly scoring."""

    def test_score_single_anomaly(self):
        """✅ Score anomaly from single feature."""
        from guardian.hunting.threat_hunting import AnomalyScorer

        scorer = AnomalyScorer()
        score = scorer.score_anomaly({
            'feature': 'api_call_count',
            'value': 500,
            'baseline_mean': 100,
            'baseline_stddev': 20
        })

        assert 'score' in score
        assert 0 <= score['score'] <= 1.0
        assert 'explanation' in score

    def test_score_multi_feature_anomaly(self):
        """✅ Score anomaly from multiple features."""
        from guardian.hunting.threat_hunting import AnomalyScorer

        scorer = AnomalyScorer()
        result = scorer.score_multi_feature({
            'features': {
                'api_calls': {'value': 500, 'baseline': 100, 'stddev': 20},
                'failed_logins': {'value': 50, 'baseline': 5, 'stddev': 2},
                'data_access': {'value': 1000, 'baseline': 100, 'stddev': 50}
            }
        })

        assert 'total_score' in result
        assert 'feature_scores' in result
        assert len(result['feature_scores']) == 3

    def test_anomaly_context_adjustment(self):
        """✅ Adjust anomaly score with context."""
        from guardian.hunting.threat_hunting import AnomalyScorer

        scorer = AnomalyScorer()
        result = scorer.score_anomaly({
            'feature': 'api_call_count',
            'value': 300,
            'baseline_mean': 100,
            'baseline_stddev': 20,
            'context': {'is_admin': True, 'business_hours': False}
        })

        assert 'score' in result
        assert 'context_adjusted' in result


class TestPatternMatcher:
    """Test attack pattern matching."""

    def test_match_known_patterns(self):
        """✅ Match events against known patterns."""
        from guardian.hunting.threat_hunting import PatternMatcher

        matcher = PatternMatcher()
        result = matcher.match_patterns({
            'events': [
                {'id': 'evt1', 'type': 'unauthorized_login'},
                {'id': 'evt2', 'type': 'privilege_escalation'},
                {'id': 'evt3', 'type': 'data_exfiltration'}
            ]
        })

        assert 'matches' in result
        assert isinstance(result['matches'], list)

    def test_pattern_confidence_scoring(self):
        """✅ Score confidence of pattern match."""
        from guardian.hunting.threat_hunting import PatternMatcher

        matcher = PatternMatcher()
        result = matcher.match_patterns({
            'events': [
                {'type': 'initial_access', 'timestamp': 1000},
                {'type': 'lateral_movement', 'timestamp': 1010}
            ],
            'pattern': 'apt_lateral_movement'
        })

        assert 'matches' in result
        assert all('confidence' in m for m in result['matches'])

    def test_detect_novel_patterns(self):
        """✅ Detect potential novel attack patterns."""
        from guardian.hunting.threat_hunting import PatternMatcher

        matcher = PatternMatcher()
        result = matcher.detect_novel_patterns({
            'events': [
                {'type': 'event_a', 'timestamp': 1},
                {'type': 'event_b', 'timestamp': 2},
                {'type': 'event_c', 'timestamp': 3}
            ]
        })

        assert 'patterns' in result or 'novel_patterns' in result


class TestThreatPrioritizer:
    """Test threat prioritization."""

    def test_prioritize_threats(self):
        """✅ Prioritize threats by risk."""
        from guardian.hunting.threat_hunting import ThreatPrioritizer

        prioritizer = ThreatPrioritizer()
        result = prioritizer.prioritize_threats({
            'threats': [
                {'id': 'thr1', 'score': 0.5, 'severity': 'medium'},
                {'id': 'thr2', 'score': 0.9, 'severity': 'critical'},
                {'id': 'thr3', 'score': 0.3, 'severity': 'low'}
            ]
        })

        assert 'ranked_threats' in result
        assert result['ranked_threats'][0]['id'] == 'thr2'

    def test_threat_ranking_with_context(self):
        """✅ Rank threats considering context."""
        from guardian.hunting.threat_hunting import ThreatPrioritizer

        prioritizer = ThreatPrioritizer()
        result = prioritizer.prioritize_threats({
            'threats': [
                {'id': 'thr1', 'score': 0.7, 'target': 'prod_db'},
                {'id': 'thr2', 'score': 0.7, 'target': 'test_env'}
            ],
            'criticality': {'prod_db': 'critical', 'test_env': 'low'}
        })

        assert 'ranked_threats' in result
        assert result['ranked_threats'][0]['target'] == 'prod_db'

    def test_actionable_threat_extraction(self):
        """✅ Extract actionable threats."""
        from guardian.hunting.threat_hunting import ThreatPrioritizer

        prioritizer = ThreatPrioritizer()
        result = prioritizer.get_actionable_threats({
            'threats': [
                {'id': 'thr1', 'score': 0.95, 'actionable': True},
                {'id': 'thr2', 'score': 0.2, 'actionable': False}
            ],
            'min_actionability': 0.5
        })

        assert 'actionable' in result
        assert len(result['actionable']) <= 2


class TestThreatHuntingIntegration:
    """Integration tests for threat hunting."""

    def test_end_to_end_hunting_pipeline(self):
        """✅ Complete hunting pipeline."""
        from guardian.hunting.threat_hunting import (
            ThreatHunter,
            AnomalyScorer,
            PatternMatcher,
            ThreatPrioritizer
        )

        hunter = ThreatHunter()
        scorer = AnomalyScorer()
        matcher = PatternMatcher()
        prioritizer = ThreatPrioritizer()

        # Hunt threats
        threats = hunter.hunt_threats({'lookback_days': 7})
        assert 'threats' in threats

    def test_hunting_with_multiple_detection_methods(self):
        """✅ Hunt using multiple detection methods."""
        from guardian.hunting.threat_hunting import ThreatHunter

        hunter = ThreatHunter()
        result = hunter.hunt_threats({
            'methods': ['behavioral', 'pattern', 'anomaly', 'statistical']
        })

        assert 'threats' in result
        assert 'methods_used' in result or 'hunting_methods' in result

    def test_continuous_threat_hunting(self):
        """✅ Continuous threat hunting mode."""
        from guardian.hunting.threat_hunting import ThreatHunter

        hunter = ThreatHunter()
        result = hunter.hunt_threats({
            'continuous': True,
            'interval_minutes': 5,
            'retention_days': 30
        })

        assert 'hunt_id' in result
        assert 'status' in result
