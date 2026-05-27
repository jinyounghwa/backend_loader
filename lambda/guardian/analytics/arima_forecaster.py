"""Seasonal ARIMA Forecasting for cost prediction."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class ARIMAForecaster:
    """Forecasts costs using seasonal ARIMA models."""

    def __init__(self):
        """Initialize ARIMA forecaster."""
        self.models = {}
        self.last_retrain = None

    def train_model(self, account_id: str, historical_costs: List[Tuple[float, str]]) -> str:
        """
        Train ARIMA model on historical cost data.

        Args:
            account_id: AWS account ID
            historical_costs: List of (cost, timestamp) tuples

        Returns:
            Model ID for future predictions
        """
        if len(historical_costs) < 12:
            logger.warning(f"Insufficient data for ARIMA training ({len(historical_costs)} < 12)")
            return None

        try:
            from pmdarima import auto_arima

            values = [float(c) for c, _ in historical_costs]

            # Auto ARIMA with seasonal parameters
            # m=12 for monthly seasonality, max_p=5, max_q=5
            model = auto_arima(
                values,
                seasonal=True,
                m=12,
                max_p=5,
                max_q=5,
                max_P=2,
                max_Q=2,
                max_d=2,
                max_D=1,
                trace=False,
                error_action="ignore",
                suppress_warnings=True,
                stepwise=True,
            )

            model_id = str(uuid.uuid4())
            self.models[model_id] = {
                "model": model,
                "account_id": account_id,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "data_points": len(values),
                "values": values,
            }

            logger.info(f"Trained ARIMA model {model_id} for {account_id} with {len(values)} data points")
            return model_id

        except ImportError:
            logger.error("pmdarima not installed. Install with: pip install pmdarima")
            return None
        except Exception as e:
            logger.error(f"Error training ARIMA model: {e}")
            return None

    def forecast(
        self, model_id: str, periods: int = 30, confidence: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Generate ARIMA forecast.

        Args:
            model_id: Trained model ID
            periods: Number of periods to forecast
            confidence: Confidence level (0-1)

        Returns:
            List of forecasts with bounds and confidence
        """
        if model_id not in self.models:
            return []

        try:
            model_data = self.models[model_id]
            model = model_data["model"]

            # Generate forecast with confidence interval (pmdarima uses predict)
            forecast_values, conf_int = model.predict(
                n_periods=periods,
                return_conf_int=True,
                alpha=1 - confidence
            )

            forecasts = []
            for i in range(periods):
                forecasts.append(
                    {
                        "period": i + 1,
                        "forecast": round(float(forecast_values[i]), 2),
                        "lower_bound": round(float(conf_int[i, 0]), 2),
                        "upper_bound": round(float(conf_int[i, 1]), 2),
                        "confidence": round(confidence, 2),
                    }
                )

            return forecasts

        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return []

    def get_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """
        Get model accuracy metrics (RMSE, MAPE, AIC, BIC).

        Args:
            model_id: Trained model ID

        Returns:
            Dict with model metrics
        """
        if model_id not in self.models:
            return {}

        try:
            model_data = self.models[model_id]
            model = model_data["model"]
            values = model_data["values"]

            # In-sample fit statistics
            fit_results = model.fittedvalues()  # Call method, not get_fitted_values
            residuals = [values[i] - fit_results[i] for i in range(len(fit_results))]

            rmse = (sum(r**2 for r in residuals) / len(residuals)) ** 0.5
            mape = (
                sum(abs((values[i] - fit_results[i]) / values[i]) for i in range(len(fit_results)))
                / len(fit_results)
                * 100
            )

            return {
                "rmse": round(rmse, 2),
                "mape": round(mape, 2),
                "aic": round(model.aic(), 2),
                "bic": round(model.bic(), 2),
                "order": model.order,
                "seasonal_order": model.seasonal_order,
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}

    def compare_with_linear(
        self, model_id: str, historical_costs: List[Tuple[float, str]]
    ) -> Dict[str, Any]:
        """
        Compare ARIMA with linear regression baseline.

        Args:
            model_id: Trained ARIMA model ID
            historical_costs: Original cost data

        Returns:
            Dict with comparison metrics
        """
        if model_id not in self.models:
            return {}

        try:
            values = [float(c) for c, _ in historical_costs]
            n = len(values)

            # Linear regression baseline
            x = list(range(n))
            mean_x = sum(x) / n
            mean_y = sum(values) / n

            slope = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n)) / sum(
                (x[i] - mean_x) ** 2 for i in range(n)
            )
            intercept = mean_y - slope * mean_x

            # Linear fit values
            linear_fit = [intercept + slope * xi for xi in x]
            linear_residuals = [values[i] - linear_fit[i] for i in range(n)]

            linear_rmse = (sum(r**2 for r in linear_residuals) / len(linear_residuals)) ** 0.5
            linear_mape = (
                sum(abs((values[i] - linear_fit[i]) / values[i]) for i in range(n)) / n * 100
            )

            # ARIMA metrics
            arima_metrics = self.get_model_metrics(model_id)
            arima_rmse = arima_metrics.get("rmse", 0)
            arima_mape = arima_metrics.get("mape", 0)

            # Calculate improvement
            improvement_rmse = ((linear_rmse - arima_rmse) / linear_rmse * 100) if linear_rmse > 0 else 0
            improvement_mape = ((linear_mape - arima_mape) / linear_mape * 100) if linear_mape > 0 else 0
            improvement_avg = (improvement_rmse + improvement_mape) / 2

            return {
                "arima_rmse": round(arima_rmse, 2),
                "linear_rmse": round(linear_rmse, 2),
                "arima_mape": round(arima_mape, 2),
                "linear_mape": round(linear_mape, 2),
                "improvement_percent": round(improvement_avg, 2),
                "improvement_rmse_percent": round(improvement_rmse, 2),
                "improvement_mape_percent": round(improvement_mape, 2),
            }

        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            return {}

    def get_parameters(self, model_id: str) -> Dict[str, Any]:
        """
        Get ARIMA model parameters (p, d, q, P, D, Q, m).

        Args:
            model_id: Trained model ID

        Returns:
            Dict with model parameters
        """
        if model_id not in self.models:
            return {}

        try:
            model_data = self.models[model_id]
            model = model_data["model"]

            return {
                "order": model.order,  # (p, d, q)
                "seasonal_order": model.seasonal_order,  # (P, D, Q, m)
                "description": str(model.summary().tables[0]),
            }

        except Exception as e:
            logger.error(f"Error getting parameters: {e}")
            return {}

    def get_forecast_summary(self, model_id: str) -> Dict[str, Any]:
        """Get comprehensive forecast summary."""
        if model_id not in self.models:
            return {}

        try:
            forecasts = self.forecast(model_id, periods=12)
            metrics = self.get_model_metrics(model_id)

            if not forecasts:
                return {}

            forecast_values = [f["forecast"] for f in forecasts]

            return {
                "forecast_available": True,
                "model_type": "ARIMA",
                "forecasts": forecasts,
                "metrics": metrics,
                "summary": {
                    "forecast_average": round(sum(forecast_values) / len(forecast_values), 2),
                    "forecast_min": min(forecast_values),
                    "forecast_max": max(forecast_values),
                    "forecast_total_12m": round(sum(forecast_values), 2),
                },
            }

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {"forecast_available": False}
