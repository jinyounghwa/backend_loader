"""Tests for cost forecasting with ML (Phase 2 of Sprint 76)."""
import pytest
import math
from datetime import datetime, timedelta, timezone


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestCostForecaster:
    """Test cost forecasting with ARIMA + Prophet + Ensemble."""

    def test_ensemble_forecast_basic(self):
        """✅ Ensemble forecast generates predictions."""
        from guardian.ml.cost_forecasting import CostForecaster

        historical_costs = [100 + i * 2 + (5 if i % 7 < 2 else 0) for i in range(90)]

        forecaster = CostForecaster()
        forecast = forecaster.ensemble_forecast({
            'historical_costs': historical_costs,
            'periods': 30
        })

        assert 'forecast' in forecast
        assert 'lower_bound' in forecast
        assert 'upper_bound' in forecast
        assert len(forecast['forecast']) == 30
        assert all(v > 0 for v in forecast['forecast'])

    def test_ensemble_forecast_confidence_intervals(self):
        """✅ Confidence intervals are wider than point forecast."""
        from guardian.ml.cost_forecasting import CostForecaster

        historical_costs = [100 + i * 1.5 for i in range(90)]

        forecaster = CostForecaster()
        forecast = forecaster.ensemble_forecast({
            'historical_costs': historical_costs,
            'periods': 30,
            'confidence': 0.95
        })

        for i in range(len(forecast['forecast'])):
            assert forecast['lower_bound'][i] < forecast['forecast'][i]
            assert forecast['forecast'][i] < forecast['upper_bound'][i]

    def test_ensemble_forecast_performance_metrics(self):
        """✅ Ensemble calculates MAE, RMSE, MAPE."""
        from guardian.ml.cost_forecasting import CostForecaster

        historical_costs = [100 + i * 2 for i in range(90)]

        forecaster = CostForecaster()
        forecast = forecaster.ensemble_forecast({
            'historical_costs': historical_costs,
            'periods': 30
        })

        assert 'mae' in forecast
        assert 'rmse' in forecast
        assert 'mape' in forecast
        assert forecast['mae'] >= 0
        assert forecast['rmse'] >= 0
        assert 0 <= forecast['mape'] <= 100


class TestSeasonalityDetector:
    """Test automatic seasonality detection."""

    def test_detect_daily_seasonality(self):
        """✅ Detect daily seasonality pattern."""
        from guardian.ml.cost_forecasting import SeasonalityDetector

        costs = []
        for day in range(30):
            for hour in range(24):
                if hour < 6:
                    costs.append(10)
                elif hour < 18:
                    costs.append(50)
                else:
                    costs.append(20)

        detector = SeasonalityDetector()
        result = detector.detect_seasonality({
            'costs': costs,
            'period': 24
        })

        assert 'has_seasonality' in result
        assert 'period' in result
        assert 'strength' in result
        assert result['has_seasonality'] is True

    def test_detect_weekly_seasonality(self):
        """✅ Detect weekly seasonality pattern."""
        from guardian.ml.cost_forecasting import SeasonalityDetector

        costs = []
        for week in range(12):
            for day in range(7):
                if day < 5:
                    costs.append(100)
                else:
                    costs.append(50)

        detector = SeasonalityDetector()
        result = detector.detect_seasonality({
            'costs': costs,
            'period': 7
        })

        assert result['has_seasonality'] is True
        assert result['strength'] > 0.5


class TestBudgetOptimizer:
    """Test budget-based optimization suggestions."""

    def test_budget_optimization_recommendations(self):
        """✅ Generate optimization recommendations."""
        from guardian.ml.cost_forecasting import BudgetOptimizer

        current_costs = {
            'daily_average': 150,
            'monthly_forecast': 4500,
            'daily_peak': 250,
            'hourly_average': 6.25
        }

        optimizer = BudgetOptimizer()
        recommendations = optimizer.optimize_budget({
            'current_costs': current_costs,
            'budget_limit': 5000
        })

        assert 'status' in recommendations
        assert 'recommendations' in recommendations
        assert isinstance(recommendations['recommendations'], list)

    def test_budget_within_limit(self):
        """✅ Report when budget is within limits."""
        from guardian.ml.cost_forecasting import BudgetOptimizer

        current_costs = {
            'daily_average': 100,
            'monthly_forecast': 3000,
            'daily_peak': 150,
            'hourly_average': 4.0
        }

        optimizer = BudgetOptimizer()
        recommendations = optimizer.optimize_budget({
            'current_costs': current_costs,
            'budget_limit': 5000
        })

        assert recommendations['status'] == 'within_limit'

    def test_budget_exceeds_limit(self):
        """✅ Alert when budget is exceeded."""
        from guardian.ml.cost_forecasting import BudgetOptimizer

        current_costs = {
            'daily_average': 200,
            'monthly_forecast': 6000,
            'daily_peak': 300,
            'hourly_average': 8.0
        }

        optimizer = BudgetOptimizer()
        recommendations = optimizer.optimize_budget({
            'current_costs': current_costs,
            'budget_limit': 5000
        })

        assert recommendations['status'] == 'exceeds_limit'
        assert len(recommendations['recommendations']) > 0


