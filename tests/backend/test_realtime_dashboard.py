"""Tests for Sprint 64 Phase 3 - WebSocket Real-Time Dashboard."""

import pytest


class TestWebSocketHandler:
    """Test WebSocket handler functionality."""

    @pytest.fixture
    def websocket_handler(self):
        """Create a WebSocketHandler instance."""
        from guardian.handlers.websocket_handler import WebSocketHandler
        return WebSocketHandler()

    def test_websocket_connect(self, websocket_handler):
        """Test WebSocket connection registration."""
        result = websocket_handler.handle_connect("conn-001", "123456789")
        assert result.get("success") is True
        assert result.get("connection_id") == "conn-001"
        assert "timestamp" in result

    def test_websocket_disconnect(self, websocket_handler):
        """Test WebSocket disconnection cleanup."""
        websocket_handler.handle_connect("conn-002", "123456789")
        result = websocket_handler.handle_disconnect("conn-002")
        assert result.get("success") is True
        assert result.get("connection_id") == "conn-002"

    def test_broadcast_cost_update(self, websocket_handler):
        """Test broadcasting cost update to connections."""
        websocket_handler.handle_connect("conn-003", "123456789")
        cost_data = {
            "current_cost": 1234.56,
            "forecast_cost": 1200.00,
            "trend": "↑",
            "variance_percent": 2.88,
        }
        result = websocket_handler.broadcast_cost_update("123456789", cost_data)
        assert result.get("success") is True
        assert result.get("broadcast_type") == "cost_update"

    def test_broadcast_recommendation_update(self, websocket_handler):
        """Test broadcasting recommendation update."""
        websocket_handler.handle_connect("conn-004", "123456789")
        recommendations = [
            {"id": "rec-001", "service": "ec2", "monthly_savings": 300},
            {"id": "rec-002", "service": "s3", "monthly_savings": 150},
        ]
        result = websocket_handler.broadcast_recommendation_update("123456789", recommendations)
        assert result.get("success") is True
        assert result.get("recommendations_sent") == 2


