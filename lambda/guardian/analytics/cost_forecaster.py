"""Cost Forecasting for AWS spending prediction."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CostForecaster:
    """Forecasts AWS costs based on historical data."""

    def __init__(self):
        """Initialize cost forecaster."""
        self.forecasts = {}

    def forecast_daily_cost(self, historical_costs: List[Tuple[float, str]], days: int = 30) -> Dict[str, Any]:
        """
        Forecast daily costs for next N days.

        Args:
            historical_costs: List of (cost, date) tuples
            days: Number of days to forecast

        Returns:
            Dict with daily forecasts and confidence intervals
        """
        if len(historical_costs) < 3:
            return {"forecast_available": False}

        costs = [float(c) for c, _ in historical_costs]

        # Calculate statistics
        mean_cost = sum(costs) / len(costs)
        min_cost = min(costs)
        max_cost = max(costs)
        std_dev = (sum((x - mean_cost) ** 2 for x in costs) / len(costs)) ** 0.5

        # Simple linear trend
        trend = self._calculate_trend(costs)

        forecasts = []
        for day in range(1, days + 1):
            # Forecast = mean + (trend * days)
            forecast_value = mean_cost + (trend * day)
            # Add confidence interval (decreasing over time)
            confidence = max(0.5, 1.0 - (day * 0.02))
            lower_bound = max(0.0, forecast_value - (std_dev * 1.5))
            upper_bound = forecast_value + (std_dev * 1.5)

            forecasts.append(
                {
                    "day": day,
                    "forecast": round(forecast_value, 2),
                    "lower_bound": round(lower_bound, 2),
                    "upper_bound": round(upper_bound, 2),
                    "confidence": round(confidence, 2),
                }
            )

        return {
            "forecast_available": True,
            "mean_historical_cost": round(mean_cost, 2),
            "trend": round(trend, 4),
            "forecasts": forecasts,
        }

    def forecast_monthly_cost(self, daily_forecasts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate monthly cost forecast from daily forecasts.

        Returns:
            Dict with monthly total forecast and statistics
        """
        if not daily_forecasts.get("forecasts"):
            return {"forecast_available": False}

        forecasts = daily_forecasts["forecasts"]
        forecast_values = [f["forecast"] for f in forecasts]

        total = sum(forecast_values)
        avg = total / len(forecast_values) if forecast_values else 0
        min_val = min(forecast_values)
        max_val = max(forecast_values)
        lower_total = sum(f["lower_bound"] for f in forecasts)
        upper_total = sum(f["upper_bound"] for f in forecasts)

        return {
            "forecast_available": True,
            "total_forecast": round(total, 2),
            "daily_average": round(avg, 2),
            "min_daily": round(min_val, 2),
            "max_daily": round(max_val, 2),
            "lower_bound_total": round(lower_total, 2),
            "upper_bound_total": round(upper_total, 2),
            "days_forecasted": len(forecasts),
        }

    def predict_cost_after_action(self, current_costs: List[float], action_type: str, action_impact: float) -> Dict[str, Any]:
        """
        Predict costs after executing an action.

        Args:
            current_costs: Historical costs
            action_type: Type of action (e.g., 'stop_ec2', 'reduce_nat')
            action_impact: Expected percentage reduction (0-1)

        Returns:
            Dict with projected costs
        """
        if not current_costs:
            return {}

        current_avg = sum(current_costs) / len(current_costs)
        projected_avg = current_avg * (1 - action_impact)
        current_monthly = current_avg * 30
        projected_monthly = projected_avg * 30
        monthly_savings = current_monthly - projected_monthly

        return {
            "action_type": action_type,
            "current_daily_average": round(current_avg, 2),
            "projected_daily_average": round(projected_avg, 2),
            "daily_savings": round(current_avg - projected_avg, 2),
            "current_monthly_cost": round(current_monthly, 2),
            "projected_monthly_cost": round(projected_monthly, 2),
            "monthly_savings": round(monthly_savings, 2),
            "annual_savings": round(monthly_savings * 12, 2),
            "impact_percentage": round(action_impact * 100, 2),
        }

    def estimate_savings_potential(self, costs_by_service: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Estimate savings potential across services.

        Returns:
            List of optimization opportunities sorted by potential savings
        """
        opportunities = []

        # Define savings potential by service
        savings_matrix = {
            "ec2": {"max_savings": 0.40, "reason": "Reserved instances, Spot instances"},
            "rds": {"max_savings": 0.35, "reason": "Reserved instances"},
            "s3": {"max_savings": 0.20, "reason": "Lifecycle policies, S3 Intelligent-Tiering"},
            "nat_gateway": {"max_savings": 0.50, "reason": "NAT instance alternative"},
            "cloudwatch": {"max_savings": 0.25, "reason": "Log retention policies"},
            "elastic_ip": {"max_savings": 1.0, "reason": "Unused IPs cleanup"},
        }

        total_cost = sum(costs_by_service.values())

        for service, cost in costs_by_service.items():
            if service in savings_matrix:
                savings_config = savings_matrix[service]
                max_savings = savings_config["max_savings"]
                potential_savings = cost * max_savings

                opportunities.append(
                    {
                        "service": service,
                        "current_cost": round(cost, 2),
                        "max_potential_savings": round(potential_savings, 2),
                        "savings_percentage": round(max_savings * 100, 2),
                        "reason": savings_config["reason"],
                        "impact": "HIGH" if potential_savings > (total_cost * 0.1) else "MEDIUM" if potential_savings > (total_cost * 0.02) else "LOW",
                    }
                )

        return sorted(opportunities, key=lambda x: x["max_potential_savings"], reverse=True)

    def calculate_breakeven(self, upfront_cost: float, monthly_savings: float) -> Dict[str, Any]:
        """
        Calculate break-even point for a cost optimization investment.

        Args:
            upfront_cost: One-time cost of optimization (e.g., reserved instance)
            monthly_savings: Monthly savings from optimization

        Returns:
            Dict with break-even analysis
        """
        if monthly_savings <= 0:
            return {"breakeven_available": False}

        breakeven_months = upfront_cost / monthly_savings
        annual_benefit = (monthly_savings * 12) - upfront_cost

        return {
            "breakeven_available": True,
            "upfront_cost": round(upfront_cost, 2),
            "monthly_savings": round(monthly_savings, 2),
            "breakeven_months": round(breakeven_months, 1),
            "annual_benefit": round(annual_benefit, 2),
            "roi_percent": round((annual_benefit / upfront_cost * 100) if upfront_cost > 0 else 0, 2),
            "payback_feasible": breakeven_months < 36,  # 3 years
        }

    def detect_cost_spike(self, costs: List[float], threshold: float = 1.5) -> List[Dict[str, Any]]:
        """
        Detect cost spikes using statistical analysis.

        Args:
            costs: Daily costs
            threshold: Standard deviation multiplier

        Returns:
            List of detected spikes
        """
        if len(costs) < 3:
            return []

        mean = sum(costs) / len(costs)
        variance = sum((x - mean) ** 2 for x in costs) / len(costs)
        std_dev = variance ** 0.5

        spikes = []
        for i, cost in enumerate(costs):
            z_score = (cost - mean) / std_dev if std_dev > 0 else 0

            if z_score > threshold:
                pct_increase = ((cost - mean) / mean * 100) if mean > 0 else 0
                spikes.append(
                    {
                        "day": i,
                        "cost": round(cost, 2),
                        "z_score": round(z_score, 2),
                        "increase_percent": round(pct_increase, 2),
                        "severity": "HIGH" if z_score > 2.5 else "MEDIUM",
                    }
                )

        return sorted(spikes, key=lambda x: x["z_score"], reverse=True)

    def _calculate_trend(self, costs: List[float]) -> float:
        """Calculate linear trend in costs."""
        n = len(costs)
        x = list(range(n))
        y = costs

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def get_forecast_summary(self, historical_costs: List[Tuple[float, str]], days: int = 30) -> Dict[str, Any]:
        """Get comprehensive forecast summary."""
        daily_forecast = self.forecast_daily_cost(historical_costs, days=days)

        if not daily_forecast.get("forecast_available"):
            return {"forecast_available": False}

        monthly_forecast = self.forecast_monthly_cost(daily_forecast)

        return {
            "forecast_available": True,
            "daily": daily_forecast,
            "monthly": monthly_forecast,
            "summary": {
                "days_forecasted": days,
                "average_daily_forecast": monthly_forecast.get("daily_average", 0),
                "projected_monthly": monthly_forecast.get("total_forecast", 0),
            },
        }
