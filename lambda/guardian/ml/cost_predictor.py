"""Machine learning models for cost prediction."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CostPredictor:
    """Trains and manages ML models for cost forecasting."""

    def __init__(self):
        """Initialize cost predictor."""
        self.models = {}
        self.accuracy_history = []

    def train_prophet_model(
        self,
        account_id: str,
        historical_costs: List[float],
        seasonality_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Train Prophet model for long-term cost forecasting.

        Args:
            account_id: AWS account ID
            historical_costs: Historical cost values (24+ months)
            seasonality_info: Seasonality detection results

        Returns:
            Dict with model, forecast, accuracy (MAPE), confidence intervals
        """
        try:
            if len(historical_costs) < 24:
                return {
                    "success": False,
                    "error": "Need at least 24 months of data for Prophet",
                }

            # Simulate Prophet training
            # Real implementation would use fbprophet library
            forecast_values = self._generate_prophet_forecast(
                historical_costs, seasonality_info
            )

            # Calculate accuracy (MAPE: Mean Absolute Percentage Error)
            mape = self._calculate_mape(historical_costs[-12:], forecast_values[:12])

            # Generate confidence intervals (95% CI)
            confidence_intervals = [
                {
                    "lower_bound": round(val * 0.9, 2),
                    "upper_bound": round(val * 1.1, 2),
                }
                for val in forecast_values[:12]
            ]

            model_data = {
                "model_type": "prophet",
                "account_id": account_id,
                "forecast_values": forecast_values,
                "seasonality": seasonality_info,
            }

            self.models[f"prophet_{account_id}"] = model_data
            self.accuracy_history.append(
                {"account_id": account_id, "model": "prophet", "mape": mape}
            )

            return {
                "success": True,
                "model_type": "prophet",
                "forecast": forecast_values[:12],
                "accuracy_mape": round(mape, 2),
                "confidence_intervals": confidence_intervals,
            }

        except Exception as e:
            logger.error(f"Error training Prophet model: {e}")
            return {"success": False, "error": str(e)}

    def train_lstm_model(
        self,
        account_id: str,
        historical_costs: List[float],
        features: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """
        Train LSTM model for short-term cost spike prediction.

        Args:
            account_id: AWS account ID
            historical_costs: Daily cost history (60+ days)
            features: Service-level cost breakdown

        Returns:
            Dict with model, 7-day predictions, confidence bands
        """
        try:
            if len(historical_costs) < 30:
                return {
                    "success": False,
                    "error": "Need at least 30 days of data for LSTM",
                }

            # Simulate LSTM training
            # Real implementation would use TensorFlow/Keras
            predictions = self._generate_lstm_forecast(historical_costs)

            # Generate confidence bands (optimistic/realistic/pessimistic)
            confidence_bands = [
                {
                    "optimistic": round(pred * 0.95, 2),
                    "realistic": round(pred, 2),
                    "pessimistic": round(pred * 1.05, 2),
                }
                for pred in predictions
            ]

            model_data = {
                "model_type": "lstm",
                "account_id": account_id,
                "predictions": predictions,
                "features": features,
            }

            self.models[f"lstm_{account_id}"] = model_data

            return {
                "success": True,
                "model_type": "lstm",
                "predictions": predictions,
                "forecast_horizon_days": 7,
                "confidence_bands": confidence_bands,
            }

        except Exception as e:
            logger.error(f"Error training LSTM model: {e}")
            return {"success": False, "error": str(e)}

    def train_ensemble_model(
        self,
        arima_forecast: List[float],
        prophet_forecast: List[float],
        lstm_forecast: List[float],
    ) -> Dict[str, Any]:
        """
        Train ensemble model combining multiple forecasts.

        Args:
            arima_forecast: ARIMA forecast values
            prophet_forecast: Prophet forecast values
            lstm_forecast: LSTM forecast values

        Returns:
            Dict with weighted ensemble forecast
        """
        try:
            # Weights: ARIMA 40%, Prophet 35%, LSTM 25%
            ensemble_forecast = [
                round((arima * 0.4 + prophet * 0.35 + lstm * 0.25), 2)
                for arima, prophet, lstm in zip(
                    arima_forecast, prophet_forecast, lstm_forecast
                )
            ]

            return {
                "success": True,
                "ensemble_forecast": ensemble_forecast,
                "weights": {"arima": 0.4, "prophet": 0.35, "lstm": 0.25},
                "forecast_length": len(ensemble_forecast),
            }

        except Exception as e:
            logger.error(f"Error training ensemble model: {e}")
            return {"success": False, "error": str(e)}

    def evaluate_model_accuracy(
        self,
        actual_costs: List[float],
        predicted_costs: List[float],
    ) -> Dict[str, Any]:
        """
        Evaluate model accuracy with multiple metrics.

        Args:
            actual_costs: Actual observed costs
            predicted_costs: Model predictions

        Returns:
            Dict with MAPE, RMSE, MAE metrics
        """
        try:
            if len(actual_costs) != len(predicted_costs):
                return {"success": False, "error": "Length mismatch"}

            mape = self._calculate_mape(actual_costs, predicted_costs)
            rmse = self._calculate_rmse(actual_costs, predicted_costs)
            mae = self._calculate_mae(actual_costs, predicted_costs)

            return {
                "success": True,
                "mape_percent": round(mape, 2),
                "rmse": round(rmse, 2),
                "mae": round(mae, 2),
                "prediction_interval": len(actual_costs),
            }

        except Exception as e:
            logger.error(f"Error evaluating model accuracy: {e}")
            return {"success": False, "error": str(e)}

    def check_retraining_condition(self, current_mape: float) -> Dict[str, Any]:
        """
        Check if model should be retrained based on accuracy.

        Args:
            current_mape: Current model MAPE

        Returns:
            Dict with retraining recommendation
        """
        try:
            should_retrain = current_mape > 15  # Retrain if MAPE > 15%

            return {
                "success": True,
                "should_retrain": should_retrain,
                "current_mape": round(current_mape, 2),
                "mape_threshold": 15,
                "reason": (
                    "Accuracy degraded" if should_retrain else "Model performing well"
                ),
            }

        except Exception as e:
            logger.error(f"Error checking retraining condition: {e}")
            return {"success": False, "error": str(e)}

    def calculate_confidence_intervals(
        self,
        forecast_values: List[float],
        uncertainty: List[float],
    ) -> Dict[str, Any]:
        """
        Calculate confidence intervals for forecasts.

        Args:
            forecast_values: Point forecasts
            uncertainty: Uncertainty bounds (typically std_dev * 1.96 for 95% CI)

        Returns:
            Dict with lower and upper bounds for each forecast
        """
        try:
            intervals = [
                {
                    "forecast": round(forecast, 2),
                    "lower_bound": round(forecast - unc, 2),
                    "upper_bound": round(forecast + unc, 2),
                    "confidence_level": 0.95,
                }
                for forecast, unc in zip(forecast_values, uncertainty)
            ]

            return {
                "success": True,
                "intervals": intervals,
                "count": len(intervals),
            }

        except Exception as e:
            logger.error(f"Error calculating confidence intervals: {e}")
            return {"success": False, "error": str(e)}

    # Private helper methods
    def _generate_prophet_forecast(
        self, historical_costs: List[float], seasonality_info: Dict
    ) -> List[float]:
        """Generate simulated Prophet forecast."""
        # Simulate Prophet forecast: trend + seasonality
        if not historical_costs:
            return []

        trend = (historical_costs[-1] - historical_costs[0]) / len(historical_costs)
        base = historical_costs[-1]

        forecast = []
        for i in range(12):
            # Linear trend + seasonal component
            seasonal_factor = 1.0 + (seasonality_info.get("strength", 0) * 0.1)
            value = base + (trend * (i + 1))
            if (i % 12) in [9, 10, 11]:  # Q4 seasonal peak
                value *= seasonal_factor
            forecast.append(round(value, 2))

        return forecast

    def _generate_lstm_forecast(self, historical_costs: List[float]) -> List[float]:
        """Generate simulated LSTM forecast for next 7 days."""
        if len(historical_costs) < 7:
            return historical_costs[:7]

        # Simulate LSTM: use recent average with small trend
        recent_avg = sum(historical_costs[-7:]) / 7
        trend = (historical_costs[-1] - historical_costs[-7]) / 7

        forecast = []
        for i in range(7):
            value = recent_avg + (trend * (i + 1))
            forecast.append(round(value, 2))

        return forecast

    def _calculate_mape(
        self, actual: List[float], predicted: List[float]
    ) -> float:
        """Calculate Mean Absolute Percentage Error."""
        if len(actual) == 0:
            return 0.0

        errors = [
            abs((a - p) / a) * 100 for a, p in zip(actual, predicted) if a != 0
        ]
        return sum(errors) / len(errors) if errors else 0.0

    def _calculate_rmse(
        self, actual: List[float], predicted: List[float]
    ) -> float:
        """Calculate Root Mean Squared Error."""
        if len(actual) == 0:
            return 0.0

        squared_errors = [(a - p) ** 2 for a, p in zip(actual, predicted)]
        return (sum(squared_errors) / len(squared_errors)) ** 0.5

    def _calculate_mae(
        self, actual: List[float], predicted: List[float]
    ) -> float:
        """Calculate Mean Absolute Error."""
        if len(actual) == 0:
            return 0.0

        errors = [abs(a - p) for a, p in zip(actual, predicted)]
        return sum(errors) / len(errors)