class TestCostStreamer:
    """Test CostStreamer functionality."""

    @pytest.fixture
    def cost_streamer(self):
        """Create a CostStreamer instance."""
        from guardian.analytics.cost_streamer import CostStreamer
        return CostStreamer()

    def test_get_current_cost(self, cost_streamer):
        """Test getting current cost snapshot with trend."""
        historical_costs = [1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
        result = cost_streamer.get_current_cost(1234.56, historical_costs)
        assert result["current_cost"] == 1234.56
        assert result["trend"] == "↑"
        assert "volatility_index" in result

    def test_stream_cost_updates(self, cost_streamer):
        """Test streaming cost updates."""
        historical_costs = [1000.0 + i * 10 for i in range(24)]
        forecast_values = [1240.0 + i * 5 for i in range(12)]
        stream = cost_streamer.stream_cost_updates(historical_costs, forecast_values, 5)
        assert len(stream) == 5
        for update in stream:
            assert "interval" in update
            assert "cost_info" in update
            assert "variance" in update

    def test_calculate_cost_variance(self, cost_streamer):
        """Test calculating variance between actual and forecast."""
        result = cost_streamer.calculate_cost_variance(1250.0, 1200.0)
        assert result["variance_amount"] == 50.0
        assert result["status"] == "over"

    def test_detect_anomalies(self, cost_streamer):
        """Test detecting cost anomalies."""
        cost_values = [1000.0, 1100.0, 1500.0, 1150.0]
        forecast_values = [1050.0, 1100.0, 1120.0, 1130.0]
        confidence_intervals = [
            {"lower_bound": 1000, "upper_bound": 1100},
            {"lower_bound": 1050, "upper_bound": 1150},
            {"lower_bound": 1050, "upper_bound": 1190},
            {"lower_bound": 1080, "upper_bound": 1180},
        ]
        anomalies = cost_streamer.detect_anomalies(cost_values, forecast_values, confidence_intervals)
        assert any(a.get("actual_cost") == 1500.0 for a in anomalies)

    def test_generate_cost_report(self, cost_streamer):
        """Test generating comprehensive cost report."""
        historical_costs = [1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
        forecast_values = [1050.0, 1100.0, 1120.0, 1140.0, 1160.0]
        report = cost_streamer.generate_cost_report(historical_costs, forecast_values, 1250.0)
        assert report["current_cost"] == 1250.0
        assert report["average_cost"] == 1100.0
        assert "forecast_accuracy" in report


class TestCostAlertHandler:
    """Test cost alert handler functionality."""

    @pytest.fixture
    def alert_handler(self):
        """Create a CostAlertHandler instance."""
        from guardian.handlers.cost_alert_handler import CostAlertHandler
        return CostAlertHandler()

    def test_check_cost_threshold(self, alert_handler):
        """Test cost threshold alert generation."""
        result = alert_handler.check_cost_threshold("123456789", 105.50, 100.0)
        assert result["alert_triggered"] is True
        assert result["current_cost"] == 105.50
        assert result["threshold"] == 100.0
        assert result["excess_amount"] == 5.50
        assert result["severity"] == "warning"

    def test_detect_cost_anomaly(self, alert_handler):
        """Test cost anomaly detection."""
        result = alert_handler.detect_cost_anomaly(
            actual_cost=1500.0,
            forecast_cost=1100.0,
            confidence_lower=1000.0,
            confidence_upper=1200.0,
        )
        assert result["is_anomaly"] is True
        assert result["variance_amount"] == 400.0
        assert result["severity"] in ["warning", "critical"]

    def test_generate_recommendation_alert(self, alert_handler):
        """Test recommendation alert generation."""
        recommendations = [
            {"id": "rec-001", "service": "ec2", "monthly_savings": 300, "confidence": 0.95},
            {"id": "rec-002", "service": "s3", "monthly_savings": 150, "confidence": 0.85},
        ]
        result = alert_handler.generate_recommendation_alert("123456789", recommendations)
        assert result["alert_triggered"] is True
        assert result["recommendations_count"] == 2
        assert result["total_annual_savings"] == 5400.0

    def test_alert_buffering_and_flush(self, alert_handler):
        """Test alert buffering and flushing."""
        # Generate multiple alerts
        alert_handler.check_cost_threshold("acc-001", 105.0, 100.0)
        alert_handler.detect_cost_anomaly(1500.0, 1100.0, 1000.0, 1200.0)

        # Verify alerts are buffered
        assert len(alert_handler.alerts_buffer) == 2

        # Flush alerts
        flushed = alert_handler.flush_alerts()
        assert len(flushed) == 2
        assert len(alert_handler.alerts_buffer) == 0
        assert len(alert_handler.alert_history) == 2


class TestRealtimeDashboardIntegration:
    """Integration tests for real-time dashboard."""

    def test_websocket_cost_stream_integration(self):
        """Test integration of WebSocket and cost streaming."""
        from guardian.handlers.websocket_handler import WebSocketHandler
        from guardian.analytics.cost_streamer import CostStreamer

        handler = WebSocketHandler()
        streamer = CostStreamer()
        
        handler.handle_connect("test-conn", "123456789")
        historical_costs = [1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
        forecast_values = [1050.0, 1100.0, 1120.0, 1140.0, 1160.0]
        stream = streamer.stream_cost_updates(historical_costs, forecast_values, 3)
        
        if stream:
            result = handler.broadcast_cost_update("123456789", {"current_cost": 1234.56})
            assert result.get("success") is True

    def test_complete_dashboard_workflow(self):
        """Test complete real-time dashboard workflow."""
        from guardian.handlers.websocket_handler import WebSocketHandler
        from guardian.analytics.cost_streamer import CostStreamer
        from guardian.analytics.recommendation_engine import RecommendationEngine

        ws_handler = WebSocketHandler()
        cost_streamer = CostStreamer()
        engine = RecommendationEngine()

        ws_handler.handle_connect("test-workflow", "123456789")

        # High volatility cost pattern (Q4 peak, Q2 trough)
        historical_costs = []
        for month in range(12):
            if month % 12 in [9, 10, 11]:  # Q4
                base = 1500.0
            else:
                base = 1000.0
            noise = month * 5.0  # Slight upward trend
            historical_costs.append(base + noise)

        cost_info = cost_streamer.get_current_cost(1300.0, historical_costs)
        assert cost_info.get("current_cost") == 1300.0

        services_costs = {"ec2": historical_costs}
        seasonality = {"is_seasonal": True, "strength": 0.6}  # > 0.5 to trigger seasonal adjustment
        opportunities = engine.identify_opportunities(services_costs, seasonality)
        assert len(opportunities) > 0

        ws_handler.handle_disconnect("test-workflow")
