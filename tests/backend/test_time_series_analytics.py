"""Tests for Phase 2 Time-Series Analytics (Trend Detection, Pattern Recognition, Forecasting)."""

from datetime import datetime, timedelta, timezone

import pytest


# ==========================================
# TrendDetector Tests
# ==========================================


class TestTrendDetector:
    """Test TrendDetector functionality."""

    @pytest.fixture
    def trend_detector(self):
        """Create a TrendDetector instance."""
        from guardian.analytics.trend_detector import TrendDetector

        return TrendDetector(window_size=24)

    def test_analyze_trend_increasing(self, trend_detector):
        """Test trend analysis for increasing trend."""
        # Generate increasing data points
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(12)]

        result = trend_detector.analyze_trend(data_points)

        assert result["trend_type"] == "INCREASING"
        assert result["slope"] > 0
        assert result["direction"] in ["SHARP_UP", "GRADUAL_UP"]
        assert result["confidence"] > 0.5

    def test_analyze_trend_stable(self, trend_detector):
        """Test trend analysis for stable trend."""
        # Generate stable data points
        data_points = [(50.0, f"2026-05-27T{i:02d}:00:00Z") for i in range(12)]

        result = trend_detector.analyze_trend(data_points)

        assert result["trend_type"] == "STABLE"
        assert result["direction"] == "FLAT"
        assert abs(result["slope"]) < 0.01

    def test_detect_trend_change(self, trend_detector):
        """Test detection of trend change."""
        trend_up = {"direction": "GRADUAL_UP", "slope": 0.5}
        trend_down = {"direction": "GRADUAL_DOWN", "slope": -0.5}

        result = trend_detector.detect_trend_change(trend_down, trend_up)

        assert result["change_detected"] is True
        assert result["change_type"] == "REVERSAL_DOWN"
        assert result["severity"] in ["HIGH", "MEDIUM", "LOW"]

    def test_forecast_next_value(self, trend_detector):
        """Test forecasting next values."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(10)]

        forecasts = trend_detector.forecast_next_value(data_points, periods=3)

        assert len(forecasts) == 3
        assert all(f > 0 for f in forecasts)
        # Values should be increasing
        assert forecasts[0] < forecasts[1] < forecasts[2]

    def test_get_trend_summary(self, trend_detector):
        """Test getting comprehensive trend summary."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(12)]

        summary = trend_detector.get_trend_summary(data_points)

        assert "trend_type" in summary
        assert "slope" in summary
        assert "min_value" in summary
        assert "max_value" in summary
        assert "volatility" in summary
        assert summary["min_value"] == 10.0
        assert summary["max_value"] == 32.0


# ==========================================
# PatternRecognizer Tests
# ==========================================


