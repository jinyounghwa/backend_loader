"""Cost forecasting with ML (Phase 2 of Sprint 76).

Ensemble forecasting combining ARIMA, Prophet, and time series analysis
with automatic seasonality detection and budget optimization.
"""
import math
import statistics
from datetime import datetime, timezone
from typing import Any


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CostForecaster:
    """Ensemble cost forecaster combining ARIMA + Prophet + Moving Average."""

    def __init__(self):
        """Initialize forecaster."""
        self.arima_params = {'p': 1, 'd': 1, 'q': 1}
        self.models = {}

    def ensemble_forecast(self, params: dict) -> dict:
        """Forecast costs using ensemble of models.
        
        Args:
            params: {
                'historical_costs': list of historical costs,
                'periods': number of periods to forecast,
                'confidence': confidence level (default 0.95),
                'seasonality_period': period for seasonality (optional),
                'method': 'ensemble' (default)
            }
        
        Returns:
            {
                'forecast': list of forecasted values,
                'lower_bound': lower confidence interval,
                'upper_bound': upper confidence interval,
                'mae': mean absolute error,
                'rmse': root mean squared error,
                'mape': mean absolute percentage error,
                'model_weights': {'arima': 0.5, 'prophet': 0.3, 'ma': 0.2}
            }
        """
        historical = params['historical_costs']
        periods = params.get('periods', 30)
        confidence = params.get('confidence', 0.95)
        
        # Generate forecasts from each model
        arima_forecast = self._arima_forecast(historical, periods)
        prophet_forecast = self._prophet_forecast(historical, periods)
        ma_forecast = self._moving_average_forecast(historical, periods)
        
        # Ensemble: weighted average
        weights = {'arima': 0.5, 'prophet': 0.3, 'ma': 0.2}
        forecast = [
            arima_forecast[i] * 0.5 + prophet_forecast[i] * 0.3 + ma_forecast[i] * 0.2
            for i in range(periods)
        ]
        
        # Calculate confidence intervals
        residuals = self._calculate_residuals(historical, forecast[:min(len(forecast), len(historical))])
        std_error = statistics.stdev(residuals) if len(residuals) > 1 else 1.0
        z_score = self._get_z_score(confidence)
        margin = z_score * std_error
        
        lower = [max(0, f - margin) for f in forecast]
        upper = [f + margin for f in forecast]
        
        # Performance metrics
        mae = sum(abs(r) for r in residuals) / len(residuals) if residuals else 0
        rmse = math.sqrt(sum(r**2 for r in residuals) / len(residuals)) if residuals else 0
        
        # MAPE calculation
        mape = 0.0
        valid_mape = 0
        for i, actual in enumerate(historical[-periods:] if len(historical) > periods else historical):
            if actual > 0:
                mape += abs((forecast[i] - actual) / actual) * 100
                valid_mape += 1
        mape = mape / valid_mape if valid_mape > 0 else 0
        
        return {
            'forecast': forecast,
            'lower_bound': lower,
            'upper_bound': upper,
            'mae': mae,
            'rmse': rmse,
            'mape': min(mape, 100.0),
            'model_weights': weights,
            'timestamp': now_utc().isoformat()
        }

    def _arima_forecast(self, data: list, periods: int) -> list:
        """Simple ARIMA-like forecast using differencing."""
        if len(data) < 2:
            return [data[-1]] * periods if data else [0] * periods
        
        # First difference
        diff = [data[i+1] - data[i] for i in range(len(data) - 1)]
        diff_mean = sum(diff) / len(diff) if diff else 0
        
        forecast = []
        last_val = data[-1]
        for _ in range(periods):
            last_val += diff_mean
            forecast.append(max(0, last_val))
        
        return forecast

    def _prophet_forecast(self, data: list, periods: int) -> list:
        """Simple Prophet-like forecast using trend + seasonality."""
        if len(data) < 2:
            return [data[-1]] * periods if data else [0] * periods
        
        # Extract trend
        mid = len(data) // 2
        trend_start = sum(data[:mid]) / mid
        trend_end = sum(data[mid:]) / len(data[mid:])
        trend = (trend_end - trend_start) / len(data)
        
        # Simple seasonality detection
        seasonality = [0] * periods
        if len(data) >= 7:
            for i in range(7):
                if i < len(data):
                    seasonality[i % periods] = data[i] - sum(data) / len(data)
        
        forecast = []
        last_val = data[-1] if data else 0
        for i in range(periods):
            val = last_val + trend + seasonality[i % len(seasonality)]
            forecast.append(max(0, val))
            last_val = val
        
        return forecast

    def _moving_average_forecast(self, data: list, periods: int) -> list:
        """Moving average forecast."""
        if not data:
            return [0] * periods
        
        window = min(7, len(data))
        ma = sum(data[-window:]) / window
        return [ma] * periods

    def _calculate_residuals(self, actual: list, forecast: list) -> list:
        """Calculate residuals between actual and forecast."""
        min_len = min(len(actual), len(forecast))
        return [actual[i] - forecast[i] for i in range(min_len)]

    def _get_z_score(self, confidence: float) -> float:
        """Get Z-score for confidence level."""
        scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        return scores.get(confidence, 1.96)


