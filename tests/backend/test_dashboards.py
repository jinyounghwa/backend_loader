"""Real-time data visualization tests for AWS Guardian."""

import pytest


class TestDashboardBuilder:
    """Test dashboard creation and management."""

    def test_create_dashboard(self):
        """✅ Create new dashboard."""
        from guardian.visualization.dashboard import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Security Overview',
            'layout': 'grid',
            'widgets': ['threats', 'costs', 'compliance']
        })

        assert 'dashboard_id' in dashboard
        assert dashboard['name'] == 'Security Overview'

    def test_add_widgets_to_dashboard(self):
        """✅ Add widgets to dashboard."""
        from guardian.visualization.dashboard import DashboardBuilder

        builder = DashboardBuilder()

        result = builder.add_widget({
            'dashboard_id': 'dash_123',
            'widget_type': 'threat_map',
            'position': {'x': 0, 'y': 0, 'width': 6, 'height': 4}
        })

        assert 'widget_id' in result or 'added' in result
        assert 'position' in result or result.get('added') is True

    def test_save_dashboard_layout(self):
        """✅ Save dashboard layout configuration."""
        from guardian.visualization.dashboard import DashboardBuilder

        builder = DashboardBuilder()

        result = builder.save_layout({
            'dashboard_id': 'dash_123',
            'layout': {
                'widgets': [
                    {'type': 'threat_counter', 'position': [0, 0]},
                    {'type': 'cost_chart', 'position': [6, 0]}
                ],
                'theme': 'dark'
            }
        })

        assert 'saved' in result or 'layout_id' in result


class TestVisualizationEngine:
    """Test chart and graph rendering."""

    def test_render_line_chart(self):
        """✅ Render line chart."""
        from guardian.visualization.dashboard import VisualizationEngine

        engine = VisualizationEngine()

        chart = engine.render({
            'type': 'line',
            'data': [100, 105, 102, 108, 110],
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
            'title': 'Daily Threats'
        })

        assert 'chart_id' in chart
        assert 'svg' in chart or 'html' in chart

    def test_render_pie_chart(self):
        """✅ Render pie chart."""
        from guardian.visualization.dashboard import VisualizationEngine

        engine = VisualizationEngine()

        chart = engine.render({
            'type': 'pie',
            'data': [45, 30, 20, 5],
            'labels': ['High', 'Medium', 'Low', 'Info'],
            'title': 'Threat Distribution'
        })

        assert 'chart_id' in chart
        assert 'data' in chart or 'visualization' in chart

    def test_render_geo_map(self):
        """✅ Render geographical map."""
        from guardian.visualization.dashboard import VisualizationEngine

        engine = VisualizationEngine()

        map_chart = engine.render({
            'type': 'map',
            'markers': [
                {'lat': 37.7749, 'lng': -122.4194, 'label': 'SF'},
                {'lat': 40.7128, 'lng': -74.0060, 'label': 'NYC'}
            ],
            'title': 'Attack Origins'
        })

        assert 'chart_id' in map_chart
        assert 'markers' in map_chart or 'map_data' in map_chart


class TestRealTimeUpdater:
    """Test real-time dashboard updates."""

    def test_subscribe_to_updates(self):
        """✅ Subscribe to dashboard updates."""
        from guardian.visualization.dashboard import RealTimeUpdater

        updater = RealTimeUpdater()

        subscription = updater.subscribe({
            'dashboard_id': 'dash_123',
            'channels': ['threats', 'costs', 'incidents']
        })

        assert 'subscription_id' in subscription
        assert 'channels' in subscription

    def test_push_update_to_dashboard(self):
        """✅ Push real-time update to dashboard."""
        from guardian.visualization.dashboard import RealTimeUpdater

        updater = RealTimeUpdater()

        result = updater.push_update({
            'dashboard_id': 'dash_123',
            'channel': 'threats',
            'data': {
                'threat_count': 5,
                'severity': 'high',
                'timestamp': '2026-05-30T10:30:00Z'
            }
        })

        assert 'update_id' in result or 'sent' in result
        assert result.get('sent') is True or 'update_id' in result

    def test_batch_updates(self):
        """✅ Send batch updates efficiently."""
        from guardian.visualization.dashboard import RealTimeUpdater

        updater = RealTimeUpdater()

        result = updater.batch_update({
            'dashboard_id': 'dash_123',
            'updates': [
                {'channel': 'threats', 'data': {'count': 5}},
                {'channel': 'costs', 'data': {'total': 1250}},
                {'channel': 'incidents', 'data': {'open': 3}}
            ]
        })

        assert 'batch_id' in result or 'updated' in result


