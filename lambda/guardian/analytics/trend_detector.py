"""Trend Detection for time-series anomaly analysis."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TrendDetector:
    """Detects trends in time-series data."""

    def __init__(self, window_size: int = 24):
        """Initialize trend detector with window size (hours)."""
        self.window_size = window_size
        self.trends_history = {}

    def analyze_trend(self, data_points: List[Tuple[float, str]]) -> Dict[str, Any]:
        """
        Analyze trend from data points.

        Args:
            data_points: List of (value, timestamp) tuples

        Returns:
            Dict with trend_type, slope, r_squared, direction
        """
        if len(data_points) < 2:
            return {
                "trend_type": "INSUFFICIENT_DATA",
                "slope": 0.0,
                "r_squared": 0.0,
                "direction": "FLAT",
                "confidence": 0.0,
            }

        # Extract values for linear regression
        values = [float(v) for v, _ in data_points]
        x = list(range(len(values)))
        y = values

        # Calculate linear regression
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        # Slope calculation
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
            r_squared = 0.0
        else:
            slope = numerator / denominator

            # R-squared calculation
            ss_res = sum((y[i] - (slope * x[i] + (mean_y - slope * mean_x))) ** 2 for i in range(n))
            ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Determine trend type and direction
        if abs(slope) < 0.01:
            trend_type = "STABLE"
            direction = "FLAT"
        elif slope > 0:
            trend_type = "INCREASING"
            if slope > 0.1:
                direction = "SHARP_UP"
            else:
                direction = "GRADUAL_UP"
        else:
            trend_type = "DECREASING"
            if slope < -0.1:
                direction = "SHARP_DOWN"
            else:
                direction = "GRADUAL_DOWN"

        # Confidence based on R-squared (fit quality)
        confidence = min(abs(r_squared), 1.0)

        return {
            "trend_type": trend_type,
            "slope": round(slope, 4),
            "r_squared": round(r_squared, 4),
            "direction": direction,
            "confidence": round(confidence, 2),
            "data_points": len(data_points),
        }

    def detect_trend_change(self, current_trend: Dict[str, Any], previous_trend: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if trend has changed significantly.

        Returns:
            Dict with change_detected, change_type, severity
        """
        if not previous_trend:
            return {"change_detected": False, "change_type": "NONE", "severity": "NONE"}

        current_direction = current_trend.get("direction", "FLAT")
        previous_direction = previous_trend.get("direction", "FLAT")

        current_slope = current_trend.get("slope", 0.0)
        previous_slope = previous_trend.get("slope", 0.0)

        # Check for direction change
        direction_changed = current_direction != previous_direction
        slope_magnitude_change = abs(current_slope - previous_slope)

        if direction_changed:
            if "UP" in current_direction and "DOWN" in previous_direction:
                change_type = "REVERSAL_UP"
                severity = "HIGH" if slope_magnitude_change > 0.2 else "MEDIUM"
            elif "DOWN" in current_direction and "UP" in previous_direction:
                change_type = "REVERSAL_DOWN"
                severity = "HIGH" if slope_magnitude_change > 0.2 else "MEDIUM"
            else:
                change_type = "DIRECTION_CHANGE"
                severity = "MEDIUM"

            return {"change_detected": True, "change_type": change_type, "severity": severity}

        # Check for slope magnitude change
        if slope_magnitude_change > 0.3:
            change_type = "ACCELERATION" if abs(current_slope) > abs(previous_slope) else "DECELERATION"
            severity = "MEDIUM"
            return {"change_detected": True, "change_type": change_type, "severity": severity}

        return {"change_detected": False, "change_type": "NONE", "severity": "NONE"}

    def forecast_next_value(self, data_points: List[Tuple[float, str]], periods: int = 1) -> List[float]:
        """
        Forecast next values using linear regression.

        Args:
            data_points: Historical data points
            periods: Number of periods to forecast

        Returns:
            List of forecasted values
        """
        if len(data_points) < 2:
            return [data_points[-1][0] if data_points else 0.0] * periods

        values = [float(v) for v, _ in data_points]
        x = list(range(len(values)))
        y = values

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        intercept = mean_y - slope * mean_x

        # Forecast future values
        forecasts = []
        last_x = len(x)
        for i in range(1, periods + 1):
            forecast_value = slope * (last_x + i) + intercept
            forecasts.append(max(0.0, forecast_value))  # Ensure non-negative

        return forecasts

    def get_trend_summary(self, data_points: List[Tuple[float, str]]) -> Dict[str, Any]:
        """Get comprehensive trend summary."""
        if not data_points:
            return {}

        trend = self.analyze_trend(data_points)
        values = [float(v) for v, _ in data_points]

        return {
            **trend,
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": sum(values) / len(values),
            "volatility": self._calculate_volatility(values),
        }

    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of values."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        volatility = variance ** 0.5

        return round(volatility, 4)
