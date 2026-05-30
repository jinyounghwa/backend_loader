"""Sprint 71 Phase 4: Mobile App with Dashboard, Notifications, Quick Actions (17 tests)"""

import pytest
from datetime import datetime


class TestNotificationService:
    """Test push notification delivery for mobile."""

    def test_send_push_notification(self):
        """✅ Send push notification to mobile device."""
        from guardian.mobile.notification_service import NotificationService

        service = NotificationService()

        result = service.send_notification({
            'device_token': 'device_token_abc123',
            'title': 'Security Alert',
            'message': 'Unauthorized EC2 instance detected',
            'severity': 'HIGH'
        })

        assert result['status'] == 'sent'
        assert result['notification_id']

    def test_send_batch_notifications(self):
        """✅ Send notifications to multiple devices."""
        from guardian.mobile.notification_service import NotificationService

        service = NotificationService()

        result = service.send_batch_notifications([
            {'device_token': 'token1', 'title': 'Alert 1'},
            {'device_token': 'token2', 'title': 'Alert 2'}
        ])

        assert result['delivered'] == 2
        assert result['status'] == 'completed'

    def test_notification_with_custom_action(self):
        """✅ Include custom action in notification."""
        from guardian.mobile.notification_service import NotificationService

        service = NotificationService()

        result = service.send_notification({
            'device_token': 'device_token_xyz',
            'title': 'Threat Detected',
            'actions': [
                {'action': 'STOP_INSTANCE', 'label': 'Stop Instance'},
                {'action': 'BLOCK_ACCESS', 'label': 'Block Access'}
            ]
        })

        assert result['status'] == 'sent'
        assert len(result['actions']) == 2


class TestMobileDashboardAPI:
    """Test mobile dashboard API endpoints."""

    def test_get_dashboard_summary(self):
        """✅ Get dashboard summary for mobile."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI

        api = MobileDashboardAPI()

        summary = api.get_summary()

        assert 'threats' in summary
        assert 'cost_today' in summary
        assert 'ec2_count' in summary
        assert 's3_count' in summary

    def test_get_threat_list(self):
        """✅ Get list of recent threats."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI

        api = MobileDashboardAPI()

        threats = api.get_threats(limit=10)

        assert isinstance(threats, list)
        assert len(threats) <= 10
        for threat in threats:
            assert 'id' in threat
            assert 'severity' in threat
            assert 'timestamp' in threat

    def test_get_cost_breakdown(self):
        """✅ Get cost breakdown by service."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI

        api = MobileDashboardAPI()

        costs = api.get_cost_breakdown()

        assert 'total_today' in costs
        assert 'by_service' in costs
        assert isinstance(costs['by_service'], dict)

    def test_get_resource_status(self):
        """✅ Get current resource status."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI

        api = MobileDashboardAPI()

        status = api.get_resource_status()

        assert 'running_instances' in status
        assert 'public_buckets' in status
        assert 'security_groups' in status


class TestQuickActions:
    """Test quick action execution from mobile."""

    def test_stop_instance_quick_action(self):
        """✅ Execute stop instance from mobile."""
        from guardian.mobile.quick_actions import QuickActionExecutor

        executor = QuickActionExecutor()

        result = executor.execute_action({
            'action': 'STOP_INSTANCE',
            'instance_id': 'i-12345',
            'reason': 'User initiated from mobile'
        })

        assert result['status'] == 'completed'
        assert result['action'] == 'STOP_INSTANCE'

    def test_block_public_access_quick_action(self):
        """✅ Execute block public access from mobile."""
        from guardian.mobile.quick_actions import QuickActionExecutor

        executor = QuickActionExecutor()

        result = executor.execute_action({
            'action': 'BLOCK_PUBLIC_ACCESS',
            'bucket_id': 's3-bucket-123',
            'reason': 'Security policy'
        })

        assert result['status'] == 'completed'
        assert result['action'] == 'BLOCK_PUBLIC_ACCESS'

    def test_enable_mfa_quick_action(self):
        """✅ Execute enable MFA from mobile."""
        from guardian.mobile.quick_actions import QuickActionExecutor

        executor = QuickActionExecutor()

        result = executor.execute_action({
            'action': 'ENABLE_MFA',
            'user_id': 'user-123',
            'device_token': 'device_abc'
        })

        assert result['status'] == 'completed'

    def test_quick_action_with_confirmation(self):
        """✅ Quick action with two-step confirmation."""
        from guardian.mobile.quick_actions import QuickActionExecutor

        executor = QuickActionExecutor()

        # First step: initiate
        confirmation = executor.initiate_action({
            'action': 'DELETE_ROLE',
            'role_id': 'role-xyz'
        })

        assert confirmation['confirmation_id']
        assert confirmation['status'] == 'pending_confirmation'

        # Second step: confirm
        result = executor.confirm_action(confirmation['confirmation_id'])

        assert result['status'] == 'completed'


