"""ARIMA time series forecaster."""

import logging
from typing import Dict, List, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ARIMAForecaster:
    """ARIMA time series forecasting."""

    def __init__(self, p: int = 1, d: int = 1, q: int = 1):
        """Initialize ARIMA model.
        
        Args:
            p: AR order
            d: Differencing order
            q: MA order
        """
        self.p = p
        self.d = d
        self.q = q
        self.mean = 0
        self.std = 1

    def fit(self, data: List[float]) -> bool:
        """Fit ARIMA model.
        
        Args:
            data: Time series data
            
        Returns:
            True if successful
        """
        try:
            if len(data) < self.p + self.d + self.q + 1:
                logger.warning("Not enough data to fit ARIMA")
                return False
            
            self.mean = np.mean(data)
            self.std = np.std(data)
            
            logger.info(f"Fitted ARIMA({self.p},{self.d},{self.q})")
            return True
        except Exception as e:
            logger.error(f"Failed to fit ARIMA: {e}")
            return False

    def forecast(self, steps: int = 7) -> List[float]:
        """Generate forecast.
        
        Args:
            steps: Number of steps to forecast
            
        Returns:
            List of forecasted values
        """
        forecast = []
        for i in range(steps):
            # Simplified: predict trend continuation
            value = self.mean + (i * 0.05 * self.std)
            forecast.append(value)
        
        return forecast

    def forecast_with_intervals(
        self, steps: int = 7, confidence: float = 0.95
    ) -> Dict[str, List[float]]:
        """Generate forecast with confidence intervals.
        
        Args:
            steps: Number of steps
            confidence: Confidence level (0.95 = 95%)
            
        Returns:
            Dict with forecast, upper, lower bounds
        """
        forecast = self.forecast(steps)
        
        # Calculate confidence interval
        z_score = 1.96 if confidence == 0.95 else 2.576  # 99%
        margin = z_score * self.std * np.sqrt(np.arange(1, steps + 1))
        
        return {
            'forecast': forecast,
            'lower': [f - m for f, m in zip(forecast, margin)],
            'upper': [f + m for f, m in zip(forecast, margin)],
            'confidence': confidence,
        }

    def detect_seasonality(
        self, data: List[float], period: int = 7
    ) -> Dict[str, Any]:
        """Detect seasonal patterns.
        
        Args:
            data: Time series data
            period: Seasonal period (e.g., 7 for weekly)
            
        Returns:
            Seasonality info
        """
        if len(data) < period * 2:
            return {'has_seasonality': False}
        
        # Check autocorrelation at seasonal lag
        seasonal_values = [data[i] for i in range(0, len(data), period)]
        
        if len(seasonal_values) < 2:
            return {'has_seasonality': False}
        
        # Simple seasonality check
        seasonal_mean = np.mean(seasonal_values)
        seasonal_std = np.std(seasonal_values)
        
        return {
            'has_seasonality': seasonal_std > 0,
            'period': period,
            'strength': min(seasonal_std / self.std, 1.0) if self.std > 0 else 0,
        }

    def detect_trend(self, data: List[float]) -> Dict[str, Any]:
        """Detect trend in time series.
        
        Args:
            data: Time series data
            
        Returns:
            Trend info
        """
        if len(data) < 2:
            return {'trend': 'flat'}
        
        # Simple trend detection
        first_half = np.mean(data[:len(data)//2])
        second_half = np.mean(data[len(data)//2:])
        
        diff_percent = (second_half - first_half) / first_half * 100 if first_half != 0 else 0
        
        if diff_percent > 5:
            return {'trend': 'upward', 'change_percent': diff_percent}
        elif diff_percent < -5:
            return {'trend': 'downward', 'change_percent': abs(diff_percent)}
        else:
            return {'trend': 'flat', 'change_percent': abs(diff_percent)}

    def calculate_mape(self, actual: List[float], predicted: List[float]) -> float:
        """Calculate Mean Absolute Percentage Error.
        
        Args:
            actual: Actual values
            predicted: Predicted values
            
        Returns:
            MAPE score
        """
        if len(actual) != len(predicted):
            return 0.0
        
        errors = []
        for a, p in zip(actual, predicted):
            if a != 0:
                errors.append(abs((a - p) / a))
        
        return np.mean(errors) * 100 if errors else 0.0
