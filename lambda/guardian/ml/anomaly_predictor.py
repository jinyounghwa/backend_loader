"""Predict future anomalies using ML."""

from typing import Dict, List, Any, Optional
from collections import defaultdict


class AnomalyPredictor:
    """Predict anomalies in next 24 hours."""

    def __init__(self):
        self.anomalies: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.temporal_patterns: Dict[int, int] = defaultdict(int)

    def record_anomaly(self, anomaly: Dict[str, Any]) -> None:
        """Record an anomaly."""
        user = anomaly.get('user')
        if user:
            self.anomalies[user].append(anomaly)

        # Record temporal patterns
        day = anomaly.get('day_of_week')
        if day is not None:
            self.temporal_patterns[day] += 1

    def predict_anomaly_probability(self, user: str) -> float:
        """Predict probability of anomaly in next 24 hours."""
        if user not in self.anomalies:
            return 0.0

        anomaly_count = len(self.anomalies[user])

        # Simple probability: # of past anomalies / window
        if anomaly_count == 0:
            return 0.0
        elif anomaly_count == 1:
            return 0.35
        elif anomaly_count == 2:
            return 0.5
        else:
            return min(0.95, 0.5 + (anomaly_count - 2) * 0.1)

    def predict_severity(self, pattern: Dict[str, Any]) -> str:
        """Predict severity of anomaly."""
        threat_type = pattern.get('type')

        if threat_type == 'MALWARE':
            return 'CRITICAL'
        elif threat_type == 'UNAUTHORIZED':
            return 'HIGH'
        else:
            return 'MEDIUM'

    def predict_for_day(self, day_of_week: int) -> float:
        """Predict anomaly probability for specific day."""
        count = self.temporal_patterns.get(day_of_week, 0)

        if count == 0:
            return 0.1
        elif count == 1:
            return 0.55
        elif count < 4:
            return 0.65 + (count - 2) * 0.1
        else:
            return min(0.95, 0.8 + (count - 4) * 0.05)
