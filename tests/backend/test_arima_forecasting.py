"""Tests for Sprint 64 Phase 1 - Seasonal ARIMA Forecasting."""

import pytest
from datetime import datetime, timedelta, timezone


# ==========================================
# ARIMAForecaster Tests
# ==========================================


class TestARIMAForecaster:
    """Test ARIMAForecaster functionality."""

    @pytest.fixture
    def arima_forecaster(self):
        """Create an ARIMAForecaster instance."""
        from guardian.analytics.arima_forecaster import ARIMAForecaster

        return ARIMAForecaster()

    def test_arima_initialization(self, arima_forecaster):
        """Test ARIMA forecaster initialization."""
        assert arima_forecaster is not None
        assert arima_forecaster.models == {}
        assert arima_forecaster.last_retrain is None

    def test_train_arima_model(self, arima_forecaster):
        """Test training ARIMA model on cost data."""
        # Generate synthetic seasonal cost data (3 years)
        import math
        import random
        random.seed(42)  # Reproducible
        historical_costs = []
        for month in range(36):
            base_cost = 1000.0 + (month * 5)  # Upward trend
            seasonal = 200.0 * math.sin(2 * math.pi * (month % 12) / 12)  # 12-month seasonality
            noise = random.gauss(0, 30)  # Random noise for stability
            cost = base_cost + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=month*30)).isoformat()
            historical_costs.append((cost, ts))

        model_id = arima_forecaster.train_model("test-account", historical_costs)

        assert model_id is not None
        assert model_id in arima_forecaster.models
        assert arima_forecaster.models[model_id] is not None

    def test_forecast_with_arima(self, arima_forecaster):
        """Test forecasting future costs using ARIMA."""
        # More realistic cost data with stronger seasonality
        import math
        import random
        random.seed(42)
        historical_costs = []
        for i in range(36):  # 3 years for better ARIMA training
            base = 1000.0 + (i * 10)  # Upward trend
            seasonal = 200.0 * math.sin(2 * math.pi * (i % 12) / 12)  # Strong seasonality
            noise = random.gauss(0, 25)  # Add noise for numerical stability
            cost = base + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i*30)).isoformat()
            historical_costs.append((cost, ts))

        model_id = arima_forecaster.train_model("test-account", historical_costs)
        forecasts = arima_forecaster.forecast(model_id, periods=12)

        assert forecasts is not None
        assert len(forecasts) == 12
        for forecast in forecasts:
            assert "period" in forecast
            assert "forecast" in forecast
            assert "lower_bound" in forecast
            assert "upper_bound" in forecast
            assert "confidence" in forecast
            assert forecast["lower_bound"] <= forecast["forecast"] <= forecast["upper_bound"]

    def test_model_accuracy_metrics(self, arima_forecaster):
        """Test model accuracy calculation (RMSE, MAPE)."""
        import math
        import random
        random.seed(43)
        # Create more realistic cost data for ARIMA training
        historical_costs = []
        for i in range(36):  # 3 years of data
            base = 1000.0 + (i * 5)
            seasonal = 150.0 * math.sin(2 * math.pi * (i % 12) / 12)
            noise = random.gauss(0, 20)
            cost = base + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i*30)).isoformat()
            historical_costs.append((cost, ts))

        model_id = arima_forecaster.train_model("test-account", historical_costs)
        metrics = arima_forecaster.get_model_metrics(model_id)

        assert metrics is not None
        assert "rmse" in metrics
        assert "mape" in metrics
        assert "aic" in metrics
        assert "bic" in metrics
        assert metrics["rmse"] >= 0
        assert metrics["mape"] >= 0

    def test_compare_models_arima_vs_linear(self, arima_forecaster):
        """Test comparing ARIMA vs linear regression models."""
        # Seasonal data where ARIMA should outperform linear
        import math
        import random
        random.seed(44)
        historical_costs = []
        for i in range(36):  # 3 years
            base = 1200.0 + (i * 8)
            seasonal = 300.0 * math.sin(2 * math.pi * (i % 12) / 12)  # Strong seasonality
            noise = random.gauss(0, 35)
            cost = base + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i*30)).isoformat()
            historical_costs.append((cost, ts))

        model_id = arima_forecaster.train_model("test-account", historical_costs)
        comparison = arima_forecaster.compare_with_linear(model_id, historical_costs)

        assert comparison is not None
        assert "arima_rmse" in comparison
        assert "linear_rmse" in comparison
        assert "arima_mape" in comparison
        assert "linear_mape" in comparison
        assert "improvement_percent" in comparison
        # Comparison metrics should be numeric
        assert isinstance(comparison["improvement_percent"], (int, float))

    def test_get_arima_parameters(self, arima_forecaster):
        """Test retrieving ARIMA parameters (p, d, q, P, D, Q, m)."""
        import math
        import random
        random.seed(45)
        # Create more realistic data
        historical_costs = []
        for i in range(36):  # 3 years
            base = 1500.0 + (i * 7)
            seasonal = 250.0 * math.sin(2 * math.pi * (i % 12) / 12)
            noise = random.gauss(0, 28)
            cost = base + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i*30)).isoformat()
            historical_costs.append((cost, ts))

        model_id = arima_forecaster.train_model("test-account", historical_costs)
        params = arima_forecaster.get_parameters(model_id)

        assert params is not None
        assert "order" in params  # (p, d, q)
        assert "seasonal_order" in params  # (P, D, Q, m)
        assert len(params["order"]) == 3
        assert len(params["seasonal_order"]) == 4

    def test_forecast_with_confidence_levels(self, arima_forecaster):
        """Test forecast with different confidence levels."""
        historical_costs = [(100.0 + i * 2, f"2024-{(i % 12) + 1:02d}-01T00:00:00Z") for i in range(24)]

        model_id = arima_forecaster.train_model("test-account", historical_costs)
        forecast_90 = arima_forecaster.forecast(model_id, periods=6, confidence=0.90)
        forecast_95 = arima_forecaster.forecast(model_id, periods=6, confidence=0.95)

        # 95% CI should be wider than 90% CI
        for i in range(len(forecast_90)):
            ci_width_90 = forecast_90[i]["upper_bound"] - forecast_90[i]["lower_bound"]
            ci_width_95 = forecast_95[i]["upper_bound"] - forecast_95[i]["lower_bound"]
            assert ci_width_95 > ci_width_90


