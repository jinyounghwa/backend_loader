"""Time-Series Forecasting for anomaly prediction."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TimeSeriesForecast:
    """Forecasts future values and anomalies in time-series."""

    def __init__(self):
        """Initialize forecasting engine."""
        self.forecast_history = {}

    def exponential_smoothing(
        self, data_points: List[Tuple[float, str]], alpha: float = 0.3, periods: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Forecast using exponential smoothing.

        Args:
            data_points: Historical data points
            alpha: Smoothing factor (0-1, default 0.3)
            periods: Number of periods to forecast

        Returns:
            List of forecasted values with confidence intervals
        """
        if len(data_points) < 2:
            return []

        values = [float(v) for v, _ in data_points]

        # Initialize with first value
        level = values[0]
        forecasts = []

        # Apply exponential smoothing
        for i in range(1, len(values)):
            level = alpha * values[i] + (1 - alpha) * level

        # Generate forecasts
        for period in range(1, periods + 1):
            forecast_value = level
            confidence = max(0.5, 1.0 - (period * 0.1))  # Decrease confidence over time

            forecasts.append({
                "period": period,
                "forecast": round(forecast_value, 2),
                "confidence": round(confidence, 2),
                "lower_bound": round(max(0.0, forecast_value * 0.8), 2),
                "upper_bound": round(forecast_value * 1.2, 2),
            })

        return forecasts

    def moving_average_forecast(
        self, data_points: List[Tuple[float, str]], window: int = 3, periods: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Forecast using moving average.

        Args:
            data_points: Historical data points
            window: Moving average window size
            periods: Number of periods to forecast

        Returns:
            List of forecasted values
        """
        if len(data_points) < window:
            return []

        values = [float(v) for v, _ in data_points]

        # Calculate moving average
        moving_avg = sum(values[-window:]) / window

        forecasts = []
        for period in range(1, periods + 1):
            forecast_value = moving_avg
            confidence = max(0.5, 1.0 - (period * 0.1))

            forecasts.append({
                "period": period,
                "forecast": round(forecast_value, 2),
                "confidence": round(confidence, 2),
                "lower_bound": round(max(0.0, forecast_value * 0.85), 2),
                "upper_bound": round(forecast_value * 1.15, 2),
            })

        return forecasts

    def adaptive_forecast(self, data_points: List[Tuple[float, str]], periods: int = 5) -> Dict[str, Any]:
        """
        Adaptive forecast combining multiple methods.

        Returns:
            Combined forecast with multiple model predictions
        """
        if len(data_points) < 3:
            return {"forecast_available": False}

        exp_smoothing = self.exponential_smoothing(data_points, alpha=0.3, periods=periods)
        moving_avg = self.moving_average_forecast(data_points, window=min(3, len(data_points) - 1), periods=periods)

        # Combine forecasts (equal weight)
        combined_forecasts = []
        for i in range(periods):
            if i < len(exp_smoothing) and i < len(moving_avg):
                combined_value = (exp_smoothing[i]["forecast"] + moving_avg[i]["forecast"]) / 2
                min_confidence = min(exp_smoothing[i]["confidence"], moving_avg[i]["confidence"])

                combined_forecasts.append({
                    "period": i + 1,
                    "forecast": round(combined_value, 2),
                    "confidence": round(min_confidence, 2),
                    "exp_smoothing": exp_smoothing[i]["forecast"],
                    "moving_average": moving_avg[i]["forecast"],
                    "lower_bound": round(max(0.0, combined_value * 0.8), 2),
                    "upper_bound": round(combined_value * 1.2, 2),
                })

        return {
            "forecast_available": True,
            "method": "adaptive",
            "forecasts": combined_forecasts,
            "model_count": 2,
        }

    def forecast_anomaly_probability(
        self, forecast: List[Dict[str, Any]], current_value: float, threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Calculate probability of anomaly based on forecast.

        Returns:
            Dict with anomaly_probability, risk_level, recommended_action
        """
        if not forecast:
            return {"anomaly_probability": 0.0, "risk_level": "NONE"}

        latest_forecast = forecast[0]
        forecast_value = latest_forecast["forecast"]
        lower_bound = latest_forecast["lower_bound"]
        upper_bound = latest_forecast["upper_bound"]

        # Check if current value is within bounds
        if lower_bound <= current_value <= upper_bound:
            anomaly_probability = 0.0
            risk_level = "NONE"
        elif current_value < lower_bound:
            deviation = (lower_bound - current_value) / lower_bound if lower_bound > 0 else 0
            anomaly_probability = min(1.0, deviation * 2)
            risk_level = "MEDIUM" if anomaly_probability > 0.3 else "LOW"
        else:  # current_value > upper_bound
            deviation = (current_value - upper_bound) / upper_bound if upper_bound > 0 else 0
            anomaly_probability = min(1.0, deviation * 2)
            risk_level = "HIGH" if anomaly_probability > 0.7 else "MEDIUM" if anomaly_probability > 0.3 else "LOW"

        return {
            "anomaly_probability": round(anomaly_probability, 2),
            "risk_level": risk_level,
            "current_value": current_value,
            "forecast_value": forecast_value,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "deviation_percentage": round(((current_value - forecast_value) / forecast_value * 100) if forecast_value > 0 else 0, 2),
        }

    def detect_forecast_drift(
        self, previous_forecast: List[Dict[str, Any]], current_forecast: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect significant changes in forecast.

        Returns:
            Dict with drift_detected, drift_severity, change_analysis
        """
        if not previous_forecast or not current_forecast:
            return {"drift_detected": False}

        previous_value = previous_forecast[0]["forecast"]
        current_value = current_forecast[0]["forecast"]

        change_percentage = ((current_value - previous_value) / previous_value * 100) if previous_value > 0 else 0

        if abs(change_percentage) > 50:
            drift_detected = True
            drift_severity = "HIGH" if abs(change_percentage) > 100 else "MEDIUM"
        elif abs(change_percentage) > 20:
            drift_detected = True
            drift_severity = "MEDIUM"
        else:
            drift_detected = False
            drift_severity = "NONE"

        return {
            "drift_detected": drift_detected,
            "drift_severity": drift_severity,
            "change_percentage": round(change_percentage, 2),
            "previous_forecast": previous_value,
            "current_forecast": current_value,
        }

    def get_forecast_summary(self, data_points: List[Tuple[float, str]]) -> Dict[str, Any]:
        """Get comprehensive forecast summary."""
        values = [float(v) for v, _ in data_points]

        if not values:
            return {}

        adaptive = self.adaptive_forecast(data_points, periods=5)

        return {
            "current_value": values[-1],
            "historical_min": min(values),
            "historical_max": max(values),
            "historical_avg": sum(values) / len(values),
            "data_points_used": len(data_points),
            "forecast": adaptive,
        }
