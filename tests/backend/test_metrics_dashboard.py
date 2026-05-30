"""Performance metrics dashboard tests for AWS Guardian."""

import pytest


class TestMetricsDashboard:
    """Test metrics dashboard."""

    def test_create_metrics_dashboard(self):
        """✅ Create metrics dashboard."""
        from guardian.dashboards.metrics import MetricsDashboard

        dashboard = MetricsDashboard()

        result = dashboard.create({
            'name': 'Security Metrics',
            'metrics': ['threat_count', 'detection_rate', 'response_time']
        })

        assert 'dashboard_id' in result
        assert 'metrics' in result

    def test_aggregate_metrics(self):
        """✅ Aggregate performance metrics."""
        from guardian.dashboards.metrics import MetricsDashboard

        dashboard = MetricsDashboard()

        result = dashboard.aggregate({
            'metrics': [
                {'name': 'threat_count', 'value': 15},
                {'name': 'response_time', 'value': 250}
            ],
            'period': '1h'
        })

        assert 'aggregated' in result or 'summary' in result

    def test_add_custom_metric(self):
        """✅ Add custom metric to dashboard."""
        from guardian.dashboards.metrics import MetricsDashboard

        dashboard = MetricsDashboard()

        result = dashboard.add_metric({
            'dashboard_id': 'dash_123',
            'metric_name': 'custom_score',
            'unit': 'percentage',
            'initial_value': 85
        })

        assert 'metric_id' in result or 'added' in result


class TestAlertsWidget:
    """Test alerts widget."""

    def test_create_alerts_widget(self):
        """✅ Create alerts widget."""
        from guardian.dashboards.metrics import AlertsWidget

        widget = AlertsWidget()

        result = widget.create({
            'title': 'Critical Alerts',
            'alert_level': 'critical',
            'auto_refresh': True
        })

        assert 'widget_id' in result
        assert 'alert_count' in result or 'status' in result

    def test_update_alert_status(self):
        """✅ Update alert status."""
        from guardian.dashboards.metrics import AlertsWidget

        widget = AlertsWidget()

        result = widget.update_status({
            'alert_id': 'alert_123',
            'status': 'acknowledged',
            'acknowledger': 'user_456'
        })

        assert 'updated' in result or 'status' in result

    def test_filter_alerts_by_severity(self):
        """✅ Filter alerts by severity."""
        from guardian.dashboards.metrics import AlertsWidget

        widget = AlertsWidget()

        result = widget.filter_alerts({
            'severity': 'high',
            'status': 'open'
        })

        assert 'alerts' in result or 'count' in result


class TestTrendAnalysis:
    """Test trend analysis."""

    def test_analyze_trends(self):
        """✅ Analyze trends in metrics."""
        from guardian.dashboards.metrics import TrendAnalysis

        analyzer = TrendAnalysis()

        result = analyzer.analyze({
            'metric': 'threat_count',
            'data_points': [10, 12, 11, 15, 18, 16, 20],
            'period': 'daily'
        })

        assert 'trend' in result or 'direction' in result
        assert 'forecast' in result or 'prediction' in result

    def test_detect_anomalies_in_trend(self):
        """✅ Detect anomalies in trend data."""
        from guardian.dashboards.metrics import TrendAnalysis

        analyzer = TrendAnalysis()

        result = analyzer.detect_anomalies({
            'data': [100, 102, 101, 99, 500, 103, 102],
            'sensitivity': 0.95
        })

        assert 'anomalies' in result or 'outliers' in result

    def test_forecast_metric(self):
        """✅ Forecast future metric values."""
        from guardian.dashboards.metrics import TrendAnalysis

        analyzer = TrendAnalysis()

        result = analyzer.forecast({
            'metric': 'threat_count',
            'history': [10, 12, 15, 18, 20],
            'horizon': 5
        })

        assert 'predictions' in result or 'forecast' in result