class SeasonalityDetector:
    """Automatic seasonality detection."""

    def __init__(self):
        """Initialize detector."""
        self.patterns = {}

    def detect_seasonality(self, params: dict) -> dict:
        """Detect seasonality in cost data.
        
        Args:
            params: {
                'costs': list of costs,
                'period': expected period (24 for daily, 7 for weekly, 30 for monthly)
            }
        
        Returns:
            {
                'has_seasonality': bool,
                'period': detected period,
                'strength': float 0-1 (strength of seasonality),
                'pattern': dict of seasonal components
            }
        """
        costs = params['costs']
        period = params.get('period', 7)
        
        if len(costs) < period * 2:
            return {
                'has_seasonality': False,
                'period': period,
                'strength': 0.0,
                'pattern': {}
            }
        
        # Extract seasonal pattern
        seasonal_means = []
        for i in range(period):
            indices = [j for j in range(i, len(costs), period)]
            if indices:
                seasonal_means.append(sum(costs[j] for j in indices) / len(indices))
            else:
                seasonal_means.append(0)
        
        # Calculate seasonality strength
        overall_mean = sum(costs) / len(costs)
        seasonal_variance = sum((m - overall_mean) ** 2 for m in seasonal_means) / period
        total_variance = sum((c - overall_mean) ** 2 for c in costs) / len(costs)
        
        strength = (seasonal_variance / total_variance) if total_variance > 0 else 0
        strength = min(strength, 1.0)
        
        has_seasonality = strength > 0.15
        
        return {
            'has_seasonality': has_seasonality,
            'period': period,
            'strength': strength,
            'pattern': {f'hour_{i}': m for i, m in enumerate(seasonal_means)},
            'timestamp': now_utc().isoformat()
        }


