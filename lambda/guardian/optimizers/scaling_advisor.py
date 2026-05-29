"""Auto-scaling advisor: Load prediction and scaling policy recommendations"""

from typing import Dict, List
import numpy as np


class LoadPredictor:
    """Predict future load from historical data."""

    def __init__(self):
        self.history = []

    def fit(self, load_data: List[float]) -> None:
        """Fit predictor on historical load."""
        self.history = list(load_data)

    def predict_peak_load(self, hours_ahead: int = 24) -> float:
        """Predict peak load hours ahead."""
        if not self.history or len(self.history) < 2:
            return 100.0

        trend = (self.history[-1] - self.history[0]) / len(self.history)
        predicted = self.history[-1] + trend * hours_ahead

        return max(0, predicted)

    def predict_average_load(self, hours_ahead: int = 24) -> float:
        """Predict average load hours ahead."""
        if not self.history:
            return 50.0

        avg = np.mean(self.history)
        return max(0, avg)

    def detect_seasonality(self) -> Dict:
        """Detect seasonal patterns in load."""
        if len(self.history) < 7:
            return {'has_seasonality': False}

        daily_patterns = []
        for i in range(7):
            daily_values = [self.history[j] for j in range(i, len(self.history), 7)]
            if daily_values:
                daily_patterns.append(np.mean(daily_values))

        pattern_variance = np.std(daily_patterns)
        has_seasonality = pattern_variance > 10

        return {
            'has_seasonality': has_seasonality,
            'pattern_variance': pattern_variance,
            'daily_patterns': daily_patterns
        }


class AutoScalingAdvisor:
    """Recommend auto-scaling policies."""

    def __init__(self):
        self.load_predictor = LoadPredictor()

    def recommend_policy(self, load_history: List[float]) -> Dict:
        """Recommend auto-scaling policy."""
        self.load_predictor.fit(load_history)

        peak_load = self.load_predictor.predict_peak_load()
        avg_load = self.load_predictor.predict_average_load()
        seasonality = self.load_predictor.detect_seasonality()

        # Calculate target capacity
        target_capacity = peak_load * 1.2  # 20% headroom

        # Scale-up threshold: 70% utilization
        scale_up_threshold = 70
        # Scale-down threshold: 30% utilization
        scale_down_threshold = 30

        return {
            'peak_load': peak_load,
            'average_load': avg_load,
            'target_capacity': target_capacity,
            'scale_up_threshold': scale_up_threshold,
            'scale_down_threshold': scale_down_threshold,
            'has_seasonality': seasonality['has_seasonality'],
            'min_instances': max(1, int(avg_load / 20)),
            'max_instances': max(2, int(target_capacity / 20))
        }


class CostSimulator:
    """Simulate cost changes from configuration changes."""

    def __init__(self):
        self.hourly_rates = {
            't3.medium': 0.0416,
            't3.large': 0.0832,
            't3.xlarge': 0.1664,
            'm5.large': 0.096,
            'c5.large': 0.085,
        }

    def simulate(self, changes: Dict) -> Dict:
        """Simulate cost impact of changes."""
        current_cost = changes.get('current_monthly_cost', 500)
        instance_type = changes.get('instance_type', 't3.medium')
        new_type = changes.get('new_instance_type', 't3.medium')
        purchase_model = changes.get('purchase_model', 'on_demand')
        term = changes.get('term', 1)

        hourly_rate = self.hourly_rates.get(new_type, 0.05)
        monthly_hours = 730  # Average hours per month

        if purchase_model == 'on_demand':
            new_cost = hourly_rate * monthly_hours
        elif purchase_model == 'reserved':
            # 33% discount for 1 year, 50% for 3 year
            discount = 0.33 if term == 1 else 0.50
            new_cost = hourly_rate * monthly_hours * (1 - discount)
        elif purchase_model == 'spot':
            new_cost = hourly_rate * monthly_hours * 0.30  # 70% discount
        else:
            new_cost = hourly_rate * monthly_hours

        monthly_savings = current_cost - new_cost
        annual_savings = monthly_savings * 12

        return {
            'current_cost': current_cost,
            'new_cost': new_cost,
            'monthly_savings': monthly_savings,
            'annual_savings': annual_savings,
            'roi_months': abs(term * 12 / monthly_savings) if monthly_savings > 0 else 0
        }
