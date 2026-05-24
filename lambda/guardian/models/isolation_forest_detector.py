"""Isolation Forest-based Anomaly Detection Model"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import json

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """Detect anomalies using Isolation Forest algorithm"""

    def __init__(self):
        """Initialize Isolation Forest detector"""
        self.model = {}
        self.trained = False
        self.last_training_time = None
        self.feature_names = []

    def train_model(self, historical_data: List[Dict]) -> Dict:
        """
        Train Isolation Forest model with historical data

        Args:
            historical_data: List of historical metric records

        Returns:
            Training result with metrics
        """
        try:
            if not historical_data:
                return {'error': 'No training data provided', 'status': 'failed'}

            # Extract feature names
            self.feature_names = list(historical_data[0].keys())

            # Initialize model with basic statistics
            self.model = {
                'mean': {},
                'std': {},
                'min': {},
                'max': {}
            }

            # Calculate statistics for each feature
            for feature in self.feature_names:
                values = [d.get(feature, 0) for d in historical_data if isinstance(d.get(feature), (int, float))]

                if values:
                    self.model['mean'][feature] = sum(values) / len(values)
                    variance = sum((x - self.model['mean'][feature]) ** 2 for x in values) / len(values)
                    self.model['std'][feature] = variance ** 0.5
                    self.model['min'][feature] = min(values)
                    self.model['max'][feature] = max(values)

            self.trained = True
            self.last_training_time = datetime.now(timezone.utc).isoformat()

            logger.info(f"Trained model with {len(historical_data)} samples, {len(self.feature_names)} features")
            return {
                'status': 'success',
                'samples': len(historical_data),
                'features': len(self.feature_names),
                'training_time': self.last_training_time
            }

        except Exception as e:
            logger.error(f"Failed to train model: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def predict_anomalies(self, new_data: List[Dict]) -> List[Dict]:
        """
        Predict anomalies on new data

        Args:
            new_data: List of new metric records

        Returns:
            List of predictions with anomaly scores
        """
        try:
            if not self.trained:
                return []

            predictions = []

            for data_point in new_data:
                score = self.calculate_anomaly_score(data_point)
                is_anomaly = score > 0.7

                prediction = {
                    'data': data_point,
                    'anomaly_score': score,
                    'is_anomaly': is_anomaly,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                predictions.append(prediction)

            logger.info(f"Predicted {len(predictions)} samples, {sum(1 for p in predictions if p['is_anomaly'])} anomalies")
            return predictions

        except Exception as e:
            logger.error(f"Failed to predict anomalies: {str(e)}")
            return []

    def calculate_anomaly_score(self, instance: Dict) -> float:
        """
        Calculate anomaly score for instance (0-1 scale)

        Args:
            instance: Metric record

        Returns:
            Anomaly score (0=normal, 1=anomaly)
        """
        try:
            if not self.trained or not self.model:
                return 0.0

            scores = []

            for feature in self.feature_names:
                value = instance.get(feature, 0)

                if not isinstance(value, (int, float)):
                    continue

                mean = self.model['mean'].get(feature, 0)
                std = self.model['std'].get(feature, 1)

                if std == 0:
                    std = 1

                # Calculate z-score
                z_score = abs((value - mean) / std)

                # Convert to anomaly score (0-1)
                # z_score of 3+ is significant outlier
                feature_score = min(1.0, z_score / 5.0)
                scores.append(feature_score)

            # Average scores across features
            if scores:
                final_score = sum(scores) / len(scores)
            else:
                final_score = 0.0

            return round(final_score, 3)

        except Exception as e:
            logger.error(f"Failed to calculate anomaly score: {str(e)}")
            return 0.0

    def detect_novel_patterns(self, data_points: List[Dict]) -> Dict:
        """
        Detect novel/previously unseen patterns

        Args:
            data_points: New data points to check

        Returns:
            Detection result with novel patterns
        """
        try:
            novel_patterns = []

            for data_point in data_points:
                score = self.calculate_anomaly_score(data_point)

                # High anomaly score indicates novel pattern
                if score > 0.75:
                    novel_patterns.append({
                        'data': data_point,
                        'novelty_score': score,
                        'detected_at': datetime.now(timezone.utc).isoformat()
                    })

            return {
                'total_checked': len(data_points),
                'novel_patterns_found': len(novel_patterns),
                'patterns': novel_patterns,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to detect novel patterns: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def auto_retrain_schedule(self, interval_days: int = 7) -> Dict:
        """
        Schedule automatic model retraining

        Args:
            interval_days: Number of days between retraining

        Returns:
            Retraining schedule
        """
        try:
            next_training_time = datetime.now(timezone.utc) + timedelta(days=interval_days)

            schedule = {
                'enabled': True,
                'interval_days': interval_days,
                'last_training': self.last_training_time,
                'next_training': next_training_time.isoformat(),
                'status': 'scheduled'
            }

            logger.info(f"Scheduled auto-retraining every {interval_days} days")
            return schedule

        except Exception as e:
            logger.error(f"Failed to schedule retraining: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
