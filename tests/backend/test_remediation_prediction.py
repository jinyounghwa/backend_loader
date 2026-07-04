"""Sprint 48 Phase 2: ML-Based Remediation Prediction Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from guardian.predictors.remediation_predictor import RemediationPredictor


class TestRemediationPrediction:
    """ML-based remediation success prediction and strategy optimization."""

    def test_feature_engineering_extraction(self):
        """✅ Feature engineering extracts and normalizes threat features."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        threat = {
            'threat_id': 'THREAT-PRED-001',
            'threat_type': 'Lateral Movement',
            'severity': 8,
            'affected_resources': 3,
            'blast_radius_score': 7.5,
            'remediation_type': 'ec2_stop',
            'timestamp': datetime.now().isoformat(),
            'attack_pattern_score': 6
        }

        features = predictor.engineer_features(threat)

        # Verify all features are extracted and normalized (0-1 range or reasonable values)
        assert 'threat_severity' in features
        assert 0.0 <= features['threat_severity'] <= 1.0
        assert 'resource_count' in features
        assert 0.0 <= features['resource_count'] <= 1.0
        assert 'blast_radius_score' in features
        assert 'remediation_complexity' in features
        assert 'recent_failure_rate' in features
        assert 0.0 <= features['recent_failure_rate'] <= 1.0
        assert 'is_peak_hours' in features
        assert 'time_of_day_risk' in features
        assert 0.0 <= features['time_of_day_risk'] <= 1.0

    def test_success_rate_prediction(self):
        """✅ Success rate prediction reflects threat severity and complexity."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Low severity, simple remediation
        easy_threat = {
            'severity': 2,
            'affected_resources': 1,
            'blast_radius_score': 1.0,
            'remediation_type': 's3_block_public',
            'timestamp': '2026-05-25T12:00:00'
        }

        # High severity, complex remediation
        hard_threat = {
            'severity': 10,
            'affected_resources': 5,
            'blast_radius_score': 9.5,
            'remediation_type': 'network_isolate',
            'timestamp': '2026-05-25T22:00:00'
        }

        easy_success = predictor.predict_success_rate(easy_threat)
        hard_success = predictor.predict_success_rate(hard_threat)

        # Easy threat should have higher success rate
        assert easy_success > hard_success
        assert 0.0 <= easy_success <= 1.0
        assert 0.0 <= hard_success <= 1.0
        assert easy_success >= 0.7  # Simple remediation should be likely
        assert hard_success >= 0.5  # Even complex should have reasonable chance

    def test_remediation_time_estimation(self):
        """✅ Time estimation reflects remediation type and resource count."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        fast_threat = {
            'remediation_type': 's3_block_public',
            'affected_resources': 1,
            'timestamp': '2026-05-25T12:00:00'
        }

        slow_threat = {
            'remediation_type': 'network_isolate',
            'affected_resources': 5,
            'timestamp': '2026-05-25T02:00:00'  # Night time = slower
        }

        fast_time = predictor.estimate_remediation_time(fast_threat)
        slow_time = predictor.estimate_remediation_time(slow_threat)

        # Fast should be quicker than slow
        assert fast_time < slow_time
        assert fast_time > 0
        assert slow_time > 0
        assert fast_time < 40  # S3 block should be < 40 seconds
        assert slow_time > 50  # Network isolate with 5 resources should be > 50

    def test_remediation_cost_estimation(self):
        """✅ Cost estimation includes action type and resource count."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        cheap_threat = {
            'remediation_type': 's3_block_public',
            'affected_resources': 1
        }

        expensive_threat = {
            'remediation_type': 'ec2_terminate',
            'affected_resources': 3
        }

        cheap_cost = predictor.estimate_remediation_cost(cheap_threat)
        expensive_cost = predictor.estimate_remediation_cost(expensive_threat)

        # EC2 terminate should cost more than S3 block
        assert cheap_cost < expensive_cost
        assert cheap_cost == 0.0  # S3 block public costs nothing
        assert expensive_cost >= 0.15  # EC2 terminate * 3 resources

    def test_remediation_strategy_ranking(self):
        """✅ Strategy ranking prioritizes by efficiency (success/cost)."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        threat = {
            'severity': 7,
            'affected_resources': 2,
            'blast_radius_score': 5.0,
            'timestamp': '2026-05-25T14:00:00'
        }

        available_strategies = [
            'ec2_stop',
            'ec2_terminate',
            's3_block_public',
            'iam_revoke'
        ]

        ranked = predictor.rank_remediation_strategies(threat, available_strategies)

        # Verify structure
        assert len(ranked) == len(available_strategies)
        assert all('strategy' in r for r in ranked)
        assert all('success_probability' in r for r in ranked)
        assert all('estimated_time_seconds' in r for r in ranked)
        assert all('estimated_cost' in r for r in ranked)
        assert all('efficiency_score' in r for r in ranked)

        # Verify ranking (first should have highest efficiency)
        for i in range(len(ranked) - 1):
            assert ranked[i]['efficiency_score'] >= ranked[i + 1]['efficiency_score']

    def test_prediction_with_confidence(self):
        """✅ Confidence-scored predictions include risk factors and intervals."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Add some historical data for confidence calculation
        for i in range(10):
            predictor.record_outcome(
                {'threat_type': 'Brute Force', 'severity': 5, 'affected_resources': 1},
                'success' if i < 8 else 'failed',
                30.0,
                0.01
            )

        threat = {
            'threat_type': 'Brute Force',
            'severity': 8,
            'affected_resources': 2,
            'blast_radius_score': 4.5,
            'remediation_type': 'iam_revoke',
            'timestamp': '2026-05-25T15:00:00'
        }

        prediction = predictor.predict_with_confidence(threat)

        # Verify structure
        assert 'success_probability' in prediction
        assert 'confidence_level' in prediction
        assert prediction['confidence_level'] in ['high', 'medium', 'low']
        assert 'confidence_score' in prediction
        assert 0.5 <= prediction['confidence_score'] <= 1.0
        assert 'estimated_time_seconds' in prediction
        assert 'estimated_cost' in prediction
        assert 'confidence_interval' in prediction
        assert len(prediction['confidence_interval']) == 2
        assert prediction['confidence_interval'][0] <= prediction['success_probability'] <= prediction['confidence_interval'][1]
        assert 'risk_factors' in prediction
        assert isinstance(prediction['risk_factors'], list)
        assert 'recommendation' in prediction

    def test_peak_hours_impact_on_prediction(self):
        """✅ Peak hours (business hours) reduce success probability."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        base_threat = {
            'severity': 5,
            'affected_resources': 1,
            'blast_radius_score': 2.0,
            'remediation_type': 'ec2_stop'
        }

        # Off-peak (2 AM)
        off_peak_threat = base_threat.copy()
        off_peak_threat['timestamp'] = '2026-05-25T02:00:00'

        # Peak hours (2 PM)
        peak_threat = base_threat.copy()
        peak_threat['timestamp'] = '2026-05-25T14:00:00'

        off_peak_success = predictor.predict_success_rate(off_peak_threat)
        peak_success = predictor.predict_success_rate(peak_threat)

        # Peak hours should have lower success (more systems active)
        assert off_peak_success >= peak_success

    def test_model_metrics_calculation(self):
        """✅ Model accuracy metrics track prediction performance."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Empty model
        metrics = predictor.get_model_metrics()
        assert metrics['total_predictions'] == 0
        assert metrics['accuracy'] == 0.0
        assert metrics['success_rate'] == 0.0

        # Add historical data
        for i in range(10):
            predictor.record_outcome(
                {
                    'threat_id': f'THREAT-{i}',
                    'threat_type': 'Test',
                    'severity': 5,
                    'affected_resources': 1
                },
                'success' if i < 7 else 'failed',
                30.0,
                0.01
            )

        metrics = predictor.get_model_metrics()
        assert metrics['total_predictions'] == 10
        assert metrics['accuracy'] == 0.7
        assert metrics['success_rate'] == 0.7