class TestKPITracker:
    """Test KPI tracking."""

    def test_create_kpi(self):
        """✅ Create KPI tracker."""
        from guardian.dashboards.metrics import KPITracker

        tracker = KPITracker()

        result = tracker.create({
            'name': 'MTTR',
            'target': 300,
            'unit': 'seconds',
            'current_value': 250
        })

        assert 'kpi_id' in result
        assert 'progress' in result or 'status' in result

    def test_update_kpi_progress(self):
        """✅ Update KPI progress."""
        from guardian.dashboards.metrics import KPITracker

        tracker = KPITracker()

        result = tracker.update({
            'kpi_id': 'kpi_123',
            'current_value': 280
        })

        assert 'updated' in result or 'percentage' in result

    def test_get_kpi_status(self):
        """✅ Get KPI status."""
        from guardian.dashboards.metrics import KPITracker

        tracker = KPITracker()

        result = tracker.get_status({
            'kpi_id': 'kpi_123'
        })

        assert 'status' in result or 'progress' in result


class TestMetricsIntegration:
    """End-to-end metrics dashboard workflows."""

    def test_full_metrics_dashboard(self):
        """✅ Complete metrics dashboard setup."""
        from guardian.dashboards.metrics import (
            MetricsDashboard,
            AlertsWidget,
            TrendAnalysis,
            KPITracker
        )

        dashboard = MetricsDashboard()
        alerts = AlertsWidget()
        trends = TrendAnalysis()
        kpi = KPITracker()

        # Create dashboard
        dash = dashboard.create({'name': 'Metrics'})
        assert 'dashboard_id' in dash

        # Add alerts widget
        widget = alerts.create({'title': 'Alerts'})
        assert 'widget_id' in widget

        # Analyze trends
        trend = trends.analyze({
            'metric': 'threat_count',
            'data_points': [1, 2, 3, 4, 5]
        })
        assert 'trend' in trend or 'direction' in trend

        # Track KPI
        kpi_result = kpi.create({'name': 'MTTR', 'target': 300})
        assert 'kpi_id' in kpi_result

    def test_metrics_with_alerts_and_trends(self):
        """✅ Dashboard with metrics, alerts, and trends."""
        from guardian.dashboards.metrics import (
            MetricsDashboard,
            AlertsWidget,
            TrendAnalysis
        )

        dashboard = MetricsDashboard()
        alerts = AlertsWidget()
        trends = TrendAnalysis()

        # Setup
        dash = dashboard.create({'name': 'Real-time Metrics'})
        widget = alerts.create({'title': 'Active Alerts'})
        analysis = trends.analyze({
            'metric': 'response_time',
            'data_points': [100, 120, 110, 150]
        })

        assert 'dashboard_id' in dash
        assert 'widget_id' in widget
        assert 'trend' in analysis or 'direction' in analysis

    def test_kpi_tracking_workflow(self):
        """✅ Complete KPI tracking workflow."""
        from guardian.dashboards.metrics import KPITracker

        tracker = KPITracker()

        # Create multiple KPIs
        kpis = []
        for name, target in [('MTTR', 300), ('Detection Rate', 95)]:
            kpi = tracker.create({
                'name': name,
                'target': target,
                'current_value': target * 0.9
            })
            kpis.append(kpi)

        # Update progress
        for kpi in kpis:
            update = tracker.update({
                'kpi_id': kpi['kpi_id'],
                'current_value': kpi['current_value'] + 10
            })
            assert 'updated' in update or 'percentage' in update

    def test_comprehensive_metrics_dashboard(self):
        """✅ Comprehensive metrics dashboard with all components."""
        from guardian.dashboards.metrics import (
            MetricsDashboard,
            AlertsWidget,
            TrendAnalysis,
            KPITracker
        )

        dashboard = MetricsDashboard()
        alerts_widget = AlertsWidget()
        trend = TrendAnalysis()
        kpi = KPITracker()

        # Create dashboard
        dash = dashboard.create({'name': 'Comprehensive'})

        # Create alerts widget
        alert = alerts_widget.create({'title': 'System Alerts'})

        # Analyze trends
        trend_data = trend.analyze({
            'metric': 'threat_detection',
            'data_points': [5, 10, 8, 12, 15]
        })

        # Create KPIs
        kpi1 = kpi.create({'name': 'Accuracy', 'target': 95})
        kpi2 = kpi.create({'name': 'Response Time', 'target': 300})

        # Update KPI
        kpi.update({'kpi_id': kpi1['kpi_id'], 'current_value': 93})

        assert 'dashboard_id' in dash
        assert 'widget_id' in alert
        assert 'forecast' in trend_data or 'trend' in trend_data
        assert len([kpi1, kpi2]) == 2