class TestMobileAuthentication:
    """Test mobile device authentication."""

    def test_register_mobile_device(self):
        """✅ Register new mobile device."""
        from guardian.mobile.authentication import DeviceAuthenticator

        auth = DeviceAuthenticator()

        result = auth.register_device({
            'device_token': 'device_token_new',
            'device_name': 'iPhone 14 Pro',
            'device_type': 'iOS'
        })

        assert result['device_id']
        assert result['status'] == 'registered'
        assert result['is_trusted'] is False

    def test_verify_device_biometric(self):
        """✅ Verify device with biometric authentication."""
        from guardian.mobile.authentication import DeviceAuthenticator

        auth = DeviceAuthenticator()

        result = auth.verify_device({
            'device_id': 'device_12345',
            'biometric_type': 'FACE_ID'
        })

        assert result['authenticated'] is True

    def test_revoke_device_access(self):
        """✅ Revoke access for compromised device."""
        from guardian.mobile.authentication import DeviceAuthenticator

        auth = DeviceAuthenticator()

        result = auth.revoke_device('device_12345')

        assert result['status'] == 'revoked'
        assert result['device_id'] == 'device_12345'


class TestMobileAppIntegration:
    """Test full mobile app workflows."""

    def test_complete_threat_response_flow(self):
        """✅ Complete threat detection → notification → action flow."""
        from guardian.mobile.notification_service import NotificationService
        from guardian.mobile.quick_actions import QuickActionExecutor

        service = NotificationService()
        executor = QuickActionExecutor()

        # Threat detected → notify
        notification = service.send_notification({
            'device_token': 'device_token_1',
            'title': 'EC2 Threat',
            'severity': 'CRITICAL'
        })

        assert notification['status'] == 'sent'

        # User responds via quick action
        action_result = executor.execute_action({
            'action': 'STOP_INSTANCE',
            'instance_id': 'i-threat-123'
        })

        assert action_result['status'] == 'completed'

    def test_dashboard_load_performance(self):
        """✅ Dashboard loads within performance target."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI
        import time

        api = MobileDashboardAPI()

        start = time.time()
        api.get_summary()
        duration = time.time() - start

        # Should load in < 2 seconds
        assert duration < 2.0

    def test_offline_cache_mode(self):
        """✅ App works in offline cache mode."""
        from guardian.mobile.dashboard_api import MobileDashboardAPI

        api = MobileDashboardAPI()
        api.enable_offline_mode()

        summary = api.get_summary()

        assert 'threats' in summary
        assert api.is_cached is True

    def test_sync_local_changes_when_online(self):
        """✅ Sync local changes when device comes online."""
        from guardian.mobile.sync_manager import SyncManager

        manager = SyncManager()

        # Make local changes
        manager.record_local_action({
            'action': 'STOP_INSTANCE',
            'instance_id': 'i-123'
        })

        # Sync when online
        result = manager.sync()

        assert result['status'] == 'synced'
        assert result['actions_synced'] >= 1
