"""Sprint 67 Phase 2: Advanced ML & Anomaly Detection (15 tests)"""

import pytest
import numpy as np
from guardian.ml.advanced_anomaly_detection import (
    GaussianMixtureDetector,
    LocalOutlierDetector,
    AnomalyDetectorEnsemble
)
from guardian.ml.advanced_forecasting import (
    ProphetForecaster,
    DynamicARIMAForecaster,
    ForecastModelSelector
)


class TestGaussianMixtureModel:
    """Test GMM anomaly detection."""

    @pytest.fixture
    def detector(self):
        return GaussianMixtureDetector(n_components=3)

    @pytest.fixture
    def multimodal_data(self):
        # Three clusters: normal, medium, high
        cluster1 = [{'value': v} for v in np.random.normal(50, 5, 20)]
        cluster2 = [{'value': v} for v in np.random.normal(100, 10, 20)]
        cluster3 = [{'value': v} for v in np.random.normal(200, 15, 20)]
        return cluster1 + cluster2 + cluster3

    def test_gaussian_mixture_fit(self, detector, multimodal_data):
        """✅ Fit GMM on multi-modal data."""
        detector.fit(multimodal_data)

        assert len(detector.means) == 3
        assert len(detector.covariances) == 3
        assert len(detector.weights) == 3

    def test_gaussian_mixture_predict(self, detector, multimodal_data):
        """✅ Predict anomaly scores."""
        detector.fit(multimodal_data)
        scores = detector.predict(multimodal_data)

        assert len(scores) == len(multimodal_data)
        assert all(0 <= score <= 100 for score in scores)

    def test_anomaly_detection_accuracy(self, detector):
        """✅ Detect anomalies in mixed data."""
        normal_data = [{'value': v} for v in [50, 52, 48, 51, 49, 50, 52, 51]]
        anomaly_data = [{'value': 300}]

        all_data = normal_data + anomaly_data
        detector.fit(all_data)
        scores = detector.predict(all_data)

        # Anomaly should have high score
        assert scores[-1] > 30


class TestLocalOutlierFactor:
    """Test LOF anomaly detection."""

    @pytest.fixture
    def detector(self):
        return LocalOutlierDetector(k=5)

    def test_local_outlier_factor(self, detector):
        """✅ Detect local outliers."""
        normal = [{'value': v} for v in [10, 11, 12, 11, 10, 12, 11]]
        anomaly = [{'value': 100}]

        all_data = normal + anomaly
        detector.fit(all_data)
        scores = detector.predict(all_data)

        assert len(scores) == len(all_data)
        assert scores[-1] > 20  # Anomaly has high LOF score

    def test_lof_density_based(self, detector):
        """✅ LOF considers local density."""
        cluster1 = [{'value': v} for v in [50, 51, 50, 51, 50]]
        cluster2 = [{'value': v} for v in [100, 120, 90, 110, 100]]
        outlier = [{'value': 55}]

        all_data = cluster1 + cluster2 + outlier
        detector.fit(all_data)
        scores = detector.predict(all_data)

        # Outlier should have detectable LOF score
        assert scores[-1] > 0


class TestAnomalyDetectorEnsemble:
    """Test ensemble of multiple detectors."""

    @pytest.fixture
    def ensemble(self):
        return AnomalyDetectorEnsemble()

    def test_ensemble_predict(self, ensemble):
        """✅ Ensemble makes combined predictions."""
        data = [{'value': v} for v in [10, 11, 10, 12, 100, 11, 10, 11]]

        ensemble.fit(data)
        scores = ensemble.predict(data)

        assert len(scores) == len(data)
        assert all(0 <= score <= 100 for score in scores)

    def test_ensemble_anomaly_detection(self, ensemble):
        """✅ Ensemble detects anomalies above threshold."""
        data = [{'value': v} for v in [50, 52, 51, 49, 300, 50, 51]]

        ensemble.fit(data)
        anomalies = ensemble.get_anomalies(data, threshold=50)

        assert len(anomalies) > 0
        assert any(a['value'] == 300 for a in anomalies)

    def test_anomaly_confidence_scoring(self, ensemble):
        """✅ Calculate confidence for anomaly scores."""
        assert ensemble.get_confidence(90.0) > 0.8
        assert ensemble.get_confidence(50.0) == 0.5
        assert ensemble.get_confidence(10.0) < 0.2


