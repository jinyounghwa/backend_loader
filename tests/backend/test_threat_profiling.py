"""Advanced threat profiling tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestThreatProfiler:
    """Test threat profiling."""

    def test_create_entity_profile(self):
        """✅ Create threat profile for entity."""
        from guardian.ml.threat_profiling import ThreatProfiler

        profiler = ThreatProfiler()

        profile = profiler.create_profile({
            'entity_type': 'IP',
            'entity_id': '203.0.113.42',
            'lookback_days': 90
        })

        assert 'profile_id' in profile
        assert profile['entity_type'] == 'IP'
        assert 'behavioral_history' in profile

    def test_profile_update(self):
        """✅ Update profile with new events."""
        from guardian.ml.threat_profiling import ThreatProfiler

        profiler = ThreatProfiler()

        profile = profiler.create_profile({
            'entity_type': 'IP',
            'entity_id': '203.0.113.42'
        })

        updated = profiler.update_profile({
            'profile_id': profile['profile_id'],
            'events': [
                {'type': 'LOGIN', 'timestamp': '2026-05-30T10:00:00Z'},
                {'type': 'DATA_ACCESS', 'timestamp': '2026-05-30T10:05:00Z'}
            ]
        })

        assert updated['status'] == 'updated'
        assert updated['event_count'] == 2

    def test_profile_comparison(self):
        """✅ Compare profiles for similarity."""
        from guardian.ml.threat_profiling import ThreatProfiler

        profiler = ThreatProfiler()

        similarity = profiler.compare_profiles({
            'profile_id_1': 'profile-123',
            'profile_id_2': 'profile-456'
        })

        assert 'similarity_score' in similarity
        assert 0 <= similarity['similarity_score'] <= 1

    def test_profile_clustering(self):
        """✅ Cluster similar threat profiles."""
        from guardian.ml.threat_profiling import ThreatProfiler

        profiler = ThreatProfiler()

        clusters = profiler.cluster_profiles({
            'profile_ids': ['p1', 'p2', 'p3', 'p4', 'p5'],
            'n_clusters': 3,
            'similarity_threshold': 0.7
        })

        assert 'clusters' in clusters
        assert len(clusters['clusters']) <= 3


class TestBehavioralAnalyzer:
    """Test behavioral anomaly detection."""

    def test_detect_anomaly(self):
        """✅ Detect anomalous behavior."""
        from guardian.ml.threat_profiling import BehavioralAnalyzer

        analyzer = BehavioralAnalyzer()

        anomaly = analyzer.detect_anomaly({
            'entity_id': 'user-123',
            'behavior': {
                'login_time': '02:00 UTC',  # Unusual time
                'location': 'CN',  # Different country
                'action': 'bulk_export'  # Unusual action
            },
            'baseline': {
                'normal_hours': '09:00-17:00 UTC',
                'normal_location': 'US',
                'normal_actions': ['read', 'write']
            }
        })

        assert 'anomaly_score' in anomaly
        assert anomaly['is_anomalous'] is True

    def test_behavior_baselining(self):
        """✅ Build behavioral baseline."""
        from guardian.ml.threat_profiling import BehavioralAnalyzer

        analyzer = BehavioralAnalyzer()

        baseline = analyzer.build_baseline({
            'entity_id': 'user-123',
            'historical_events': [
                {'time': '09:00 UTC', 'action': 'read'},
                {'time': '10:00 UTC', 'action': 'write'},
                {'time': '14:00 UTC', 'action': 'read'}
            ],
            'baseline_period_days': 30
        })

        assert 'baseline_id' in baseline
        assert 'normal_hours' in baseline
        assert 'normal_actions' in baseline

    def test_behavior_drift_detection(self):
        """✅ Detect behavioral drift."""
        from guardian.ml.threat_profiling import BehavioralAnalyzer

        analyzer = BehavioralAnalyzer()

        drift = analyzer.detect_drift({
            'entity_id': 'user-123',
            'baseline_id': 'baseline-456',
            'recent_events': 10,
            'drift_threshold': 0.8
        })

        assert 'drift_score' in drift
        assert 'drift_detected' in drift

    def test_collective_anomaly(self):
        """✅ Detect collective anomalies."""
        from guardian.ml.threat_profiling import BehavioralAnalyzer

        analyzer = BehavioralAnalyzer()

        collective = analyzer.detect_collective_anomaly({
            'entity_ids': ['user-1', 'user-2', 'user-3'],
            'behavior': 'simultaneous_data_export',
            'lookback_minutes': 5
        })

        assert 'collective_score' in collective
        assert collective['is_collective_anomaly'] is True or 'score' in collective


class TestPatternLearner:
    """Test attack pattern learning."""

    def test_extract_patterns(self):
        """✅ Extract patterns from events."""
        from guardian.ml.threat_profiling import PatternLearner

        learner = PatternLearner()

        patterns = learner.extract_patterns({
            'events': [
                {'type': 'RECON', 'target': 'server-1'},
                {'type': 'RECON', 'target': 'server-2'},
                {'type': 'EXPLOIT', 'target': 'server-1'},
                {'type': 'LATERAL_MOVE', 'target': 'server-3'}
            ],
            'pattern_types': ['sequential', 'frequent']
        })

        assert 'patterns' in patterns
        assert len(patterns['patterns']) > 0

    def test_pattern_matching(self):
        """✅ Match events against known patterns."""
        from guardian.ml.threat_profiling import PatternLearner

        learner = PatternLearner()

        matches = learner.match_patterns({
            'event_sequence': [
                {'type': 'RECON'},
                {'type': 'EXPLOIT'},
                {'type': 'LATERAL_MOVE'}
            ],
            'known_patterns': ['ransomware_chain', 'apt_infiltration']
        })

        assert 'matched_patterns' in matches
        assert 'confidence' in matches

    def test_pattern_evolution(self):
        """✅ Track pattern evolution over time."""
        from guardian.ml.threat_profiling import PatternLearner

        learner = PatternLearner()

        evolution = learner.track_evolution({
            'pattern_id': 'pattern-123',
            'lookback_days': 30
        })

        assert 'evolution_score' in evolution
        assert 'trend' in evolution

    def test_zero_day_detection(self):
        """✅ Detect potential zero-day patterns."""
        from guardian.ml.threat_profiling import PatternLearner

        learner = PatternLearner()

        potential_zero_day = learner.detect_zero_day({
            'event_sequence': [
                {'type': 'UNKNOWN_SYSCALL', 'args': [1, 2, 3]},
                {'type': 'PRIVILEGE_ESCALATION'},
                {'type': 'KERNEL_MODIFICATION'}
            ]
        })

        assert 'zero_day_score' in potential_zero_day
        assert 'risk_level' in potential_zero_day


class TestThreatScorer:
    """Test threat scoring."""

    def test_compute_threat_score(self):
        """✅ Compute entity threat score."""
        from guardian.ml.threat_profiling import ThreatScorer

        scorer = ThreatScorer()

        score = scorer.compute_score({
            'entity_id': 'ip-203.0.113.42',
            'signals': [
                {'type': 'anomaly_score', 'value': 0.85},
                {'type': 'pattern_match', 'value': 0.72},
                {'type': 'reputation', 'value': 0.90}
            ]
        })

        assert 'threat_score' in score
        assert 0 <= score['threat_score'] <= 1
        assert 'risk_level' in score

    def test_contextual_scoring(self):
        """✅ Score threats with context."""
        from guardian.ml.threat_profiling import ThreatScorer

        scorer = ThreatScorer()

        score = scorer.compute_contextual_score({
            'entity_id': 'user-123',
            'threat_level': 0.75,
            'context': {
                'is_admin': True,
                'access_level': 'critical',
                'data_sensitivity': 'high'
            }
        })

        assert 'contextual_score' in score
        assert score['contextual_score'] >= 0.75

    def test_score_explanation(self):
        """✅ Explain threat score components."""
        from guardian.ml.threat_profiling import ThreatScorer

        scorer = ThreatScorer()

        explanation = scorer.explain_score({
            'threat_score': 0.82,
            'entity_id': 'ip-203.0.113.42'
        })

        assert 'explanation' in explanation or 'components' in explanation
        assert 'contributing_factors' in explanation or 'factors' in explanation

    def test_score_timeline(self):
        """✅ Generate threat score timeline."""
        from guardian.ml.threat_profiling import ThreatScorer

        scorer = ThreatScorer()

        timeline = scorer.get_score_timeline({
            'entity_id': 'ip-203.0.113.42',
            'lookback_hours': 24,
            'interval_minutes': 60
        })

        assert 'timeline' in timeline
        assert len(timeline['timeline']) > 0


class TestThreatProfilingIntegration:
    """End-to-end threat profiling workflows."""

    def test_full_profiling_pipeline(self):
        """✅ Complete pipeline: profile → analyze → score."""
        from guardian.ml.threat_profiling import (
            ThreatProfiler,
            BehavioralAnalyzer,
            ThreatScorer
        )

        profiler = ThreatProfiler()
        analyzer = BehavioralAnalyzer()
        scorer = ThreatScorer()

        # Step 1: Create profile
        profile = profiler.create_profile({
            'entity_type': 'IP',
            'entity_id': '203.0.113.42'
        })

        assert 'profile_id' in profile

        # Step 2: Analyze behavior
        anomaly = analyzer.detect_anomaly({
            'entity_id': '203.0.113.42',
            'behavior': {'action': 'bulk_export'}
        })

        assert 'anomaly_score' in anomaly

        # Step 3: Score threat
        score = scorer.compute_score({
            'entity_id': '203.0.113.42',
            'signals': [{'type': 'anomaly_score', 'value': anomaly['anomaly_score']}]
        })

        assert score['threat_score'] > 0

    def test_attack_chain_detection(self):
        """✅ Detect multi-stage attack chains."""
        from guardian.ml.threat_profiling import PatternLearner

        learner = PatternLearner()

        chain = learner.match_patterns({
            'event_sequence': [
                {'type': 'RECON'},
                {'type': 'EXPLOIT'},
                {'type': 'LATERAL_MOVE'},
                {'type': 'PERSISTENCE'},
                {'type': 'EXFILTRATION'}
            ],
            'known_patterns': ['apt_chain']
        })

        assert 'matched_patterns' in chain

    def test_threat_correlation(self):
        """✅ Correlate threat profiles."""
        from guardian.ml.threat_profiling import ThreatProfiler

        profiler = ThreatProfiler()

        correlation = profiler.correlate_threats({
            'entity_ids': ['ip-1', 'ip-2', 'user-1'],
            'correlation_type': 'simultaneous_activity'
        })

        assert 'correlations' in correlation or 'correlated_entities' in correlation

    def test_threat_ranking(self):
        """✅ Rank threats by priority."""
        from guardian.ml.threat_profiling import ThreatScorer

        scorer = ThreatScorer()

        ranking = scorer.rank_threats({
            'entities': [
                {'id': 'ip-1', 'score': 0.85},
                {'id': 'ip-2', 'score': 0.65},
                {'id': 'user-1', 'score': 0.92}
            ]
        })

        assert 'ranked_threats' in ranking
        assert ranking['ranked_threats'][0]['score'] >= ranking['ranked_threats'][1]['score']