class TestPatternRecognizer:
    """Test PatternRecognizer functionality."""

    @pytest.fixture
    def pattern_recognizer(self):
        """Create a PatternRecognizer instance."""
        from guardian.analytics.pattern_recognizer import PatternRecognizer

        return PatternRecognizer()

    def test_identify_patterns(self, pattern_recognizer):
        """Test pattern identification."""
        # Create data with repeating patterns
        values = [10, 20, 30, 10, 20, 30, 10, 20, 30, 40, 50]
        data_points = [(float(v), f"2026-05-27T{i:02d}:00:00Z") for i, v in enumerate(values)]

        patterns = pattern_recognizer.identify_patterns(data_points, pattern_window=3)

        assert len(patterns) > 0
        # Check if (10, 20, 30) pattern is identified
        found_pattern = any(p["pattern"] == [10.0, 20.0, 30.0] for p in patterns)
        assert found_pattern

    def test_classify_pattern_constant(self, pattern_recognizer):
        """Test pattern classification for constant pattern."""
        pattern = (50.0, 50.0, 50.0)
        pattern_type = pattern_recognizer._classify_pattern(pattern)

        assert pattern_type == "CONSTANT"

    def test_classify_pattern_increasing(self, pattern_recognizer):
        """Test pattern classification for increasing pattern."""
        pattern = (10.0, 20.0, 30.0)
        pattern_type = pattern_recognizer._classify_pattern(pattern)

        assert pattern_type == "INCREASING"

    def test_detect_anomalous_pattern(self, pattern_recognizer):
        """Test anomalous pattern detection."""
        current = [100.0, 200.0, 300.0]
        normal = [[10.0, 20.0, 30.0], [15.0, 25.0, 35.0]]

        result = pattern_recognizer.detect_anomalous_pattern(current, normal, threshold=0.7)

        assert "is_anomalous" in result
        assert "similarity_score" in result
        assert "most_similar_pattern" in result

    def test_find_repeating_interval(self, pattern_recognizer):
        """Test finding repeating time intervals."""
        # Create data with 1-hour intervals
        data_points = []
        base_time = datetime(2026, 5, 27, 0, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            ts = (base_time + timedelta(hours=i)).isoformat()
            data_points.append((float(i * 10), ts))

        result = pattern_recognizer.find_repeating_interval(data_points)

        assert result is not None
        assert "interval_seconds" in result
        assert "occurrence_rate" in result
        assert result["interval_seconds"] == 3600  # 1 hour in seconds

    def test_get_pattern_statistics(self, pattern_recognizer):
        """Test comprehensive pattern statistics."""
        values = [10, 20, 30, 10, 20, 30, 40, 50]
        data_points = [(float(v), f"2026-05-27T{i:02d}:00:00Z") for i, v in enumerate(values)]

        stats = pattern_recognizer.get_pattern_statistics(data_points)

        assert "total_data_points" in stats
        assert "unique_patterns" in stats
        assert "patterns" in stats
        assert stats["total_data_points"] == 8


# ==========================================
# TimeSeriesForecast Tests
# ==========================================


class TestTimeSeriesForecast:
    """Test TimeSeriesForecast functionality."""

    @pytest.fixture
    def forecast_engine(self):
        """Create a TimeSeriesForecast instance."""
        from guardian.analytics.time_series_forecast import TimeSeriesForecast

        return TimeSeriesForecast()

    def test_exponential_smoothing(self, forecast_engine):
        """Test exponential smoothing forecasting."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(10)]

        forecasts = forecast_engine.exponential_smoothing(data_points, alpha=0.3, periods=5)

        assert len(forecasts) == 5
        for f in forecasts:
            assert "period" in f
            assert "forecast" in f
            assert "confidence" in f
            assert "lower_bound" in f
            assert "upper_bound" in f
            assert f["lower_bound"] <= f["forecast"] <= f["upper_bound"]

    def test_moving_average_forecast(self, forecast_engine):
        """Test moving average forecasting."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(10)]

        forecasts = forecast_engine.moving_average_forecast(data_points, window=3, periods=5)

        assert len(forecasts) == 5
        assert all(f["forecast"] > 0 for f in forecasts)
        # All forecasts should be similar (constant moving average)
        assert all(abs(f["forecast"] - forecasts[0]["forecast"]) < 5 for f in forecasts)

    def test_adaptive_forecast(self, forecast_engine):
        """Test adaptive forecasting combining multiple methods."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(10)]

        result = forecast_engine.adaptive_forecast(data_points, periods=5)

        assert result["forecast_available"] is True
        assert result["method"] == "adaptive"
        assert len(result["forecasts"]) == 5
        for f in result["forecasts"]:
            assert "exp_smoothing" in f
            assert "moving_average" in f
            assert "forecast" in f

    def test_forecast_anomaly_probability(self, forecast_engine):
        """Test anomaly probability calculation from forecast."""
        forecast = [
            {
                "forecast": 50.0,
                "lower_bound": 40.0,
                "upper_bound": 60.0,
            }
        ]

        # Test normal value
        result_normal = forecast_engine.forecast_anomaly_probability(forecast, 50.0)
        assert result_normal["anomaly_probability"] == 0.0
        assert result_normal["risk_level"] == "NONE"

        # Test anomalous value (below lower bound)
        result_anomaly = forecast_engine.forecast_anomaly_probability(forecast, 20.0)
        assert result_anomaly["anomaly_probability"] > 0
        assert result_anomaly["risk_level"] != "NONE"

    def test_detect_forecast_drift(self, forecast_engine):
        """Test detection of forecast drift."""
        previous = [{"forecast": 50.0}]
        current = [{"forecast": 100.0}]

        result = forecast_engine.detect_forecast_drift(previous, current)

        assert "drift_detected" in result
        assert "change_percentage" in result
        if abs(result["change_percentage"]) > 20:
            assert result["drift_detected"] is True

    def test_get_forecast_summary(self, forecast_engine):
        """Test comprehensive forecast summary."""
        data_points = [(10.0 + i * 2, f"2026-05-27T{i:02d}:00:00Z") for i in range(10)]

        summary = forecast_engine.get_forecast_summary(data_points)

        assert "current_value" in summary
        assert "historical_min" in summary
        assert "historical_max" in summary
        assert "historical_avg" in summary
        assert "forecast" in summary
        assert summary["current_value"] == 28.0  # Last value


# ==========================================
# Integration Tests
# ==========================================


class TestTimeSeriesAnalyticsIntegration:
    """Integration tests for time-series analytics."""

    def test_complete_analytics_pipeline(self):
        """Test complete analytics pipeline from trend to forecast."""
        from guardian.analytics.trend_detector import TrendDetector
        from guardian.analytics.pattern_recognizer import PatternRecognizer
        from guardian.analytics.time_series_forecast import TimeSeriesForecast

        # Create sample data
        values = []
        for cycle in range(3):
            for i in range(8):
                values.append(100 + (i * 5) + (cycle * 50))

        data_points = [(float(v), f"2026-05-27T{i:02d}:00:00Z") for i, v in enumerate(values)]

        # Step 1: Detect trend
        detector = TrendDetector()
        trend = detector.analyze_trend(data_points)
        assert trend["trend_type"] in ["INCREASING", "DECREASING", "STABLE"]

        # Step 2: Recognize patterns
        recognizer = PatternRecognizer()
        patterns = recognizer.identify_patterns(data_points)
        assert len(patterns) >= 0

        # Step 3: Forecast future values
        forecast_engine = TimeSeriesForecast()
        forecast = forecast_engine.adaptive_forecast(data_points, periods=3)
        assert forecast["forecast_available"] is True
        assert len(forecast["forecasts"]) == 3

        # Step 4: Check anomaly probability of last forecast
        current_value = data_points[-1][0]
        anomaly_result = forecast_engine.forecast_anomaly_probability(forecast["forecasts"], current_value)
        assert "anomaly_probability" in anomaly_result
        assert "risk_level" in anomaly_result
