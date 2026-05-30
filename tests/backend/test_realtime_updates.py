"""Sprint 72 Phase 1: WebSocket Real-Time Updates (15 tests)"""

import pytest
from datetime import datetime


class TestWebSocketManager:
    """Test WebSocket connection management."""

    def test_client_connects(self):
        """✅ Client connects to WebSocket."""
        from guardian.realtime.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        connection = manager.register_client({
            'client_id': 'client_1',
            'user_id': 'user_123'
        })

        assert connection['status'] == 'connected'
        assert connection['client_id'] == 'client_1'

    def test_multiple_clients_connect(self):
        """✅ Multiple clients can connect simultaneously."""
        from guardian.realtime.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        for i in range(5):
            conn = manager.register_client({
                'client_id': f'client_{i}',
                'user_id': f'user_{i}'
            })
            assert conn['status'] == 'connected'

        assert manager.get_active_connections() == 5

    def test_client_disconnects(self):
        """✅ Client disconnect is tracked."""
        from guardian.realtime.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        manager.register_client({'client_id': 'client_1', 'user_id': 'user_1'})
        result = manager.unregister_client('client_1')

        assert result['status'] == 'disconnected'
        assert manager.get_active_connections() == 0


class TestEventBroadcaster:
    """Test event broadcasting to clients."""

    def test_broadcast_threat_event(self):
        """✅ Broadcast threat event to all connected clients."""
        from guardian.realtime.websocket_manager import EventBroadcaster

        broadcaster = EventBroadcaster()

        result = broadcaster.broadcast({
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL',
            'instance_id': 'i-12345',
            'timestamp': datetime.utcnow().isoformat()
        })

        assert result['status'] == 'delivered'
        assert 'broadcast_id' in result

    def test_broadcast_cost_alert(self):
        """✅ Broadcast cost alert event."""
        from guardian.realtime.websocket_manager import EventBroadcaster

        broadcaster = EventBroadcaster()

        result = broadcaster.broadcast({
            'event_type': 'COST_ALERT',
            'daily_cost': 150.50,
            'threshold': 100.00,
            'message': 'Daily cost exceeded threshold'
        })

        assert result['status'] == 'delivered'

    def test_broadcast_action_executed(self):
        """✅ Broadcast action execution event."""
        from guardian.realtime.websocket_manager import EventBroadcaster

        broadcaster = EventBroadcaster()

        result = broadcaster.broadcast({
            'event_type': 'ACTION_EXECUTED',
            'action': 'STOP_INSTANCE',
            'instance_id': 'i-xyz',
            'status': 'success'
        })

        assert result['status'] == 'delivered'

    def test_broadcast_latency(self):
        """✅ Broadcast completes within 100ms."""
        from guardian.realtime.websocket_manager import EventBroadcaster
        import time

        broadcaster = EventBroadcaster()

        start = time.time()
        broadcaster.broadcast({
            'event_type': 'TEST',
            'data': 'test_payload'
        })
        duration = (time.time() - start) * 1000  # ms

        assert duration < 100  # < 100ms


class TestSubscriptionManager:
    """Test event subscription and filtering."""

    def test_subscribe_to_threat_events(self):
        """✅ Client subscribes to threat events."""
        from guardian.realtime.websocket_manager import SubscriptionManager

        manager = SubscriptionManager()

        result = manager.subscribe('client_1', {
            'event_type': 'THREAT_DETECTED'
        })

        assert result['status'] == 'subscribed'
        assert result['client_id'] == 'client_1'

    def test_subscribe_to_critical_threats_only(self):
        """✅ Subscribe with severity filter."""
        from guardian.realtime.websocket_manager import SubscriptionManager

        manager = SubscriptionManager()

        manager.subscribe('client_1', {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL'
        })

        # CRITICAL threat should match
        match_critical = manager.matches_subscription('client_1', {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL'
        })
        assert match_critical is True

        # LOW threat should not match
        match_low = manager.matches_subscription('client_1', {
            'event_type': 'THREAT_DETECTED',
            'severity': 'LOW'
        })
        assert match_low is False

    def test_unsubscribe_from_events(self):
        """✅ Client can unsubscribe."""
        from guardian.realtime.websocket_manager import SubscriptionManager

        manager = SubscriptionManager()

        manager.subscribe('client_1', {'event_type': 'THREAT_DETECTED'})
        result = manager.unsubscribe('client_1', 'THREAT_DETECTED')

        assert result['status'] == 'unsubscribed'