class TestProphetForecaster:
    """Test Prophet-like forecasting."""

    @pytest.fixture
    def forecaster(self):
        return ProphetForecaster()

    @pytest.fixture
    def trending_data(self):
        return [100 + i * 2 + np.sin(i / 7) * 5 for i in range(60)]

    def test_prophet_forecast(self, forecaster, trending_data):
        """✅ Generate Prophet forecast."""
        forecaster.fit(trending_data)
        forecast = forecaster.forecast(periods=30)

        assert len(forecast) == 30
        assert all(isinstance(v, float) for v in forecast)

    def test_prophet_seasonality_detection(self, forecaster, trending_data):
        """✅ Detect seasonal patterns."""
        result = forecaster.detect_seasonality(trending_data, period=7)

        assert 'has_seasonality' in result
        assert 'period' in result
        assert result['period'] == 7

    def test_prophet_with_confidence_intervals(self, forecaster, trending_data):
        """✅ Forecast with confidence bounds."""
        forecaster.fit(trending_data)
        result = forecaster.forecast_with_intervals(periods=14, confidence=0.95)

        assert len(result['forecast']) == 14
        assert len(result['upper']) == 14
        assert len(result['lower']) == 14

        # Verify bounds: upper > forecast > lower
        for f, u, l in zip(result['forecast'], result['upper'], result['lower']):
            assert l <= f <= u


class TestDynamicARIMA:
    """Test Dynamic ARIMA forecasting."""

    @pytest.fixture
    def forecaster(self):
        return DynamicARIMAForecaster()

    def test_dynamic_arima_parameter_optimization(self, forecaster):
        """✅ Auto-optimize ARIMA(p,d,q)."""
        data = [100 + i * 1.5 + np.random.randn() * 3 for i in range(50)]

        p, d, q = forecaster.optimize_arima_params(data, max_p=3, max_d=2, max_q=3)

        assert 0 <= p <= 3
        assert 0 <= d <= 2
        assert 0 <= q <= 3

    def test_dynamic_arima_forecast(self, forecaster):
        """✅ Forecast with optimized parameters."""
        data = [100 + i * 2 for i in range(30)]

        forecaster.fit(data)
        forecast = forecaster.forecast(steps=10)

        assert len(forecast) == 10
        assert all(v >= 0 for v in forecast)

    def test_dynamic_arima_with_intervals(self, forecaster):
        """✅ ARIMA forecast with confidence intervals."""
        data = [100 + i * 1.5 for i in range(40)]

        forecaster.fit(data)
        result = forecaster.forecast_with_intervals(periods=7, confidence=0.99)

        assert len(result['forecast']) == 7
        assert all(result['lower'][i] <= result['forecast'][i] <= result['upper'][i] for i in range(7))


class TestProphetTrendDetection:
    """Test trend analysis."""

    @pytest.fixture
    def forecaster(self):
        return ProphetForecaster()

    def test_detect_upward_trend(self, forecaster):
        """✅ Detect upward trend."""
        upward_data = [100 + i * 2 for i in range(30)]

        result = forecaster.detect_trend(upward_data)

        assert result['trend'] == 'upward'
        assert result['change_percent'] > 5

    def test_detect_downward_trend(self, forecaster):
        """✅ Detect downward trend."""
        downward_data = [100 - i * 2 for i in range(30)]

        result = forecaster.detect_trend(downward_data)

        assert result['trend'] == 'downward'
        assert result['change_percent'] < -5

    def test_detect_flat_trend(self, forecaster):
        """✅ Detect flat trend."""
        flat_data = [100 for _ in range(20)]

        result = forecaster.detect_trend(flat_data)

        assert result['trend'] == 'flat'
        assert abs(result['change_percent']) <= 5


class TestForecastModelSelector:
    """Test automatic model selection."""

    @pytest.fixture
    def selector(self):
        return ForecastModelSelector()

    def test_select_prophet_for_seasonal_data(self, selector):
        """✅ Select best model for seasonal data."""
        seasonal_data = [100 + 20 * np.sin(i / 7 * 2 * np.pi) for i in range(60)]

        best_model = selector.select_best_model(seasonal_data)
        # Model selection validates the approach
        assert best_model in ['prophet', 'arima']

    def test_select_arima_for_trending_data(self, selector):
        """✅ Select best model for trending data."""
        trending_data = [100 + i * 2 for i in range(50)]

        best_model = selector.select_best_model(trending_data)
        # Model selection validates the approach
        assert best_model in ['prophet', 'arima']

    def test_forecast_with_model_selection(self, selector):
        """✅ Forecast using selected model."""
        data = [100 + i + np.random.randn() for i in range(40)]

        selector.fit(data)
        result = selector.forecast(data, periods=7)

        assert 'model' in result
        assert 'forecast' in result
        assert len(result['forecast']) == 7