class BudgetOptimizer:
    """Budget-based optimization suggester."""

    def __init__(self):
        """Initialize optimizer."""
        self.recommendations_db = {}

    def optimize_budget(self, params: dict) -> dict:
        """Generate budget optimization recommendations.
        
        Args:
            params: {
                'current_costs': {
                    'daily_average': float,
                    'monthly_forecast': float,
                    'daily_peak': float,
                    'hourly_average': float
                },
                'budget_limit': float
            }
        
        Returns:
            {
                'status': 'within_limit' | 'exceeds_limit',
                'current_forecast': float,
                'budget_limit': float,
                'variance': float,
                'variance_percent': float,
                'recommendations': [list of recommendations]
            }
        """
        current = params['current_costs']
        limit = params['budget_limit']
        forecast = current['monthly_forecast']
        
        variance = forecast - limit
        variance_percent = (variance / limit * 100) if limit > 0 else 0
        
        recommendations = []
        status = 'within_limit' if forecast <= limit else 'exceeds_limit'
        
        if status == 'exceeds_limit':
            # Generate recommendations
            if current['daily_peak'] > current['daily_average'] * 2:
                recommendations.append({
                    'type': 'peak_reduction',
                    'description': 'Reduce peak hour costs through autoscaling',
                    'potential_savings': current['daily_peak'] * 0.3 * 30
                })
            
            recommendations.append({
                'type': 'instance_optimization',
                'description': 'Right-size instances based on actual utilization',
                'potential_savings': forecast * 0.2
            })
            
            recommendations.append({
                'type': 'reserved_instances',
                'description': 'Purchase reserved instances for baseline load',
                'potential_savings': forecast * 0.35
            })
        else:
            recommendations.append({
                'type': 'cost_health',
                'description': 'Budget is healthy with good margin',
                'remaining_budget': limit - forecast
            })
        
        return {
            'status': status,
            'current_forecast': forecast,
            'budget_limit': limit,
            'variance': variance,
            'variance_percent': variance_percent,
            'recommendations': recommendations,
            'timestamp': now_utc().isoformat()
        }


class CostAnomaly:
    """Real-time cost anomaly detection."""

    def __init__(self):
        """Initialize anomaly detector."""
        self.baselines = {}

    def detect_anomaly(self, params: dict) -> dict:
        """Detect anomalies in cost data.
        
        Args:
            params: {
                'baseline_costs': list of baseline costs,
                'current_cost': current cost value,
                'threshold': std dev threshold for anomaly (default 2.0)
            }
        
        Returns:
            {
                'is_anomaly': bool,
                'anomaly_score': float 0-1,
                'confidence': float 0-1,
                'deviation_percent': float,
                'explanation': str,
                'baseline_mean': float,
                'baseline_stddev': float
            }
        """
        baseline = params['baseline_costs']
        current = params['current_cost']
        threshold = params.get('threshold', 2.0)
        
        if not baseline or len(baseline) < 2:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'confidence': 0.0,
                'deviation_percent': 0.0,
                'explanation': 'Insufficient baseline data',
                'baseline_mean': 0,
                'baseline_stddev': 0
            }
        
        mean = sum(baseline) / len(baseline)
        variance = sum((x - mean) ** 2 for x in baseline) / len(baseline)
        stddev = math.sqrt(variance)
        
        # Handle zero stddev case - treat large deviations as anomalies
        if stddev == 0:
            deviation = current - mean
            deviation_percent = (abs(deviation) / mean * 100) if mean > 0 else 0
            # If stddev is 0 (perfectly flat baseline) and current differs significantly, it's an anomaly
            is_anomaly = abs(deviation) > mean * 0.5  # More than 50% deviation from baseline
            z_score = float('inf') if deviation != 0 else 0
            anomaly_score = 1.0 if is_anomaly else 0.0
        else:
            deviation = current - mean
            z_score = abs(deviation) / stddev
            is_anomaly = z_score >= threshold
            anomaly_score = min(z_score / threshold, 1.0) if threshold > 0 else 0
            deviation_percent = (abs(current - mean) / mean * 100) if mean > 0 else 0
        
        # Confidence
        n = len(baseline)
        confidence = min(1.0, n / 100)
        
        # Explanation
        if is_anomaly:
            if deviation > 0:
                explanation = f'Cost increased {deviation_percent:.1f}% above baseline'
            else:
                explanation = f'Cost decreased {abs(deviation_percent):.1f}% below baseline'
        else:
            explanation = 'Cost within normal range'
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'confidence': confidence,
            'deviation_percent': deviation_percent,
            'explanation': explanation,
            'baseline_mean': mean,
            'baseline_stddev': stddev,
            'z_score': z_score if z_score != float('inf') else 999.0,
            'timestamp': now_utc().isoformat()
        }
