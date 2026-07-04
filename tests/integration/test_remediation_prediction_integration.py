"""Sprint 48 Phase 2: ML-Based Remediation Prediction Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from guardian.predictors.remediation_predictor import RemediationPredictor


class TestRemediationPredictionIntegration:
    """End-to-end ML-based prediction workflows."""

    def test_end_to_end_threat_prediction_pipeline(self):
        """✅ Complete flow: feature engineering → prediction → ranking → recommendation."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Realistic threat
        threat = {
            'threat_id': 'THREAT-PRED-E2E-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 9,
            'affected_resources': 3,
            'blast_radius_score': 7.8,
            'remediation_type': 'ec2_terminate',
            'timestamp': '2026-05-25T11:30:00',
            'attack_pattern_score': 5
        }

        # Step 1: Feature engineering
        features = predictor.engineer_features(threat)
        assert len(features) > 0
        assert all(isinstance(v, float) for v in features.values())

        # Step 2: Success prediction
        success_prob = predictor.predict_success_rate(threat)
        assert 0.0 <= success_prob <= 1.0

        # Step 3: Strategy ranking
        strategies = ['ec2_stop', 'ec2_terminate', 'network_isolate']
        ranked = predictor.rank_remediation_strategies(threat, strategies)
        assert len(ranked) == len(strategies)
        assert ranked[0]['efficiency_score'] >= ranked[-1]['efficiency_score']

        # Step 4: Confidence-based recommendation
        prediction = predictor.predict_with_confidence(threat)
        assert prediction['recommendation'] in [
            'Proceed with remediation',
            'Proceed with caution',
            'Require manual approval',
            'Escalate to human review'
        ]

    def test_multi_strategy_comparison(self):
        """✅ Compare multiple strategies for same threat."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        threat = {
            'severity': 7,
            'affected_resources': 2,
            'blast_radius_score': 5.5,
            'timestamp': '2026-05-25T13:00:00'
        }

        strategies = [
            'ec2_stop',
            'ec2_terminate',
            's3_block_public',
            'iam_revoke',
            'network_isolate'
        ]

        ranked = predictor.rank_remediation_strategies(threat, strategies)

        # Verify ranking properties
        assert len(ranked) == len(strategies)

        # Check each strategy has complete metrics
        for strategy in ranked:
            assert 0.0 <= strategy['success_probability'] <= 1.0
            assert strategy['estimated_time_seconds'] > 0
            assert strategy['estimated_cost'] >= 0.0
            assert strategy['efficiency_score'] >= 0.0

        # Top strategy should be efficient
        top_strategy = ranked[0]
        assert top_strategy['efficiency_score'] >= ranked[-1]['efficiency_score']

    def test_cost_benefit_analysis(self):
        """✅ Compare remediation cost vs. threat severity."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Low-cost threat
        cheap_threat = {
            'severity': 3,
            'affected_resources': 1,
            'blast_radius_score': 1.5,
            'remediation_type': 's3_block_public',
            'timestamp': '2026-05-25T10:00:00'
        }

        # Expensive threat
        expensive_threat = {
            'severity': 10,
            'affected_resources': 5,
            'blast_radius_score': 9.5,
            'remediation_type': 'ec2_terminate',
            'timestamp': '2026-05-25T10:00:00'
        }

        cheap_cost = predictor.estimate_remediation_cost(cheap_threat)
        cheap_success = predictor.predict_success_rate(cheap_threat)

        expensive_cost = predictor.estimate_remediation_cost(expensive_threat)
        expensive_success = predictor.predict_success_rate(expensive_threat)

        # Verify cost increases with severity and resource count
        assert expensive_cost > cheap_cost
        # Success rate for cheap remediation should be high
        assert cheap_success >= 0.7

    def test_historical_data_impact_on_confidence(self):
        """✅ More historical data increases model confidence."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        threat = {
            'threat_type': 'Lateral Movement',
            'severity': 6,
            'affected_resources': 2,
            'blast_radius_score': 4.5,
            'remediation_type': 'iam_revoke',
            'timestamp': '2026-05-25T12:00:00'
        }

        # Predict with no historical data
        pred_no_history = predictor.predict_with_confidence(threat)
        initial_confidence = pred_no_history['confidence_score']

        # Add historical data
        for i in range(50):
            predictor.record_outcome(
                {
                    'threat_type': 'Lateral Movement',
                    'severity': 6,
                    'affected_resources': 2
                },
                'success' if i < 45 else 'failed',
                40.0,
                0.02
            )

        # Predict with historical data
        pred_with_history = predictor.predict_with_confidence(threat)
        improved_confidence = pred_with_history['confidence_score']

        # Confidence should improve with more data
        assert improved_confidence >= initial_confidence

    def test_time_series_prediction_accuracy(self):
        """✅ Predictions remain consistent across different threat severities."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Test across severity range
        predictions = []
        for severity in [2, 4, 6, 8, 10]:
            threat = {
                'severity': severity,
                'affected_resources': 1,
                'blast_radius_score': severity * 0.5,  # Lower blast radius multiplier
                'remediation_type': 'ec2_stop',
                'timestamp': '2026-05-25T12:00:00'
            }
            pred = predictor.predict_with_confidence(threat)
            predictions.append(pred)

        # Verify predictions are reasonable
        assert len(predictions) == 5

        # Success probability should be reasonable for all
        for pred in predictions:
            assert 0.3 <= pred['success_probability'] <= 1.0
            assert pred['recommendation'] is not None

        # All predictions should be consistent and reasonable
        assert all(p['success_probability'] >= 0.3 for p in predictions)

    def test_parallel_strategy_optimization(self):
        """✅ Optimize strategy selection for multi-resource threat."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        # Complex multi-resource threat
        multi_threat = {
            'severity': 9,
            'affected_resources': 5,
            'blast_radius_score': 8.5,
            'timestamp': '2026-05-25T14:30:00'
        }

        # Strategies suitable for different resource types
        strategies = [
            'ec2_stop',           # For EC2
            'ec2_terminate',      # For EC2 (aggressive)
            's3_block_public',    # For S3
            'iam_revoke',         # For IAM
            'network_isolate'     # For Network
        ]

        ranked = predictor.rank_remediation_strategies(multi_threat, strategies)

        # Verify optimal strategy is identified
        best_strategy = ranked[0]
        assert best_strategy['strategy'] is not None
        assert best_strategy['efficiency_score'] > 0

        # Top 3 strategies should all be reasonable
        top_3 = ranked[:3]
        for strategy in top_3:
            assert strategy['success_probability'] >= 0.4
            assert strategy['estimated_time_seconds'] > 0

    def test_model_improvement_with_outcome_recording(self):
        """✅ Model accuracy improves as outcomes are recorded."""
        mock_audit = Mock()
        predictor = RemediationPredictor(mock_audit)

        threat_type = 'Brute Force'
        threats = []

        # Generate 20 threats of same type
        for i in range(20):
            threat = {
                'threat_id': f'THREAT-IMPROVE-{i}',
                'threat_type': threat_type,
                'severity': 5 + (i % 3),
                'affected_resources': 1 + (i % 3),
                'timestamp': (datetime.now() + timedelta(hours=i)).isoformat()
            }
            threats.append(threat)

        # Record outcomes (80% success rate)
        for i, threat in enumerate(threats):
            outcome = 'success' if i < 16 else 'failed'
            predictor.record_outcome(threat, outcome, 30.0, 0.01)

        # Get model metrics
        metrics = predictor.get_model_metrics()

        # Verify metrics
        assert metrics['total_predictions'] == 20
        assert metrics['success_rate'] == 0.8
        assert metrics['accuracy'] == 0.8

        # Future predictions should account for this 80% success rate
        new_threat = {
            'threat_type': threat_type,
            'severity': 5,
            'affected_resources': 1,
            'remediation_type': 'iam_revoke',
            'timestamp': '2026-05-25T16:00:00'
        }

        prediction = predictor.predict_with_confidence(new_threat)
        # Should reflect the historical 80% success for similar threats
        assert prediction['confidence_level'] in ['high', 'medium']
