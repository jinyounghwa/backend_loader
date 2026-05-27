"""Real-time cost streaming with forecast integration."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Generator
import math

logger = logging.getLogger(__name__)


class CostStreamer:
    """Generate real-time cost updates with trend analysis and forecast comparison."""

    def __init__(self):
        """Initialize cost streamer."""
        self.cost_history = {}
        self.forecast_cache = {}

    def get_current_cost(self, cost_value: float, historical_costs: List[float]) -> Dict[str, Any]:
        """
        Get current cost snapshot with trend analysis.

        Args:
            cost_value: Current cost value
            historical_costs: List of historical costs (for trend calculation)

        Returns:
            Cost snapshot with trend and volatility
        """
        try:
            if not historical_costs or len(historical_costs) < 2:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "current_cost": round(cost_value, 2),
                    "trend": "→",
                    "trend_percent": 0.0,
                    "volatility_index": 0.0,
                }

            # Calculate trend (compare to previous)
            previous_cost = historical_costs[-1]
            trend_change = cost_value - previous_cost
            trend_percent = (trend_change / previous_cost * 100) if previous_cost > 0 else 0

            # Determine trend symbol
            if trend_change > 0:
                trend = "↑"
            elif trend_change < 0:
                trend = "↓"
            else:
                trend = "→"

            # Calculate volatility (standard deviation / mean)
            avg_cost = sum(historical_costs) / len(historical_costs)
            variance = sum((c - avg_cost) ** 2 for c in historical_costs) / len(historical_costs)
            std_dev = math.sqrt(variance)
            volatility_index = (std_dev / avg_cost) if avg_cost > 0 else 0.0

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_cost": round(cost_value, 2),
                "previous_cost": round(previous_cost, 2),
                "trend": trend,
                "trend_percent": round(trend_percent, 2),
                "volatility_index": round(volatility_index, 3),
            }

        except Exception as e:
            logger.error(f"Error getting current cost: {e}")
            return {"error": str(e)}

    def stream_cost_updates(
        self,
        historical_costs: List[float],
        forecast_values: List[float],
        interval_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate simulated cost stream with forecast comparison.

        Args:
            historical_costs: Historical cost data
            forecast_values: Forecasted costs from Phase 1
            interval_count: Number of updates to generate

        Returns:
            Stream of cost updates with forecast comparison
        """
        try:
            if not historical_costs or not forecast_values:
                return []

            stream = []
            base_cost = historical_costs[-1] if historical_costs else 1000.0

            for i in range(interval_count):
                # Simulate cost update (slight variation around base)
                trend = (i - interval_count // 2) * 10  # Upward/downward trend
                noise = (i % 3 - 1) * 20  # Small random variation
                simulated_cost = base_cost + trend + noise

                # Get current cost info
                cost_info = self.get_current_cost(simulated_cost, historical_costs + [simulated_cost])

                # Calculate variance from forecast
                expected_forecast = forecast_values[min(i, len(forecast_values) - 1)]
                variance_info = self.calculate_cost_variance(simulated_cost, expected_forecast)

                # Combine into stream update
                update = {
                    "interval": i + 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cost_info": cost_info,
                    "variance": variance_info,
                    "alert": variance_info.get("is_anomaly", False),
                }

                stream.append(update)

            return stream

        except Exception as e:
            logger.error(f"Error generating cost stream: {e}")
            return []

    def calculate_cost_variance(
        self, actual_cost: float, forecast_cost: float, anomaly_threshold: float = 0.15
    ) -> Dict[str, Any]:
        """
        Calculate variance between actual and forecast cost.

        Args:
            actual_cost: Actual observed cost
            forecast_cost: Forecasted cost from Phase 1
            anomaly_threshold: Threshold for anomaly detection (15% default)

        Returns:
            Variance analysis with anomaly flag
        """
        try:
            if forecast_cost <= 0:
                return {
                    "variance_percent": 0.0,
                    "variance_amount": 0.0,
                    "is_anomaly": False,
                    "severity": "none",
                }

            # Calculate variance
            variance_amount = actual_cost - forecast_cost
            variance_percent = (variance_amount / forecast_cost) * 100

            # Determine anomaly status
            abs_variance_percent = abs(variance_percent)
            is_anomaly = abs_variance_percent > (anomaly_threshold * 100)

            # Determine severity
            if not is_anomaly:
                severity = "none"
            elif abs_variance_percent < 25:
                severity = "warning"
            else:
                severity = "critical"

            return {
                "actual_cost": round(actual_cost, 2),
                "forecast_cost": round(forecast_cost, 2),
                "variance_amount": round(variance_amount, 2),
                "variance_percent": round(variance_percent, 2),
                "is_anomaly": is_anomaly,
                "anomaly_threshold_percent": anomaly_threshold * 100,
                "severity": severity,
                "status": "over" if variance_amount > 0 else "under",
            }

        except Exception as e:
            logger.error(f"Error calculating cost variance: {e}")
            return {}

    def detect_anomalies(
        self,
        cost_values: List[float],
        forecast_values: List[float],
        confidence_intervals: List[Dict[str, float]],
    ) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies using forecast confidence intervals.

        Args:
            cost_values: Actual cost values
            forecast_values: Forecasted costs
            confidence_intervals: Confidence intervals from Phase 1 (lower_bound, upper_bound)

        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []

            for i, actual_cost in enumerate(cost_values):
                if i >= len(forecast_values):
                    break

                forecast_cost = forecast_values[i]
                ci = confidence_intervals[i] if i < len(confidence_intervals) else None

                if ci:
                    lower_bound = ci.get("lower_bound", forecast_cost * 0.9)
                    upper_bound = ci.get("upper_bound", forecast_cost * 1.1)

                    # Check if actual is outside 95% confidence interval
                    if actual_cost < lower_bound or actual_cost > upper_bound:
                        variance_percent = ((actual_cost - forecast_cost) / forecast_cost) * 100
                        anomalies.append(
                            {
                                "period": i,
                                "actual_cost": round(actual_cost, 2),
                                "forecast_cost": round(forecast_cost, 2),
                                "lower_bound": round(lower_bound, 2),
                                "upper_bound": round(upper_bound, 2),
                                "variance_percent": round(variance_percent, 2),
                                "severity": "critical" if abs(variance_percent) > 25 else "warning",
                            }
                        )

            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def generate_cost_report(
        self,
        historical_costs: List[float],
        forecast_values: List[float],
        current_cost: float,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive cost report with forecast comparison.

        Args:
            historical_costs: Historical cost data
            forecast_values: Forecasted costs
            current_cost: Most recent cost

        Returns:
            Comprehensive report
        """
        try:
            if not historical_costs:
                return {"error": "No historical costs provided"}

            avg_cost = sum(historical_costs) / len(historical_costs)
            min_cost = min(historical_costs)
            max_cost = max(historical_costs)

            # Calculate variance for current vs forecast
            current_forecast = forecast_values[0] if forecast_values else avg_cost
            current_variance = self.calculate_cost_variance(current_cost, current_forecast)

            # Calculate forecast accuracy
            forecast_errors = []
            for i, historical in enumerate(historical_costs):
                if i < len(forecast_values):
                    error = abs(historical - forecast_values[i]) / forecast_values[i] * 100
                    forecast_errors.append(error)

            avg_forecast_error = sum(forecast_errors) / len(forecast_errors) if forecast_errors else 0

            return {
                "report_date": datetime.now(timezone.utc).isoformat(),
                "current_cost": round(current_cost, 2),
                "average_cost": round(avg_cost, 2),
                "min_cost": round(min_cost, 2),
                "max_cost": round(max_cost, 2),
                "cost_range": round(max_cost - min_cost, 2),
                "current_vs_forecast": current_variance,
                "forecast_accuracy": {
                    "average_error_percent": round(avg_forecast_error, 2),
                    "data_points": len(forecast_errors),
                },
                "trend": "↑" if current_cost > avg_cost else "↓",
                "summary": f"Current: ${current_cost:.0f}, Avg: ${avg_cost:.0f}, Forecast accuracy: {100 - avg_forecast_error:.1f}%",
            }

        except Exception as e:
            logger.error(f"Error generating cost report: {e}")
            return {"error": str(e)}
