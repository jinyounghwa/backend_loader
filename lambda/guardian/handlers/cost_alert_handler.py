"""Cost-specific alert handler for real-time dashboard."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CostAlertHandler:
    """Generates and manages cost-related alerts."""

    def __init__(self):
        """Initialize cost alert handler."""
        self.alerts_buffer = []
        self.alert_history = []

    def check_cost_threshold(
        self, account_id: str, current_cost: float, threshold: float
    ) -> Dict[str, Any]:
        """
        Check if current cost exceeds user-defined threshold.

        Args:
            account_id: AWS account ID
            current_cost: Current cost amount
            threshold: User-defined cost threshold

        Returns:
            Dict with alert_triggered, current_cost, threshold, severity
        """
        try:
            alert_triggered = current_cost > threshold
            severity = "warning" if alert_triggered else "none"

            result = {
                "alert_triggered": alert_triggered,
                "current_cost": round(current_cost, 2),
                "threshold": round(threshold, 2),
                "excess_amount": round(max(0, current_cost - threshold), 2),
                "severity": severity,
                "account_id": account_id,
            }

            if alert_triggered:
                self.alerts_buffer.append(
                    {
                        "type": "cost_threshold",
                        "account_id": account_id,
                        "message": f"Daily cost exceeded ${threshold:.2f} threshold (actual: ${current_cost:.2f})",
                        **result,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error checking cost threshold: {e}")
            return {"alert_triggered": False, "error": str(e)}

    def detect_cost_anomaly(
        self,
        actual_cost: float,
        forecast_cost: float,
        confidence_lower: float,
        confidence_upper: float,
    ) -> Dict[str, Any]:
        """
        Detect unusual costs outside forecast confidence intervals.

        Args:
            actual_cost: Actual observed cost
            forecast_cost: Forecasted cost from Phase 1 ARIMA
            confidence_lower: Lower bound of 95% CI
            confidence_upper: Upper bound of 95% CI

        Returns:
            Dict with is_anomaly, severity, variance details
        """
        try:
            is_anomaly = actual_cost < confidence_lower or actual_cost > confidence_upper
            variance = actual_cost - forecast_cost
            variance_percent = (variance / forecast_cost * 100) if forecast_cost > 0 else 0

            severity = "none"
            if is_anomaly:
                if abs(variance_percent) > 30:
                    severity = "critical"
                elif abs(variance_percent) > 15:
                    severity = "warning"
                else:
                    severity = "info"

            result = {
                "is_anomaly": is_anomaly,
                "actual_cost": round(actual_cost, 2),
                "forecast_cost": round(forecast_cost, 2),
                "variance_amount": round(variance, 2),
                "variance_percent": round(variance_percent, 1),
                "confidence_lower": round(confidence_lower, 2),
                "confidence_upper": round(confidence_upper, 2),
                "severity": severity,
            }

            if is_anomaly:
                self.alerts_buffer.append(
                    {
                        "type": "cost_anomaly",
                        "message": f"Cost anomaly detected: ${actual_cost:.2f} vs forecast ${forecast_cost:.2f} ({variance_percent:+.1f}%)",
                        **result,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error detecting cost anomaly: {e}")
            return {"is_anomaly": False, "error": str(e)}

    def generate_recommendation_alert(
        self, account_id: str, recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate alert when high-confidence recommendations are available.

        Args:
            account_id: AWS account ID
            recommendations: List of recommendations with confidence scores

        Returns:
            Dict with alert details, top recommendations, total potential savings
        """
        try:
            if not recommendations:
                return {
                    "alert_triggered": False,
                    "message": "No recommendations available",
                    "recommendations_count": 0,
                    "total_monthly_savings": 0.0,
                }

            # Filter high-confidence recommendations (confidence >= 0.8)
            high_confidence = [r for r in recommendations if r.get("confidence", 0) >= 0.8]

            if not high_confidence:
                return {
                    "alert_triggered": False,
                    "message": "No high-confidence recommendations",
                    "recommendations_count": 0,
                    "total_monthly_savings": 0.0,
                }

            # Calculate total potential savings
            total_monthly_savings = sum(r.get("monthly_savings", 0) for r in high_confidence)
            total_annual_savings = total_monthly_savings * 12

            result = {
                "alert_triggered": True,
                "account_id": account_id,
                "message": f"New cost optimization recommendations available: {len(high_confidence)} recommendations with ${total_annual_savings:,.0f}/year potential savings",
                "recommendations_count": len(high_confidence),
                "top_recommendations": high_confidence[:3],
                "total_monthly_savings": round(total_monthly_savings, 2),
                "total_annual_savings": round(total_annual_savings, 2),
                "severity": "info",
            }

            if result["alert_triggered"]:
                self.alerts_buffer.append(
                    {
                        "type": "recommendation_ready",
                        **result,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error generating recommendation alert: {e}")
            return {"alert_triggered": False, "error": str(e)}

    def flush_alerts(self) -> List[Dict[str, Any]]:
        """
        Flush buffered alerts and return for broadcasting.

        Returns:
            List of alerts ready to broadcast
        """
        try:
            alerts = self.alerts_buffer.copy()
            self.alert_history.extend(alerts)
            self.alerts_buffer = []
            return alerts

        except Exception as e:
            logger.error(f"Error flushing alerts: {e}")
            return []

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent alert history.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts (newest first)
        """
        try:
            return self.alert_history[-limit:][::-1]  # Reverse for newest first

        except Exception as e:
            logger.error(f"Error retrieving alert history: {e}")
            return []
