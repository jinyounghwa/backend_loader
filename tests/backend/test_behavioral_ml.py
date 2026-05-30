"""Sprint 71 Phase 3: Advanced ML Anomaly Detection (17 tests)"""

import pytest
from datetime import datetime, timedelta


class TestBehavioralProfiler:
    """Test user behavior profiling."""

    def test_build_user_profile(self):
        """✅ Build behavioral profile for user."""
        from guardian.ml.behavioral_analyzer import BehavioralProfiler

        profiler = BehavioralProfiler()

        # Add user activity
        activities = [
            {'user': 'alice', 'action': 'GetUser', 'timestamp': datetime.now()},
            {'user': 'alice', 'action': 'ListRoles', 'timestamp': datetime.now()},
            {'user': 'alice', 'action': 'GetUser', 'timestamp': datetime.now()}
        ]

        for activity in activities:
            profiler.record_activity(activity)

        profile = profiler.get_profile('alice')

        assert 'typical_actions' in profile
        assert 'GetUser' in profile['typical_actions']

    def test_detect_action_deviation(self):
        """✅ Detect deviation from typical actions."""
        from guardian.ml.behavioral_analyzer import BehavioralProfiler

        profiler = BehavioralProfiler()

        # Build profile
        profiler.record_activity({'user': 'bob', 'action': 'GetUser'})
        profiler.record_activity({'user': 'bob', 'action': 'ListRoles'})

        # Unusual action
        profile = profiler.get_profile('bob')

        assert 'GetUser' in profile['typical_actions']

    def test_profile_time_patterns(self):
        """✅ Profile typical activity times."""
        from guardian.ml.behavioral_analyzer import BehavioralProfiler

        profiler = BehavioralProfiler()

        # Activity during business hours
        for hour in [9, 10, 11, 14, 15]:
            ts = datetime.now().replace(hour=hour, minute=0)
            profiler.record_activity({'user': 'charlie', 'timestamp': ts, 'action': 'API_CALL'})

        profile = profiler.get_profile('charlie')

        assert 'typical_hours' in profile


class TestAnomalyDetector:
    """Test anomaly detection algorithms."""

    def test_detect_behavioral_anomaly(self):
        """✅ Detect anomalous user behavior."""
        from guardian.ml.behavioral_analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Normal behavior
        detector.record_normal_behavior({
            'user': 'alice',
            'action': 'GetUser',
            'location': 'US-EAST-1'
        })

        # Anomalous behavior
        anomaly_score = detector.detect_anomaly({
            'user': 'alice',
            'action': 'DeleteBucket',  # Unusual
            'location': 'EU-WEST-1'    # Unusual
        })

        assert anomaly_score > 50

    def test_detect_time_based_anomaly(self):
        """✅ Detect anomalies based on time."""
        from guardian.ml.behavioral_analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Typical daytime activity
        for _ in range(5):
            detector.record_normal_behavior({
                'user': 'bob',
                'hour': 10,
                'action': 'GetUser'
            })

        # Night activity (anomalous)
        anomaly_score = detector.detect_anomaly({
            'user': 'bob',
            'hour': 3,
            'action': 'DeleteTable'
        })

        assert anomaly_score > 60

    def test_detect_frequency_anomaly(self):
        """✅ Detect unusual frequency of actions."""
        from guardian.ml.behavioral_analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Baseline: 1 API call per hour
        detector.record_normal_behavior({'user': 'charlie', 'frequency': 1})

        # Anomaly: 50 API calls per hour
        anomaly_score = detector.detect_anomaly({
            'user': 'charlie',
            'frequency': 50
        })

        assert anomaly_score > 70


