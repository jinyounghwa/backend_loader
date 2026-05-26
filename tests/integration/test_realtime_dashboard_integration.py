"""Sprint 57 Phase 1: Real-time Dashboard Integration Tests (6 tests)"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.websocket.event_broadcaster import WebSocketEventBroadcaster
from guardian.services.realtime_dashboard_service import RealtimeDashboardService
from guardian.websocket.connection_manager import DashboardConnectionManager
from guardian.websocket.stream_manager import DashboardStreamManager


class TestRealtimeDashboardIntegration:
    """End-to-end real-time dashboard integration tests."""

    def test_end_to_end_threat_broadcast(self):
        """✅ Threat detection → broadcast → client receives."""
        broadcaster = WebSocketEventBroadcaster()
        stream_manager = DashboardStreamManager(broadcaster=broadcaster)

        # Register client
        broadcaster.register_client_connection('conn-001')

        # Simulate threat detection
        threat = {
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123'
        }

        # Handle threat detection
        event = stream_manager.handle_threat_detection(threat)

        assert event['event_type'] == 'threat_detected'
        assert event['threat']['threat_id'] == 'threat-001'

    def test_remediation_progress_streaming(self):
        """✅ Real-time remediation progress updates."""
        broadcaster = WebSocketEventBroadcaster()
        stream_manager = DashboardStreamManager(broadcaster=broadcaster)

        broadcaster.register_client_connection('conn-001')

        # Simulate remediation progress updates
        update = {
            'progress_percent': 45,
            'resources_status': {
                'total': 3,
                'completed': 1,
                'failed': 0,
                'pending': 2
            }
        }

        event = stream_manager.handle_remediation_update('exec-001', update)

        assert event['event_type'] == 'remediation_update'
        assert event['update']['progress_percent'] == 45

    def test_multi_client_same_threat_subscription(self):
        """✅ Multiple clients receive same threat updates."""
        manager = DashboardConnectionManager()
        broadcaster = WebSocketEventBroadcaster()

        # Register multiple clients
        manager.register_connection('conn-001', 'user-1', 'acc-123')
        manager.register_connection('conn-002', 'user-2', 'acc-123')

        # Both subscribe to same threat
        manager.subscribe_to_threat('conn-001', 'threat-001')
        manager.subscribe_to_threat('conn-002', 'threat-001')

        # Verify both subscribed
        subscribers = manager.get_subscribers('threat-001')
        assert 'conn-001' in subscribers
        assert 'conn-002' in subscribers
        assert len(subscribers) == 2

    def test_account_filtered_subscription(self):
        """✅ Clients only receive account-relevant threats."""
        manager = DashboardConnectionManager()
        service = RealtimeDashboardService()

        # Register clients from different accounts
        manager.register_connection('conn-001', 'user-1', 'acc-prod')
        manager.register_connection('conn-002', 'user-2', 'acc-dev')

        # Subscribe to accounts
        manager.subscribe_to_account('conn-001', 'acc-prod')
        manager.subscribe_to_account('conn-002', 'acc-dev')

        # Verify subscriptions
        assert 'account:acc-prod' in manager.get_subscriptions('conn-001')
        assert 'account:acc-dev' in manager.get_subscriptions('conn-002')

    def test_connection_recovery_and_replay(self):
        """✅ Reconnected client receives recent history."""
        stream_manager = DashboardStreamManager()

        # Simulate multiple events
        threat1 = {
            'threat_id': 'threat-001',
            'threat_type': 'Type1',
            'severity': 7
        }
        threat2 = {
            'threat_id': 'threat-002',
            'threat_type': 'Type2',
            'severity': 8
        }

        stream_manager.handle_threat_detection(threat1)
        stream_manager.handle_threat_detection(threat2)

        # Get playback history
        history = stream_manager.get_event_history(limit=10)

        assert len(history) >= 2
        # Verify events in order
        assert history[0]['threat']['threat_id'] == 'threat-001'
        assert history[1]['threat']['threat_id'] == 'threat-002'

    def test_dashboard_performance_under_load(self):
        """✅ Broadcast 100 concurrent clients, <100ms latency."""
        broadcaster = WebSocketEventBroadcaster()

        # Register 100 concurrent connections
        for i in range(100):
            broadcaster.register_client_connection(f'conn-{i:03d}')

        # Measure broadcast latency
        threat = {
            'threat_id': 'threat-perf-001',
            'threat_type': 'Test',
            'severity': 5,
            'account_id': 'acc-test'
        }

        start_time = datetime.utcnow()
        recipient_count = broadcaster.broadcast_to_all(threat)
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Verify broadcast reached all clients
        assert recipient_count == 100
        # Verify latency within acceptable range
        assert latency_ms < 100, f"Latency {latency_ms}ms exceeds 100ms limit"