# ==========================================
# SeasonalityDetector Tests
# ==========================================


class TestSeasonalityDetector:
    """Test SeasonalityDetector functionality."""

    @pytest.fixture
    def seasonality_detector(self):
        """Create a SeasonalityDetector instance."""
        from guardian.analytics.seasonality_detector import SeasonalityDetector

        return SeasonalityDetector()

    def test_detect_seasonality(self, seasonality_detector):
        """Test detecting seasonal patterns in data."""
        # Generate data with clear monthly seasonality
        values = []
        for month in range(24):
            value = 100 + (month % 12) * 20 + month * 0.5
            values.append(value)

        seasonality = seasonality_detector.detect_seasonality(values)

        assert seasonality is not None
        assert "is_seasonal" in seasonality
        assert "seasonal_period" in seasonality
        assert "strength" in seasonality
        assert seasonality["is_seasonal"] is True
        # Period should be around 12 for monthly seasonality
        assert seasonality["seasonal_period"] in [6, 12, 24]

    def test_decompose_series(self, seasonality_detector):
        """Test STL decomposition of time series."""
        # Generate seasonal series
        values = [100 + (i % 12) * 10 + i * 0.2 for i in range(36)]

        decomposition = seasonality_detector.decompose(values)

        assert decomposition is not None
        assert "trend" in decomposition
        assert "seasonal" in decomposition
        assert "residual" in decomposition
        assert len(decomposition["trend"]) == len(values)
        assert len(decomposition["seasonal"]) == len(values)
        assert len(decomposition["residual"]) == len(values)

    def test_identify_peak_season(self, seasonality_detector):
        """Test identifying peak and trough seasons."""
        # Generate monthly data with clear seasonality (peaks in Q4)
        values = []
        months = []
        for month in range(24):
            # Higher costs in Q4, lower in Q2
            base = 100 if month % 12 in [9, 10, 11] else 50
            value = base + (month * 0.1)
            values.append(value)
            months.append(month)

        peaks = seasonality_detector.identify_peaks(values, period=12)

        assert peaks is not None
        assert "peak_months" in peaks
        assert "trough_months" in peaks
        assert "peak_to_trough_ratio" in peaks
        assert len(peaks["peak_months"]) > 0
        assert len(peaks["trough_months"]) > 0


# ==========================================
# Integration Tests
# ==========================================


class TestARIMAIntegration:
    """Integration tests for ARIMA forecasting."""

    def test_complete_arima_forecasting_pipeline(self):
        """Test complete ARIMA pipeline: train, forecast, compare, decompose."""
        from guardian.analytics.arima_forecaster import ARIMAForecaster
        from guardian.analytics.seasonality_detector import SeasonalityDetector
        import math

        forecaster = ARIMAForecaster()
        detector = SeasonalityDetector()

        # Step 1: Generate seasonal cost data (3 years for better seasonality detection)
        import random
        random.seed(46)
        historical_costs = []
        for month in range(36):
            base = 1000.0 + (month * 5)  # Upward trend
            seasonal = 250.0 * math.sin(2 * math.pi * (month % 12) / 12)  # Strong 12-month seasonality
            noise = random.gauss(0, 30)
            cost = base + seasonal + noise
            ts = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=month*30)).isoformat()
            historical_costs.append((cost, ts))

        values = [c for c, _ in historical_costs]

        # Step 2: Detect seasonality
        seasonality = detector.detect_seasonality(values)
        assert seasonality["is_seasonal"] is True

        # Step 3: Train ARIMA model
        model_id = forecaster.train_model("integration-test", historical_costs)
        assert model_id is not None

        # Step 4: Get model metrics
        metrics = forecaster.get_model_metrics(model_id)
        assert metrics["rmse"] >= 0

        # Step 5: Generate forecast
        forecast = forecaster.forecast(model_id, periods=6)
        assert len(forecast) == 6

        # Step 6: Compare with linear
        comparison = forecaster.compare_with_linear(model_id, historical_costs)
        # Comparison should contain improvement metrics
        assert "improvement_percent" in comparison

        # Step 7: Decompose original series
        decomposition = detector.decompose(values)
        assert len(decomposition["trend"]) == len(values)
        assert len(decomposition["seasonal"]) == len(values)
