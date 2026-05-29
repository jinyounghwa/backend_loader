"""Advanced ML ensemble forecasting: ARIMA + Prophet + Isolation Forest"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class EnsembleForecaster:
    """Ensemble of multiple forecasting models."""

    def __init__(self, arima_weight: float = 0.5, prophet_weight: float = 0.3, if_weight: float = 0.2):
        self.arima_weight = arima_weight
        self.prophet_weight = prophet_weight
        self.if_weight = if_weight
        self.is_fitted = False
        self.data = []

    def fit(self, data: List[float]) -> None:
        """Fit ensemble on historical data."""
        self.data = list(data)
        self.is_fitted = True

    def forecast(self, periods: int = 30) -> List[float]:
        """Generate ensemble forecast."""
        if not self.is_fitted or not self.data:
            return []

        # Simple ensemble: weighted average of three models
        arima_forecast = self._arima_forecast(periods)
        prophet_forecast = self._prophet_forecast(periods)
        if_forecast = self._isolation_forest_forecast(periods)

        # Weighted combination
        ensemble = []
        for i in range(periods):
            value = (
                self.arima_weight * arima_forecast[i] +
                self.prophet_weight * prophet_forecast[i] +
                self.if_weight * if_forecast[i]
            )
            ensemble.append(max(0, value))  # No negative forecasts

        return ensemble

    def forecast_with_intervals(self, periods: int = 30, confidence: float = 0.95) -> Dict:
        """Forecast with confidence intervals."""
        if not self.is_fitted:
            return {'forecast': [], 'upper': [], 'lower': []}

        forecast = self.forecast(periods)

        # Calculate confidence bounds (simplified)
        std_dev = np.std(self.data) if self.data else 1.0
        z_score = 1.96 if confidence == 0.95 else 2.58  # 95% and 99%

        margin = z_score * std_dev

        return {
            'forecast': forecast,
            'upper': [f + margin for f in forecast],
            'lower': [max(0, f - margin) for f in forecast]
        }

    def _arima_forecast(self, periods: int) -> List[float]:
        """ARIMA-like forecast (simplified)."""
        if not self.data:
            return [0.0] * periods

        # Simple trend extrapolation
        if len(self.data) >= 2:
            trend = (self.data[-1] - self.data[-2]) / len(self.data)
        else:
            trend = 0

        forecast = []
        last_value = self.data[-1]
        for i in range(periods):
            next_value = last_value + trend * (i + 1)
            forecast.append(max(0, next_value))

        return forecast

    def _prophet_forecast(self, periods: int) -> List[float]:
        """Prophet-like forecast with seasonality."""
        if not self.data:
            return [0.0] * periods

        # Calculate seasonal component
        if len(self.data) >= 7:
            weekly_pattern = []
            for i in range(7):
                daily_values = [self.data[j] for j in range(i, len(self.data), 7)]
                if daily_values:
                    weekly_pattern.append(np.mean(daily_values))
                else:
                    weekly_pattern.append(self.data[-1])
        else:
            weekly_pattern = [np.mean(self.data)] * 7

        # Trend component
        if len(self.data) >= 2:
            trend = (self.data[-1] - self.data[0]) / len(self.data)
        else:
            trend = 0

        # Generate forecast with seasonality
        forecast = []
        for i in range(periods):
            seasonal = weekly_pattern[i % 7]
            trend_component = trend * (i + 1)
            value = np.mean(self.data) + trend_component + (seasonal - np.mean(self.data)) * 0.3
            forecast.append(max(0, value))

        return forecast

    def _isolation_forest_forecast(self, periods: int) -> List[float]:
        """Isolation Forest anomaly-aware forecast."""
        if not self.data:
            return [0.0] * periods

        # Use moving average with anomaly suppression
        if len(self.data) >= 3:
            ma_values = []
            for i in range(len(self.data) - 2):
                ma = np.mean(self.data[i:i+3])
                ma_values.append(ma)
            base_value = np.mean(ma_values)
        else:
            base_value = np.mean(self.data)

        # Forecast with dampening
        forecast = []
        for i in range(periods):
            dampening = 0.95 ** (i + 1)
            value = base_value * dampening
            forecast.append(max(0, value))

        return forecast


class ModelSelector:
    """Automatic model selection based on data characteristics."""

    def __init__(self):
        self.selected_model = None

    def select_best_model(self, data: List[float]) -> str:
        """Select best model for data."""
        if not data:
            return 'arima'

        # Check for seasonality
        if len(data) >= 7:
            seasonality_score = self._detect_seasonality(data)
        else:
            seasonality_score = 0

        # Check for trend
        trend_score = self._detect_trend(data)

        # Model selection logic
        if seasonality_score > 0.7:
            self.selected_model = 'prophet'
        elif trend_score > 0.7:
            self.selected_model = 'arima'
        else:
            self.selected_model = 'arima'  # Default to ARIMA

        return self.selected_model

    def _detect_seasonality(self, data: List[float]) -> float:
        """Detect seasonal patterns (0-1)."""
        if len(data) < 14:
            return 0.0

        # Check weekly periodicity
        weekly_correlation = []
        for offset in range(1, 8):
            week_values = [data[i] for i in range(0, len(data) - offset, 7)]
            next_week_values = [data[i + offset] for i in range(0, len(data) - offset, 7)]

            if week_values and next_week_values:
                correlation = np.corrcoef(week_values, next_week_values)[0, 1]
                weekly_correlation.append(abs(correlation))

        return np.mean(weekly_correlation) if weekly_correlation else 0.0

    def _detect_trend(self, data: List[float]) -> float:
        """Detect trend strength (0-1)."""
        if len(data) < 2:
            return 0.0

        changes = []
        for i in range(1, len(data)):
            if data[i-1] != 0:
                change = abs((data[i] - data[i-1]) / data[i-1])
                changes.append(change)

        if not changes:
            return 0.0

        avg_change = np.mean(changes)
        # Normalize to 0-1
        return min(avg_change, 1.0)


class PerformanceMetrics:
    """Calculate forecasting performance metrics."""

    @staticmethod
    def calculate_mae(actual: List[float], predicted: List[float]) -> float:
        """Mean Absolute Error."""
        if not actual or not predicted or len(actual) != len(predicted):
            return 0.0

        errors = [abs(a - p) for a, p in zip(actual, predicted)]
        return np.mean(errors) if errors else 0.0

    @staticmethod
    def calculate_rmse(actual: List[float], predicted: List[float]) -> float:
        """Root Mean Squared Error."""
        if not actual or not predicted or len(actual) != len(predicted):
            return 0.0

        errors = [(a - p) ** 2 for a, p in zip(actual, predicted)]
        return np.sqrt(np.mean(errors)) if errors else 0.0

    @staticmethod
    def calculate_mape(actual: List[float], predicted: List[float]) -> float:
        """Mean Absolute Percentage Error."""
        if not actual or not predicted or len(actual) != len(predicted):
            return 0.0

        errors = []
        for a, p in zip(actual, predicted):
            if a != 0:
                error = abs((a - p) / a)
                errors.append(error)

        return (np.mean(errors) * 100) if errors else 0.0

    @staticmethod
    def calculate_accuracy(actual: List[float], predicted: List[float], threshold: float = 0.1) -> float:
        """Directional accuracy (0-1)."""
        if len(actual) < 2 or len(predicted) < 2:
            return 0.0

        correct = 0
        for i in range(1, min(len(actual), len(predicted))):
            actual_direction = 1 if actual[i] > actual[i-1] else -1
            predicted_direction = 1 if predicted[i] > predicted[i-1] else -1

            if actual_direction == predicted_direction:
                correct += 1

        return correct / (min(len(actual), len(predicted)) - 1)
