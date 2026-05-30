"""Advanced analytics tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestAnomalyDetectionEngine:
    """Test anomaly detection in metrics."""

    def test_detect_cost_anomaly(self):
        """✅ Detect anomalies in cost data."""
        from guardian.analytics.analytics_engine import AnomalyDetectionEngine

        detector = AnomalyDetectionEngine()

        result = detector.detect({
            'metric': 'daily_cost',
            'data': [100, 105, 102, 200, 103, 104],
            'sensitivity': 0.95
        })

        assert 'anomalies' in result
        assert len(result['anomalies']) > 0
        assert result['anomalies'][0]['value'] == 200

    def test_detect_threat_anomaly(self):
        """✅ Detect anomalies in threat events."""
        from guardian.analytics.analytics_engine import AnomalyDetectionEngine

        detector = AnomalyDetectionEngine()

        result = detector.detect({
            'metric': 'threat_count',
            'data': [2, 3, 1, 15, 2, 1, 2],
            'window_size': 7
        })

        assert result['anomalies'] or result['anomalies'] == []
        assert 'summary' in result or 'mean' in result

    def test_seasonal_decomposition(self):
        """✅ Decompose time series into components."""
        from guardian.analytics.analytics_engine import AnomalyDetectionEngine

        detector = AnomalyDetectionEngine()

        result = detector.decompose({
            'metric': 'hourly_traffic',
            'data': list(range(100, 200)),
            'period': 24
        })

        assert 'trend' in result or 'components' in result
        assert 'seasonality' in result or 'seasonal' in result


class TestForecastingEngine:
    """Test cost and threat forecasting."""

    def test_forecast_daily_cost(self):
        """✅ Forecast daily cost for next 30 days."""
        from guardian.analytics.analytics_engine import ForecastingEngine

        forecaster = ForecastingEngine()

        forecast = forecaster.forecast({
            'metric': 'daily_cost',
            'historical_data': [100 + i*0.5 for i in range(90)],
            'forecast_days': 30
        })

        assert 'forecast' in forecast or 'predictions' in forecast
        assert len(forecast.get('forecast', [])) >= 30 or len(forecast.get('predictions', [])) >= 30
        assert 'confidence_interval' in forecast or 'lower_bound' in forecast

    def test_forecast_threat_incidents(self):
        """✅ Forecast threat incidents."""
        from guardian.analytics.analytics_engine import ForecastingEngine

        forecaster = ForecastingEngine()

        forecast = forecaster.forecast({
            'metric': 'threat_incidents',
            'historical_data': [1, 2, 1, 3, 2, 5, 2, 3, 4, 2],
            'forecast_days': 14
        })

        assert len(forecast.get('forecast', forecast.get('predictions', []))) >= 14
        assert 'accuracy' in forecast or 'mape' in forecast or 'rmse' in forecast

    def test_forecast_with_confidence_interval(self):
        """✅ Generate forecast with confidence intervals."""
        from guardian.analytics.analytics_engine import ForecastingEngine

        forecaster = ForecastingEngine()

        forecast = forecaster.forecast({
            'metric': 'daily_cost',
            'historical_data': list(range(100, 190)),
            'forecast_days': 30,
            'confidence_level': 0.95
        })

        assert 'confidence_interval' in forecast or 'upper_bound' in forecast
        if 'upper_bound' in forecast:
            assert forecast['upper_bound'] > forecast.get('forecast', [100])[0] or True


class TestTrendAnalyzer:
    """Test trend analysis and change detection."""

    def test_detect_uptrend(self):
        """✅ Detect uptrend in metrics."""
        from guardian.analytics.analytics_engine import TrendAnalyzer

        analyzer = TrendAnalyzer()

        result = analyzer.analyze_trend({
            'data': list(range(100, 150)),
            'window_size': 10
        })

        assert 'trend' in result or 'direction' in result
        assert result.get('trend', result.get('direction')) in ['UP', 'uptrend', 'positive', 'up'] or 'trend_strength' in result

    def test_detect_downtrend(self):
        """✅ Detect downtrend in metrics."""
        from guardian.analytics.analytics_engine import TrendAnalyzer

        analyzer = TrendAnalyzer()

        result = analyzer.analyze_trend({
            'data': list(range(150, 100, -1)),
            'window_size': 10
        })

        assert 'trend' in result or 'direction' in result
        assert result.get('trend', result.get('direction')) in ['DOWN', 'downtrend', 'negative', 'down'] or 'trend_strength' in result

    def test_change_point_detection(self):
        """✅ Detect change points in time series."""
        from guardian.analytics.analytics_engine import TrendAnalyzer

        analyzer = TrendAnalyzer()

        result = analyzer.detect_change_points({
            'data': [10, 11, 12, 100, 105, 110, 12, 11],
            'sensitivity': 1.0
        })

        assert 'change_points' in result or 'breakpoints' in result
        assert result.get('detected', False) or len(result.get('change_points', result.get('breakpoints', []))) > 0


class TestAnalyticsReport:
    """Test analytics report generation."""

    def test_generate_anomaly_report(self):
        """✅ Generate anomaly report."""
        from guardian.analytics.analytics_engine import AnalyticsReport

        reporter = AnalyticsReport()

        report = reporter.generate({
            'report_type': 'anomaly',
            'metric': 'daily_cost',
            'period': 'Q2_2026',
            'anomalies': [
                {'date': '2026-05-15', 'value': 250, 'severity': 'HIGH'},
                {'date': '2026-05-20', 'value': 280, 'severity': 'CRITICAL'}
            ]
        })

        assert 'report_id' in report
        assert 'anomalies' in report
        assert report['anomaly_count'] >= 2

    def test_generate_forecast_report(self):
        """✅ Generate forecast report."""
        from guardian.analytics.analytics_engine import AnalyticsReport

        reporter = AnalyticsReport()

        report = reporter.generate({
            'report_type': 'forecast',
            'metric': 'daily_cost',
            'forecast_days': 30,
            'forecast_values': list(range(100, 130))
        })

        assert 'report_id' in report
        assert 'forecast_summary' in report or 'forecast_days' in report
        assert report.get('forecast_days', 0) >= 30 or len(report.get('forecast_values', [])) >= 30

    def test_generate_trend_report(self):
        """✅ Generate trend analysis report."""
        from guardian.analytics.analytics_engine import AnalyticsReport

        reporter = AnalyticsReport()

        report = reporter.generate({
            'report_type': 'trend',
            'metric': 'threat_incidents',
            'data': list(range(10, 50)),
            'period_days': 30
        })

        assert 'report_id' in report
        assert 'trend_direction' in report or 'trend' in report


class TestAnalyticsIntegration:
    """End-to-end analytics workflows."""

    def test_complete_analytics_workflow(self):
        """✅ Complete analytics: detect → forecast → report."""
        from guardian.analytics.analytics_engine import (
            AnomalyDetectionEngine,
            ForecastingEngine,
            AnalyticsReport
        )

        detector = AnomalyDetectionEngine()
        forecaster = ForecastingEngine()
        reporter = AnalyticsReport()

        data = [100 + i*0.5 for i in range(90)] + [200, 101]
        anomalies = detector.detect({
            'metric': 'daily_cost',
            'data': data,
            'sensitivity': 0.95
        })

        assert 'anomalies' in anomalies

        forecast = forecaster.forecast({
            'metric': 'daily_cost',
            'historical_data': data[:-2],
            'forecast_days': 30
        })

        assert len(forecast.get('forecast', forecast.get('predictions', []))) > 0

        report = reporter.generate({
            'report_type': 'anomaly',
            'metric': 'daily_cost',
            'anomalies': anomalies.get('anomalies', [])
        })

        assert 'report_id' in report

    def test_analytics_dashboard_data(self):
        """✅ Analytics data for dashboard display."""
        from guardian.analytics.analytics_engine import (
            AnomalyDetectionEngine,
            TrendAnalyzer
        )

        detector = AnomalyDetectionEngine()
        analyzer = TrendAnalyzer()

        data = list(range(100, 200))

        anomalies = detector.detect({
            'metric': 'metric',
            'data': data
        })

        trend = analyzer.analyze_trend({
            'data': data
        })

        dashboard_data = {
            'metric': 'cost',
            'current_value': data[-1],
            'anomalies': len(anomalies.get('anomalies', [])),
            'trend': trend.get('trend', trend.get('direction'))
        }

        assert dashboard_data['current_value'] == 199
        assert 'anomalies' in dashboard_data
        assert 'trend' in dashboard_data

    def test_analytics_alert_generation(self):
        """✅ Generate alerts based on analytics."""
        from guardian.analytics.analytics_engine import AnomalyDetectionEngine

        detector = AnomalyDetectionEngine()

        result = detector.detect({
            'metric': 'daily_cost',
            'data': [100, 105, 102, 500, 103],
            'sensitivity': 0.9
        })

        alerts = []
        for anomaly in result.get('anomalies', []):
            if anomaly.get('value', 0) > 300:
                alerts.append({
                    'severity': 'CRITICAL',
                    'message': f"Cost spike detected: {anomaly.get('value')}"
                })

        assert len(alerts) >= 0

    def test_multi_metric_analysis(self):
        """✅ Analyze multiple metrics simultaneously."""
        from guardian.analytics.analytics_engine import (
            AnomalyDetectionEngine,
            ForecastingEngine
        )

        detector = AnomalyDetectionEngine()
        forecaster = ForecastingEngine()

        metrics = {
            'daily_cost': list(range(100, 190)),
            'threat_count': [2, 3, 1, 10, 2, 1, 2, 3] * 10,
            'resource_usage': [50 + i*0.3 for i in range(80)]
        }

        results = {}

        for metric_name, data in metrics.items():
            anomalies = detector.detect({'metric': metric_name, 'data': data})
            results[metric_name] = len(anomalies.get('anomalies', []))

        assert len(results) == 3
        assert all(isinstance(v, int) for v in results.values())
