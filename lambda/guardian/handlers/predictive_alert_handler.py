"""Predictive alerting system for cost threshold breaches."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PredictiveAlertHandler:
    """Generates proactive alerts based on cost forecasts."""

    def __init__(self):
        """Initialize predictive alert handler."""
        self.scheduled_alerts = []

    def predict_threshold_breach(
        self, account_id: str, threshold: float, forecast_values: List[float]
    ) -> Dict[str, Any]:
        """
        Predict if cost threshold will be breached.

        Args:
            account_id: AWS account ID
            threshold: Cost threshold to monitor
            forecast_values: Forecasted cost values

        Returns:
            Dict with breach prediction, timing, and confidence
        """
        try:
            will_breach = any(value > threshold for value in forecast_values)
            days_until_breach = None
            predicted_breach_cost = None

            if will_breach:
                for day, value in enumerate(forecast_values):
                    if value > threshold:
                        days_until_breach = day
                        predicted_breach_cost = value
                        break

            return {
                "success": True,
                "account_id": account_id,
                "alert_triggered": will_breach,
                "will_breach": will_breach,
                "threshold": round(threshold, 2),
                "days_until_breach": days_until_breach,
                "predicted_breach_cost": round(predicted_breach_cost, 2)
                if predicted_breach_cost
                else None,
                "confidence": 0.95,
            }

        except Exception as e:
            logger.error(f"Error predicting threshold breach: {e}")
            return {"success": False, "error": str(e)}

    def detect_cost_trend_change(
        self, historical_costs: List[float], forecast_values: List[float]
    ) -> Dict[str, Any]:
        """
        Detect unusual trend changes in cost forecasts.

        Args:
            historical_costs: Historical cost values
            forecast_values: Forecasted cost values

        Returns:
            Dict with trend change detection and severity
        """
        try:
            if len(historical_costs) < 5:
                return {"success": False, "error": "Need at least 5 historical values"}

            # Calculate historical trend
            historical_trend = (
                historical_costs[-1] - historical_costs[0]
            ) / len(historical_costs)

            # Calculate forecast trend
            if len(forecast_values) > 1:
                forecast_trend = (forecast_values[-1] - forecast_values[0]) / len(
                    forecast_values
                )
            else:
                forecast_trend = 0

            # Calculate trend acceleration
            trend_acceleration = forecast_trend / historical_trend if historical_trend != 0 else 0
            trend_changed = abs(trend_acceleration) > 1.5

            # Determine severity
            if abs(trend_acceleration) > 2:
                severity = "critical"
            elif abs(trend_acceleration) > 1.5:
                severity = "warning"
            else:
                severity = "none"

            return {
                "success": True,
                "trend_changed": trend_changed,
                "historical_trend": round(historical_trend, 2),
                "forecast_trend": round(forecast_trend, 2),
                "trend_acceleration": round(trend_acceleration, 2),
                "severity": severity,
            }

        except Exception as e:
            logger.error(f"Error detecting trend change: {e}")
            return {"success": False, "error": str(e)}

    def forecast_monthly_budget_impact(
        self, daily_forecasts: List[float], monthly_budget: float
    ) -> Dict[str, Any]:
        """
        Project end-of-month cost against budget.

        Args:
            daily_forecasts: Daily cost forecasts
            monthly_budget: Monthly budget limit

        Returns:
            Dict with projected cost, variance, and budget status
        """
        try:
            projected_month_cost = sum(daily_forecasts)
            variance_from_budget = projected_month_cost - monthly_budget
            variance_percent = (variance_from_budget / monthly_budget * 100) if monthly_budget > 0 else 0

            on_budget = projected_month_cost <= monthly_budget
            overage_level = "none"
            if variance_percent > 20:
                overage_level = "critical"
            elif variance_percent > 10:
                overage_level = "warning"
            elif variance_percent > 0:
                overage_level = "caution"

            return {
                "success": True,
                "projected_month_cost": round(projected_month_cost, 2),
                "monthly_budget": round(monthly_budget, 2),
                "variance_from_budget": round(variance_from_budget, 2),
                "variance_percent": round(variance_percent, 1),
                "on_budget": on_budget,
                "overage_level": overage_level,
                "forecast_days": len(daily_forecasts),
            }

        except Exception as e:
            logger.error(f"Error forecasting budget impact: {e}")
            return {"success": False, "error": str(e)}

    def schedule_predictive_alerts(
        self, alert_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Schedule escalating alerts for predicted threshold breaches.

        Args:
            alert_config: Alert configuration with threshold and forecast

        Returns:
            Dict with scheduled alerts and alert IDs
        """
        try:
            account_id = alert_config.get("account_id")
            threshold = alert_config.get("threshold", 5000)
            forecast_breach_day = alert_config.get("forecast_breach_day", 7)
            escalation = alert_config.get("alert_escalation", ["email", "sms"])

            # Schedule alerts at 7 days, 3 days, 1 day, and same day
            alert_timings = [
                {"days_before": 7, "alert_level": "info"},
                {"days_before": 3, "alert_level": "warning"},
                {"days_before": 1, "alert_level": "critical"},
                {"days_before": 0, "alert_level": "critical"},
            ]

            scheduled_alerts = []
            alert_ids = []

            for timing in alert_timings:
                if timing["days_before"] <= forecast_breach_day:
                    alert = {
                        "account_id": account_id,
                        "scheduled_day": forecast_breach_day - timing["days_before"],
                        "alert_level": timing["alert_level"],
                        "escalation_channels": escalation,
                        "threshold": threshold,
                    }
                    import uuid
                    alert_id = str(uuid.uuid4())
                    alert["alert_id"] = alert_id
                    scheduled_alerts.append(alert)
                    alert_ids.append(alert_id)

            self.scheduled_alerts.extend(scheduled_alerts)

            return {
                "success": True,
                "account_id": account_id,
                "scheduled_alerts": scheduled_alerts,
                "alert_ids": alert_ids,
                "total_alerts": len(scheduled_alerts),
            }

        except Exception as e:
            logger.error(f"Error scheduling predictive alerts: {e}")
            return {"success": False, "error": str(e)}