class TestCostAnomaly:
    """Test real-time cost anomaly detection."""

    def test_detect_cost_spike(self):
        """✅ Detect sudden cost spike."""
        from guardian.ml.cost_forecasting import CostAnomaly

        baseline_costs = [100] * 30
        current_cost = 500

        anomaly_detector = CostAnomaly()
        result = anomaly_detector.detect_anomaly({
            'baseline_costs': baseline_costs,
            'current_cost': current_cost,
            'threshold': 2.0
        })

        assert 'is_anomaly' in result
        assert 'anomaly_score' in result
        assert result['is_anomaly'] is True
        assert result['anomaly_score'] > 0.5

    def test_normal_cost_variation(self):
        """✅ Normal variation is not flagged as anomaly."""
        from guardian.ml.cost_forecasting import CostAnomaly

        baseline_costs = [100 + i % 10 for i in range(30)]
        current_cost = 105

        anomaly_detector = CostAnomaly()
        result = anomaly_detector.detect_anomaly({
            'baseline_costs': baseline_costs,
            'current_cost': current_cost,
            'threshold': 2.0
        })

        assert result['is_anomaly'] is False

    def test_anomaly_explanation(self):
        """✅ Anomaly includes deviation explanation."""
        from guardian.ml.cost_forecasting import CostAnomaly

        baseline_costs = [100] * 30
        current_cost = 400

        anomaly_detector = CostAnomaly()
        result = anomaly_detector.detect_anomaly({
            'baseline_costs': baseline_costs,
            'current_cost': current_cost,
            'threshold': 2.0
        })

        assert 'explanation' in result
        assert 'deviation_percent' in result
        assert result['deviation_percent'] > 100

    def test_anomaly_with_confidence(self):
        """✅ Anomaly detection includes confidence score."""
        from guardian.ml.cost_forecasting import CostAnomaly

        baseline_costs = [100 + i % 20 for i in range(90)]
        current_cost = 250

        anomaly_detector = CostAnomaly()
        result = anomaly_detector.detect_anomaly({
            'baseline_costs': baseline_costs,
            'current_cost': current_cost,
            'threshold': 1.5
        })

        assert 'confidence' in result
        assert 0 <= result['confidence'] <= 1.0


class TestCostForecastingIntegration:
    """Integration tests for cost forecasting pipeline."""

    def test_full_cost_analysis_pipeline(self):
        """✅ Full pipeline: detect seasonality → forecast → optimize."""
        from guardian.ml.cost_forecasting import (
            CostForecaster,
            SeasonalityDetector,
            BudgetOptimizer
        )

        historical_costs = []
        for day in range(90):
            for hour in range(24):
                base = 100 + (day * 0.5)
                if hour < 6:
                    cost = base * 0.5
                elif hour < 18:
                    cost = base * 1.5
                else:
                    cost = base
                historical_costs.append(cost)

        # Step 1: Detect seasonality
        detector = SeasonalityDetector()
        seasonality = detector.detect_seasonality({
            'costs': historical_costs,
            'period': 24
        })

        # Step 2: Forecast
        forecaster = CostForecaster()
        forecast = forecaster.ensemble_forecast({
            'historical_costs': historical_costs,
            'periods': 30,
            'seasonality_period': seasonality.get('period', 24) if seasonality['has_seasonality'] else None
        })

        # Step 3: Optimize budget
        monthly_forecast = sum(forecast['forecast'])
        optimizer = BudgetOptimizer()
        recommendations = optimizer.optimize_budget({
            'current_costs': {
                'monthly_forecast': monthly_forecast,
                'daily_average': monthly_forecast / 30,
                'daily_peak': max(forecast['forecast']),
                'hourly_average': monthly_forecast / (30 * 24)
            },
            'budget_limit': monthly_forecast * 1.2
        })

        assert seasonality['has_seasonality']
        assert len(forecast['forecast']) == 30
        assert recommendations['status'] == 'within_limit'

    def test_cost_drift_detection_over_time(self):
        """✅ Detect cost drift across periods."""
        from guardian.ml.cost_forecasting import CostAnomaly

        period_1 = [100 + i % 10 for i in range(30)]
        period_2 = [110 + i % 10 for i in range(30)]
        period_3 = [150 + i % 10 for i in range(30)]

        anomaly_detector = CostAnomaly()
        anomaly_3 = anomaly_detector.detect_anomaly({
            'baseline_costs': period_1 + period_2,
            'current_cost': sum(period_3) / len(period_3),
            'threshold': 1.5
        })

        assert anomaly_3['is_anomaly'] is True
        assert anomaly_3['anomaly_score'] > 0.3

    def test_forecast_captures_trends(self):
        """✅ Forecast captures trends."""
        from guardian.ml.cost_forecasting import CostForecaster

        historical_costs = [100 + i * 2 for i in range(90)]

        forecaster = CostForecaster()
        forecast = forecaster.ensemble_forecast({
            'historical_costs': historical_costs,
            'periods': 30
        })

        # Forecast should be increasing (following trend)
        early_forecast = sum(forecast['forecast'][:10]) / 10
        late_forecast = sum(forecast['forecast'][20:]) / 10
        assert late_forecast > early_forecast

    def test_anomaly_in_integration(self):
        """✅ Anomaly detection works in pipeline."""
        from guardian.ml.cost_forecasting import CostAnomaly

        baseline = [100 + i * 0.5 for i in range(60)]
        current = 250

        detector = CostAnomaly()
        result = detector.detect_anomaly({
            'baseline_costs': baseline,
            'current_cost': current,
            'threshold': 2.0
        })

        assert result['is_anomaly'] is True
