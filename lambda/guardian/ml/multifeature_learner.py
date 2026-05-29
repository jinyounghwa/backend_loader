"""Multi-feature learning: Process 10+ features for ML predictions"""

import numpy as np
from typing import Dict, List, Tuple, Any
from collections import defaultdict


class MultiFeatureLearner:
    """Learn patterns from multiple features."""

    def __init__(self, min_feature_count: int = 5):
        self.min_feature_count = min_feature_count
        self.features: Dict[str, List[float]] = {}
        self.feature_stats: Dict[str, Dict[str, float]] = {}
        self.is_fitted = False

    def fit(self, features: Dict[str, List[float]]) -> None:
        """Fit learner on features."""
        if len(features) < self.min_feature_count:
            raise ValueError(f"Minimum {self.min_feature_count} features required")

        self.features = features
        self._calculate_stats()
        self.is_fitted = True

    def _calculate_stats(self) -> None:
        """Calculate statistics for each feature."""
        self.feature_stats = {}

        for feature_name, values in self.features.items():
            if not values:
                continue

            self.feature_stats[feature_name] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values),
                'count': len(values)
            }

    def get_feature_importance(self) -> Dict[str, float]:
        """Calculate feature importance using variance."""
        if not self.is_fitted:
            return {}

        importance = {}
        total_variance = 0

        # Calculate variance for each feature
        for feature_name, stats in self.feature_stats.items():
            variance = stats['std'] ** 2
            importance[feature_name] = variance
            total_variance += variance

        # Normalize to 0-1
        if total_variance > 0:
            importance = {k: v / total_variance for k, v in importance.items()}

        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def normalize_features(self) -> Dict[str, List[float]]:
        """Normalize features to 0-1 range."""
        if not self.is_fitted:
            return {}

        normalized = {}

        for feature_name, values in self.features.items():
            stats = self.feature_stats[feature_name]
            range_val = stats['max'] - stats['min']

            if range_val == 0:
                # All values are the same
                normalized[feature_name] = [0.5] * len(values)
            else:
                normalized[feature_name] = [
                    (v - stats['min']) / range_val for v in values
                ]

        return normalized

    def correlate_features(self) -> Dict[Tuple[str, str], float]:
        """Calculate correlation between features."""
        if not self.is_fitted or len(self.features) < 2:
            return {}

        correlations = {}
        feature_names = list(self.features.keys())

        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                feat1 = feature_names[i]
                feat2 = feature_names[j]

                values1 = self.features[feat1]
                values2 = self.features[feat2]

                if len(values1) == len(values2) and len(values1) > 1:
                    correlation = np.corrcoef(values1, values2)[0, 1]
                    if not np.isnan(correlation):
                        correlations[(feat1, feat2)] = correlation

        return correlations

    def detect_anomalies(self, threshold: float = 2.0) -> Dict[str, List[int]]:
        """Detect anomalous values using z-score."""
        if not self.is_fitted:
            return {}

        anomalies = defaultdict(list)

        for feature_name, values in self.features.items():
            stats = self.feature_stats[feature_name]
            mean = stats['mean']
            std = stats['std']

            if std == 0:
                continue

            for idx, value in enumerate(values):
                z_score = abs((value - mean) / std)
                if z_score > threshold:
                    anomalies[feature_name].append(idx)

        return dict(anomalies)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all features."""
        if not self.is_fitted:
            return {}

        return {
            'feature_count': len(self.features),
            'feature_names': list(self.features.keys()),
            'feature_stats': self.feature_stats,
            'feature_importance': self.get_feature_importance(),
            'correlations': self.correlate_features()
        }


class FeatureProcessor:
    """Process and prepare features for ML."""

    @staticmethod
    def handle_missing_values(values: List[float], method: str = 'mean') -> List[float]:
        """Handle missing values (None or NaN)."""
        if not values:
            return []

        # Replace None with placeholder
        numeric_values = [v for v in values if v is not None and not np.isnan(v)]

        if not numeric_values:
            return [0.0] * len(values)

        if method == 'mean':
            fill_value = np.mean(numeric_values)
        elif method == 'median':
            fill_value = np.median(numeric_values)
        elif method == 'zero':
            fill_value = 0.0
        else:
            fill_value = np.mean(numeric_values)

        return [v if v is not None and not np.isnan(v) else fill_value for v in values]

    @staticmethod
    def remove_outliers(values: List[float], z_threshold: float = 3.0) -> List[float]:
        """Remove outliers using z-score."""
        if not values or len(values) < 2:
            return values

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return values

        filtered = []
        for v in values:
            z_score = abs((v - mean) / std)
            if z_score <= z_threshold:
                filtered.append(v)

        return filtered if filtered else values

    @staticmethod
    def scale_features(values: List[float], method: str = 'minmax') -> List[float]:
        """Scale features to standard range."""
        if not values:
            return []

        if method == 'minmax':
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val

            if range_val == 0:
                return [0.5] * len(values)

            return [(v - min_val) / range_val for v in values]

        elif method == 'zscore':
            mean = np.mean(values)
            std = np.std(values)

            if std == 0:
                return [0.0] * len(values)

            return [(v - mean) / std for v in values]

        return values

    @staticmethod
    def create_lagged_features(values: List[float], lag: int = 1) -> Dict[str, List[float]]:
        """Create lagged features for time series."""
        if not values or lag < 1:
            return {}

        lagged = {}
        for i in range(1, lag + 1):
            lagged_name = f'lag_{i}'
            lagged[lagged_name] = [None] * i + values[:-i]

        return lagged


class FeatureImportance:
    """Calculate feature importance using multiple methods."""

    @staticmethod
    def variance_based(features: Dict[str, List[float]]) -> Dict[str, float]:
        """Feature importance based on variance."""
        importance = {}
        total_variance = 0

        for name, values in features.items():
            variance = np.var(values) if values else 0
            importance[name] = variance
            total_variance += variance

        if total_variance > 0:
            importance = {k: v / total_variance for k, v in importance.items()}

        return importance

    @staticmethod
    def correlation_based(features: Dict[str, List[float]], target_name: str = None) -> Dict[str, float]:
        """Feature importance based on correlation with target."""
        if not features or target_name not in features:
            return {}

        target = features[target_name]
        importance = {}

        for name, values in features.items():
            if name == target_name or len(values) != len(target):
                continue

            correlation = np.corrcoef(values, target)[0, 1]
            importance[name] = abs(correlation) if not np.isnan(correlation) else 0

        return importance

    @staticmethod
    def entropy_based(features: Dict[str, List[float]]) -> Dict[str, float]:
        """Feature importance based on entropy."""
        importance = {}

        for name, values in features.items():
            if not values:
                importance[name] = 0
                continue

            # Calculate entropy (simplified)
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val

            if range_val == 0:
                importance[name] = 0
            else:
                # Normalize values
                normalized = [(v - min_val) / range_val for v in values]
                entropy = -sum([p * np.log(max(p, 1e-10)) for p in normalized]) / len(values)
                importance[name] = entropy

        return importance