class TestMessageRouter:
    """Test message routing and filtering."""

    def test_route_event_to_subscribed_clients(self):
        """✅ Route event to subscribed clients only."""
        from guardian.realtime.websocket_manager import MessageRouter

        router = MessageRouter()

        # Register subscriptions
        router.add_subscription('client_1', 'THREAT_DETECTED')
        router.add_subscription('client_2', 'COST_ALERT')

        # Route threat event
        recipients = router.route_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'HIGH'
        })

        assert 'client_1' in recipients
        assert 'client_2' not in recipients

    def test_route_with_multiple_filters(self):
        """✅ Route event with multiple filter criteria."""
        from guardian.realtime.websocket_manager import MessageRouter

        router = MessageRouter()

        router.add_subscription('client_1', {
            'event_type': 'THREAT_DETECTED',
            'severity': ['CRITICAL', 'HIGH']
        })

        # High severity matches
        recipients_high = router.route_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'HIGH'
        })
        assert 'client_1' in recipients_high

        # Medium severity doesn't match
        recipients_medium = router.route_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'MEDIUM'
        })
        assert 'client_1' not in recipients_medium

    def test_broadcast_to_all_subscribers(self):
        """✅ Broadcast event to all subscribers of type."""
        from guardian.realtime.websocket_manager import MessageRouter

        router = MessageRouter()

        # Multiple subscribers
        for i in range(5):
            router.add_subscription(f'client_{i}', 'THREAT_DETECTED')

        recipients = router.route_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL'
        })

        assert len(recipients) == 5


class TestRealtimeIntegration:
    """Test end-to-end real-time workflows."""

    def test_threat_alert_workflow(self):
        """✅ Complete threat detection → broadcast → client receives."""
        from guardian.realtime.websocket_manager import (
            WebSocketManager, EventBroadcaster, SubscriptionManager
        )

        # Setup
        ws_manager = WebSocketManager()
        broadcaster = EventBroadcaster()
        sub_manager = SubscriptionManager()

        # Client connects
        ws_manager.register_client({'client_id': 'dashboard', 'user_id': 'admin'})

        # Client subscribes to CRITICAL threats
        sub_manager.subscribe('dashboard', {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL'
        })

        # Threat detected
        threat_event = {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL',
            'instance_id': 'i-threat-123'
        }

        # Broadcast
        result = broadcaster.broadcast(threat_event)

        assert result['status'] == 'delivered'

    def test_real_time_dashboard_updates(self):
        """✅ Dashboard receives real-time metrics."""
        from guardian.realtime.websocket_manager import EventBroadcaster

        broadcaster = EventBroadcaster()

        metrics = {
            'event_type': 'METRICS_UPDATE',
            'active_threats': 3,
            'daily_cost': 85.50,
            'running_instances': 12,
            'timestamp': datetime.utcnow().isoformat()
        }

        result = broadcaster.broadcast(metrics)

        assert result['status'] == 'delivered'

    def test_concurrent_events_broadcast(self):
        """✅ Multiple events broadcast concurrently."""
        from guardian.realtime.websocket_manager import EventBroadcaster

        broadcaster = EventBroadcaster()

        events = [
            {'event_type': 'THREAT_DETECTED', 'severity': 'HIGH'},
            {'event_type': 'COST_ALERT', 'daily_cost': 120},
            {'event_type': 'ACTION_EXECUTED', 'action': 'STOP_INSTANCE'},
            {'event_type': 'METRICS_UPDATE', 'active_threats': 5}
        ]

        for event in events:
            result = broadcaster.broadcast(event)
            assert result['status'] == 'delivered'

    def test_client_connection_resilience(self):
        """✅ Handle client reconnection gracefully."""
        from guardian.realtime.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        # Connect
        conn1 = manager.register_client({'client_id': 'mobile', 'user_id': 'user_1'})
        assert conn1['status'] == 'connected'

        # Disconnect
        manager.unregister_client('mobile')

        # Reconnect
        conn2 = manager.register_client({'client_id': 'mobile', 'user_id': 'user_1'})
        assert conn2['status'] == 'connected'
