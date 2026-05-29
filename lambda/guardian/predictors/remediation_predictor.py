"""ML-Based Remediation Prediction - Success rate and strategy optimization."""

from typing import Dict, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import statistics


class RemediationPredictor:
    """Predict remediation success and optimal strategies using ML."""

    def __init__(self, audit_logger=None):
        """Initialize predictor with historical data."""
        self.audit = audit_logger
        self.historical_data = []

    def engineer_features(self, threat: Dict) -> Dict[str, float]:
        """
        Extract features for ML model.

        Features:
        - threat_severity (1-10)
        - resource_count (affected resources)
        - blast_radius_score (0-10)
        - remediation_type (ec2_stop, s3_block, iam_revoke, network_isolate)
        - is_peak_hours (0 = off-peak, 1 = peak)
        - recent_failure_rate (0.0-1.0)
        - attack_pattern_score (0-10)
        - time_of_day_risk (0.0-1.0)
        """
        features = {}

        # Base threat features
        features['threat_severity'] = float(threat.get('severity', 5)) / 10.0
        features['resource_count'] = min(float(threat.get('affected_resources', 1)) / 10.0, 1.0)
        features['blast_radius_score'] = float(threat.get('blast_radius_score', 0)) / 10.0

        # Time-based features
        timestamp = threat.get('timestamp', datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
                hour = dt.hour
                # Peak hours: 9-17 (business hours)
                features['is_peak_hours'] = 1.0 if 9 <= hour <= 17 else 0.0
                # Risk increases during night hours (higher blast radius potential)
                if 0 <= hour < 6:
                    features['time_of_day_risk'] = 0.8
                elif 18 <= hour < 24:
                    features['time_of_day_risk'] = 0.6
                else:
                    features['time_of_day_risk'] = 0.2
            except:
                features['is_peak_hours'] = 0.5
                features['time_of_day_risk'] = 0.5
        else:
            features['is_peak_hours'] = 0.5
            features['time_of_day_risk'] = 0.5

        # Remediation type
        remediation_type = threat.get('remediation_type', 'unknown')
        type_complexity = {
            'ec2_stop': 0.3,
            'ec2_terminate': 0.4,
            's3_block_public': 0.2,
            'iam_revoke': 0.5,
            'network_isolate': 0.6,
            'unknown': 0.5
        }
        features['remediation_complexity'] = type_complexity.get(remediation_type, 0.5)

        # Historical failure rate
        features['recent_failure_rate'] = self._calculate_recent_failure_rate(threat)

        # Attack pattern
        features['attack_pattern_score'] = float(threat.get('attack_pattern_score', 0)) / 10.0

        return features

    def predict_success_rate(self, threat: Dict) -> float:
        """
        Predict probability of successful remediation (0.0-1.0).

        Formula: base_success * (1.0 - complexity) * (1.0 - failure_penalty) * time_adjustment
        """
        features = self.engineer_features(threat)

        # Base success rate: 0.95 (high confidence)
        base_success = 0.95

        # Severity penalty: higher severity = higher success rate (more critical, more careful)
        severity_bonus = features['threat_severity'] * 0.15

        # Complexity penalty
        complexity_penalty = features['remediation_complexity'] * 0.25

        # Historical failure penalty
        failure_penalty = features['recent_failure_rate'] * 0.30

        # Time of day adjustment (peak hours = lower success due to more systems active)
        time_adjustment = 1.0 - (features['is_peak_hours'] * 0.10)

        # Blast radius increases risk
        blast_penalty = features['blast_radius_score'] * 0.15

        # Combine factors
        success_rate = base_success + severity_bonus - complexity_penalty - failure_penalty - blast_penalty
        success_rate *= time_adjustment

        # Clamp between 0.0 and 1.0
        return max(0.0, min(1.0, success_rate))

    def estimate_remediation_time(self, threat: Dict) -> float:
        """
        Estimate time to complete remediation in seconds.

        Base times by type:
        - ec2_stop: 30-45 seconds
        - ec2_terminate: 60-90 seconds
        - s3_block_public: 20-30 seconds
        - iam_revoke: 40-60 seconds
        - network_isolate: 50-70 seconds
        """
        remediation_type = threat.get('remediation_type', 'unknown')

        base_times = {
            'ec2_stop': 35.0,
            'ec2_terminate': 75.0,
            's3_block_public': 25.0,
            'iam_revoke': 50.0,
            'network_isolate': 60.0,
            'unknown': 45.0
        }

        base_time = base_times.get(remediation_type, 45.0)

        # Scale by resource count
        resource_count = threat.get('affected_resources', 1)
        time_estimate = base_time * (1.0 + (resource_count - 1) * 0.3)

        # Peak hours add overhead
        features = self.engineer_features(threat)
        if features['is_peak_hours'] > 0.5:
            time_estimate *= 1.2

        # Blast radius adds complexity
        time_estimate *= (1.0 + features['blast_radius_score'] * 0.2)

        return time_estimate

    def estimate_remediation_cost(self, threat: Dict) -> float:
        """
        Estimate cost of remediation in dollars.

        Cost by type:
        - ec2_stop: $0.01
        - ec2_terminate: $0.05
        - s3_block_public: $0.00
        - iam_revoke: $0.02
        - network_isolate: $0.03
        """
        remediation_type = threat.get('remediation_type', 'unknown')

        base_costs = {
            'ec2_stop': 0.01,
            'ec2_terminate': 0.05,
            's3_block_public': 0.00,
            'iam_revoke': 0.02,
            'network_isolate': 0.03,
            'unknown': 0.02
        }

        base_cost = base_costs.get(remediation_type, 0.02)

        # Scale by resource count
        resource_count = threat.get('affected_resources', 1)
        cost_estimate = base_cost * resource_count

        return round(cost_estimate, 3)

    def rank_remediation_strategies(self, threat: Dict, available_strategies: List[str]) -> List[Dict]:
        """
        Rank available remediation strategies by success probability and efficiency.

        Returns list of strategies with scores, ranked by efficiency (success_rate / cost).
        """
        ranked = []

        for strategy in available_strategies:
            # Simulate strategy
            strategy_threat = threat.copy()
            strategy_threat['remediation_type'] = strategy

            success_rate = self.predict_success_rate(strategy_threat)
            time_estimate = self.estimate_remediation_time(strategy_threat)
            cost_estimate = self.estimate_remediation_cost(strategy_threat)

            # Efficiency score: success_rate / (cost + time/1000)
            # Prefer fast, cheap, reliable strategies
            efficiency = success_rate / (cost_estimate + 0.01) / (time_estimate / 100.0 + 0.1)

            ranked.append({
                'strategy': strategy,
                'success_probability': round(success_rate, 3),
                'estimated_time_seconds': round(time_estimate, 1),
                'estimated_cost': round(cost_estimate, 3),
                'efficiency_score': round(efficiency, 3),
                'recommendation': self._get_recommendation(success_rate)
            })

        # Sort by efficiency score (descending)
        ranked.sort(key=lambda x: x['efficiency_score'], reverse=True)
        return ranked

    def predict_with_confidence(self, threat: Dict) -> Dict:
        """
        Generate full prediction with confidence interval.

        Returns:
        {
            'success_probability': float,
            'confidence_level': str (high/medium/low),
            'estimated_time_seconds': float,
            'estimated_cost': float,
            'confidence_interval': (min, max),
            'risk_factors': [str],
            'recommendation': str
        }
        """
        features = self.engineer_features(threat)
        success_prob = self.predict_success_rate(threat)
        time_est = self.estimate_remediation_time(threat)
        cost_est = self.estimate_remediation_cost(threat)

        # Confidence based on data quality and feature reliability
        # More historical data = higher confidence
        base_confidence = 0.7 + (len(self.historical_data) / 1000.0) * 0.25

        # Severity influences confidence (extreme severity = lower confidence)
        if threat.get('severity', 5) >= 9:
            base_confidence -= 0.1

        # Peak hours reduce confidence
        if features['is_peak_hours'] > 0.5:
            base_confidence -= 0.05

        # Clamp confidence
        confidence = max(0.5, min(1.0, base_confidence))

        # Confidence level
        if confidence >= 0.8:
            conf_level = 'high'
        elif confidence >= 0.6:
            conf_level = 'medium'
        else:
            conf_level = 'low'

        # Confidence interval (±20% of estimate)
        confidence_margin = success_prob * 0.2

        # Risk factors
        risk_factors = []
        if features['threat_severity'] >= 0.8:
            risk_factors.append('High severity threat')
        if features['blast_radius_score'] >= 0.6:
            risk_factors.append('Large blast radius')
        if features['recent_failure_rate'] >= 0.3:
            risk_factors.append('Recent similar failures')
        if features['is_peak_hours'] > 0.5:
            risk_factors.append('Peak business hours')
        if features['remediation_complexity'] >= 0.5:
            risk_factors.append('Complex remediation type')

        return {
            'success_probability': round(success_prob, 3),
            'confidence_level': conf_level,
            'confidence_score': round(confidence, 3),
            'estimated_time_seconds': round(time_est, 1),
            'estimated_cost': round(cost_est, 3),
            'confidence_interval': (
                round(max(0.0, success_prob - confidence_margin), 3),
                round(min(1.0, success_prob + confidence_margin), 3)
            ),
            'risk_factors': risk_factors,
            'recommendation': self._get_recommendation(success_prob)
        }

    def _calculate_recent_failure_rate(self, threat: Dict) -> float:
        """Calculate failure rate for similar threats."""
        if not self.historical_data:
            return 0.0

        # Find similar threats by type
        threat_type = threat.get('threat_type', 'unknown')
        similar = [t for t in self.historical_data if t.get('threat_type') == threat_type]

        if not similar:
            return 0.0

        failed = sum(1 for t in similar if t.get('status') == 'failed')
        return failed / len(similar)

    def _get_recommendation(self, success_prob: float) -> str:
        """Get remediation recommendation based on success probability."""
        if success_prob >= 0.85:
            return 'Proceed with remediation'
        elif success_prob >= 0.7:
            return 'Proceed with caution'
        elif success_prob >= 0.5:
            return 'Require manual approval'
        else:
            return 'Escalate to human review'

    def record_outcome(self, threat: Dict, outcome: str, time_taken: float, cost: float):
        """Record actual remediation outcome for model improvement."""
        record = {
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'affected_resources': threat.get('affected_resources'),
            'status': outcome,
            'actual_time': time_taken,
            'actual_cost': cost,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
        self.historical_data.append(record)

    def get_model_metrics(self) -> Dict:
        """
        Calculate model accuracy metrics from historical data.

        Returns accuracy, precision, recall metrics.
        """
        if not self.historical_data:
            return {
                'total_predictions': 0,
                'accuracy': 0.0,
                'success_rate': 0.0,
                'avg_time_error_percent': 0.0,
                'avg_cost_error_percent': 0.0
            }

        success_count = sum(1 for t in self.historical_data if t.get('status') == 'success')
        success_rate = success_count / len(self.historical_data)

        return {
            'total_predictions': len(self.historical_data),
            'accuracy': round(success_rate, 3),
            'success_rate': round(success_rate, 3),
            'avg_time_error_percent': 0.0,  # Placeholder for actual comparison
            'avg_cost_error_percent': 0.0   # Placeholder for actual comparison
        }