class TestChartRenderer:
    """Test chart rendering engine."""

    def test_render_multiple_series_chart(self):
        """✅ Render multi-series chart."""
        from guardian.visualization.dashboard import ChartRenderer

        renderer = ChartRenderer()

        chart = renderer.render({
            'type': 'bar',
            'series': [
                {'name': 'EC2 Threats', 'data': [10, 12, 15, 20]},
                {'name': 'S3 Threats', 'data': [5, 7, 6, 8]}
            ],
            'xAxis': ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        })

        assert 'chart_id' in chart
        assert 'series' in chart or 'rendered' in chart

    def test_apply_theme_to_chart(self):
        """✅ Apply theme to chart."""
        from guardian.visualization.dashboard import ChartRenderer

        renderer = ChartRenderer()

        themed_chart = renderer.apply_theme({
            'chart_id': 'chart_123',
            'theme': 'dark',
            'colors': ['#FF0000', '#00FF00', '#0000FF']
        })

        assert 'chart_id' in themed_chart
        assert 'theme' in themed_chart

    def test_export_chart_as_image(self):
        """✅ Export chart as image."""
        from guardian.visualization.dashboard import ChartRenderer

        renderer = ChartRenderer()

        export = renderer.export({
            'chart_id': 'chart_123',
            'format': 'png',
            'width': 1200,
            'height': 600
        })

        assert 'image_url' in export or 'file_path' in export
        assert 'format' in export


class TestDashboardIntegration:
    """End-to-end dashboard workflows."""

    def test_full_dashboard_setup(self):
        """✅ Complete dashboard creation and visualization."""
        from guardian.visualization.dashboard import (
            DashboardBuilder,
            VisualizationEngine
        )

        builder = DashboardBuilder()
        engine = VisualizationEngine()

        # Create dashboard
        dashboard = builder.create({
            'name': 'Security Console',
            'layout': 'grid'
        })
        assert 'dashboard_id' in dashboard

        # Add visualization
        chart = engine.render({
            'type': 'line',
            'data': [100, 105, 102]
        })
        assert 'chart_id' in chart

    def test_realtime_dashboard_updates(self):
        """✅ Real-time dashboard with live updates."""
        from guardian.visualization.dashboard import (
            DashboardBuilder,
            RealTimeUpdater
        )

        builder = DashboardBuilder()
        updater = RealTimeUpdater()

        # Create dashboard
        dash = builder.create({'name': 'Live Monitor'})

        # Subscribe to updates
        sub = updater.subscribe({
            'dashboard_id': dash['dashboard_id'],
            'channels': ['threats']
        })
        assert 'subscription_id' in sub

        # Push update
        update = updater.push_update({
            'dashboard_id': dash['dashboard_id'],
            'channel': 'threats',
            'data': {'count': 10}
        })
        assert 'update_id' in update or update.get('sent') is True

    def test_multi_widget_dashboard(self):
        """✅ Dashboard with multiple widget types."""
        from guardian.visualization.dashboard import (
            DashboardBuilder,
            VisualizationEngine
        )

        builder = DashboardBuilder()
        engine = VisualizationEngine()

        # Create dashboard
        dash = builder.create({'name': 'Multi-Widget'})

        # Add multiple widgets
        for widget_type in ['line', 'pie', 'map']:
            chart = engine.render({
                'type': widget_type,
                'data': [1, 2, 3]
            })
            assert 'chart_id' in chart

    def test_dashboard_with_live_metrics(self):
        """✅ Dashboard displaying live KPI metrics."""
        from guardian.visualization.dashboard import (
            DashboardBuilder,
            RealTimeUpdater,
            ChartRenderer
        )

        builder = DashboardBuilder()
        updater = RealTimeUpdater()
        renderer = ChartRenderer()

        # Setup
        dash = builder.create({'name': 'KPI Dashboard'})
        sub = updater.subscribe({'dashboard_id': dash['dashboard_id'], 'channels': ['kpi']})

        # Render metrics
        chart = renderer.render({
            'type': 'bar',
            'series': [{'name': 'Threats', 'data': [5, 10, 8]}]
        })

        # Push update
        update = updater.push_update({
            'dashboard_id': dash['dashboard_id'],
            'channel': 'kpi',
            'data': {'metric': 'threat_count', 'value': 15}
        })

        assert 'dashboard_id' in dash
        assert 'subscription_id' in sub
        assert 'chart_id' in chart
        assert 'update_id' in update or update.get('sent') is True