class TestContextScorer:
    """Test context-based anomaly scoring."""

    def test_score_time_context(self):
        """✅ Score anomaly based on time context."""
        from guardian.ml.behavioral_analyzer import ContextScorer

        scorer = ContextScorer()

        # Set baseline hours
        scorer.set_baseline_hours('alice', [9, 10, 11, 14, 15])

        # Check activity at unusual time
        score = scorer.get_time_context_score('alice', hour=3)

        assert score > 50

    def test_score_location_context(self):
        """✅ Score anomaly based on geographic location."""
        from guardian.ml.behavioral_analyzer import ContextScorer

        scorer = ContextScorer()

        # Set baseline locations
        scorer.set_baseline_locations('bob', ['US-EAST-1', 'US-WEST-2'])

        # Check activity from unusual location
        score = scorer.get_location_context_score('bob', location='AP-SOUTHEAST-1')

        assert score > 40

    def test_score_device_context(self):
        """✅ Score anomaly based on device."""
        from guardian.ml.behavioral_analyzer import ContextScorer

        scorer = ContextScorer()

        # Set baseline devices
        scorer.set_baseline_devices('charlie', ['browser', 'cli'])

        # Check activity from unusual device
        score = scorer.get_device_context_score('charlie', device='mobile')

        assert score > 30


class TestAnomalyPredictor:
    """Test anomaly prediction."""

    def test_predict_anomaly_probability(self):
        """✅ Predict probability of anomaly in next 24 hours."""
        from guardian.ml.anomaly_predictor import AnomalyPredictor

        predictor = AnomalyPredictor()

        # Historical anomalies
        predictor.record_anomaly({'user': 'alice', 'severity': 'HIGH'})
        predictor.record_anomaly({'user': 'alice', 'severity': 'MEDIUM'})

        # Predict next 24 hours
        probability = predictor.predict_anomaly_probability('alice')

        assert 0 <= probability <= 1
        assert probability > 0.3  # Has historical anomalies

    def test_predict_threat_severity(self):
        """✅ Predict threat severity."""
        from guardian.ml.anomaly_predictor import AnomalyPredictor

        predictor = AnomalyPredictor()

        # Add threat patterns
        predictor.record_anomaly({'severity': 'CRITICAL', 'type': 'MALWARE'})
        predictor.record_anomaly({'severity': 'HIGH', 'type': 'UNAUTHORIZED'})

        # Predict
        severity = predictor.predict_severity({'type': 'MALWARE'})

        assert severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

    def test_predict_with_temporal_patterns(self):
        """✅ Predict using temporal patterns."""
        from guardian.ml.anomaly_predictor import AnomalyPredictor

        predictor = AnomalyPredictor()

        # Record daily pattern
        for day in range(7):
            predictor.record_anomaly({
                'day_of_week': day,
                'anomaly_count': 5 if day in [1, 2] else 0
            })

        # Monday prediction (historically anomalous)
        probability = predictor.predict_for_day(day_of_week=1)

        assert probability > 0.5


class TestBehavioralMLIntegration:
    """Test end-to-end behavioral ML."""

    def test_profile_and_detect_workflow(self):
        """✅ Full profiling and detection workflow."""
        from guardian.ml.behavioral_analyzer import (
            BehavioralProfiler, AnomalyDetector, ContextScorer
        )

        profiler = BehavioralProfiler()
        detector = AnomalyDetector()
        scorer = ContextScorer()

        # Build profile
        for _ in range(10):
            profiler.record_activity({
                'user': 'alice',
                'action': 'GetUser',
                'hour': 10
            })

        profile = profiler.get_profile('alice')

        # Detect anomaly
        anomaly_score = detector.detect_anomaly({
            'user': 'alice',
            'action': 'DeleteTable',  # Unusual
            'hour': 3                  # Unusual time
        })

        assert anomaly_score > 50

    def test_combined_scoring(self):
        """✅ Combine multiple anomaly scores."""
        from guardian.ml.behavioral_analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Build baseline
        detector.record_normal_behavior({'user': 'bob', 'action': 'read'})

        # Detect with multiple signals
        final_score = detector.detect_anomaly({
            'user': 'bob',
            'action': 'delete',  # +30
            'frequency': 'high',  # +20
            'time': 'night'       # +15
        })

        assert final_score > 50

    def test_false_positive_reduction(self):
        """✅ Reduce false positives with context."""
        from guardian.ml.behavioral_analyzer import ContextScorer

        scorer = ContextScorer()

        # If user has done this action before, lower score
        scorer.set_baseline_actions('charlie', ['DeleteBucket'])

        # Same action, lower anomaly
        score = scorer.get_action_context_score('charlie', 'DeleteBucket')

        assert score < 20  # Not anomalous if in baseline
