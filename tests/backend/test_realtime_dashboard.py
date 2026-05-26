"""Sprint 57 Phase 1: Real-time Dashboard Tests (8 backend tests)"""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.websocket.event_broadcaster import WebSocketEventBroadcaster
from guardian.services.realtime_dashboard_service import RealtimeDashboardService
from guardian.websocket.connection_manager import DashboardConnectionManager
from guardian.websocket.stream_manager import DashboardStreamManager


class TestWebSocketEventBroadcaster:
    """WebSocket event broadcasting tests."""

    def test_broadcast_threat_detected(self):
        """✅ Broadcast new threat detection."""
        broadcaster = WebSocketEventBroadcaster()

        # Register client
        broadcaster.register_client_connection('conn-001')

        threat = {
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
            'affected_resources': [{'resource_id': 'i-12345'}]
        }

        message = broadcaster.broadcast_threat_detected(threat)

        assert message['event_type'] == 'threat_detected'
        assert message['threat_id'] == 'threat-001'
        assert message['severity'] == 8

    def test_broadcast_remediation_progress(self):
        """✅ Broadcast real-time remediation progress."""
        broadcaster = WebSocketEventBroadcaster()
        broadcaster.register_client_connection('conn-001')

        resources_status = {
            'total': 3,
            'completed': 1,
            'failed': 0,
            'pending': 2,
            'current_action': 'Isolating network'
        }

        message = broadcaster.broadcast_remediation_progress(
            'exec-001',
            45,
            resources_status
        )

        assert message['event_type'] == 'remediation_progress'
        assert message['progress_percent'] == 45
        assert message['resources_status']['current_action'] == 'Isolating network'

    def test_register_client_connection(self):
        """✅ Register WebSocket client."""
        broadcaster = WebSocketEventBroadcaster()

        connection = broadcaster.register_client_connection('conn-001', {'severity_min': 5})

        assert connection['connection_id'] == 'conn-001'
        assert connection['filters']['severity_min'] == 5
        assert 'connected_at' in connection


class TestRealtimeDashboardService:
    """Real-time dashboard service tests."""

    def test_get_initial_dashboard_state(self):
        """✅ Get full state for new connection."""
        service = RealtimeDashboardService()

        state = service.get_initial_dashboard_state(account_id='acc-123')

        assert state['account_id'] == 'acc-123'
        assert 'threats' in state
        assert 'metrics' in state
        assert 'compliance' in state
        assert state['metrics']['total_threats'] == 0

    def test_stream_threat_updates(self):
        """✅ Stream specific threat updates."""
        service = RealtimeDashboardService()

        stream = service.stream_threat_updates('threat-001')

        assert len(stream) > 0
        assert stream[0]['threat_id'] == 'threat-001'
        assert 'events' in stream[0]

    def test_get_dashboard_diff(self):
        """✅ Calculate incremental diff for efficiency."""
        service = RealtimeDashboardService()

        last_state = {
            'threats': [
                {'threat_id': 'threat-001', 'severity': 7},
                {'threat_id': 'threat-002', 'severity': 8}
            ],
            'metrics': {'total_threats': 2}
        }

        current_state = {
            'threats': [
                {'threat_id': 'threat-001', 'severity': 7},
                {'threat_id': 'threat-003', 'severity': 9}
            ],
            'metrics': {'total_threats': 2}
        }

        diff = service.get_dashboard_diff(last_state, current_state)

        assert 'changes' in diff
        # Should detect threat-003 added and threat-002 removed
        assert len(diff['changes']) >= 2


class TestConnectionManager:
    """Connection management tests."""

    def test_register_and_unregister_connection(self):
        """✅ Manage connection lifecycle."""
        manager = DashboardConnectionManager()

        # Register
        connection = manager.register_connection('conn-001', 'user-123', 'acc-456')
        assert connection['connection_id'] == 'conn-001'
        assert connection['user_id'] == 'user-123'

        # Unregister
        success = manager.unregister_connection('conn-001')
        assert success is True

        # Verify removed
        assert manager.get_connection_info('conn-001') is None

    def test_subscription_management(self):
        """✅ Subscribe/unsubscribe from threats."""
        manager = DashboardConnectionManager()
        manager.register_connection('conn-001', 'user-123')

        # Subscribe to threat
        success = manager.subscribe_to_threat('conn-001', 'threat-001')
        assert success is True

        # Verify subscription
        subscriptions = manager.get_subscriptions('conn-001')
        assert 'threat-001' in subscriptions

        # Unsubscribe
        success = manager.unsubscribe_from_threat('conn-001', 'threat-001')
        assert success is True

        # Verify removed
        subscriptions = manager.get_subscriptions('conn-001')
        assert 'threat-001' not in subscriptions
