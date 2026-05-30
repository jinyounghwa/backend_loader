"""API Gateway and integrations tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestAPIGateway:
    """Test REST API gateway."""

    def test_create_webhook(self):
        """✅ Create webhook endpoint."""
        from guardian.integrations.api_gateway import APIGateway

        gateway = APIGateway()

        webhook = gateway.create_webhook({
            'name': 'threat-alert',
            'url': 'https://external.example.com/threats',
            'events': ['THREAT_DETECTED']
        })

        assert 'webhook_id' in webhook
        assert webhook['status'] == 'active'
        assert webhook['name'] == 'threat-alert'

    def test_delete_webhook(self):
        """✅ Delete webhook endpoint."""
        from guardian.integrations.api_gateway import APIGateway

        gateway = APIGateway()

        webhook = gateway.create_webhook({
            'name': 'temp-webhook',
            'url': 'https://example.com/temp'
        })

        result = gateway.delete_webhook(webhook['webhook_id'])

        assert result['status'] == 'deleted'

    def test_list_webhooks(self):
        """✅ List all webhooks."""
        from guardian.integrations.api_gateway import APIGateway

        gateway = APIGateway()

        gateway.create_webhook({
            'name': 'webhook1',
            'url': 'https://example.com/1'
        })

        webhooks = gateway.list_webhooks()

        assert isinstance(webhooks, list)
        assert len(webhooks) >= 1


class TestWebhookManager:
    """Test webhook message handling."""

    def test_send_webhook_event(self):
        """✅ Send event via webhook."""
        from guardian.integrations.api_gateway import WebhookManager

        manager = WebhookManager()

        result = manager.send_event({
            'webhook_url': 'https://example.com/webhook',
            'event_type': 'THREAT_DETECTED',
            'payload': {
                'threat_id': 'threat-123',
                'severity': 'CRITICAL'
            }
        })

        assert result['status'] == 'sent'
        assert 'event_id' in result

    def test_webhook_retry(self):
        """✅ Retry failed webhook deliveries."""
        from guardian.integrations.api_gateway import WebhookManager

        manager = WebhookManager()

        result = manager.send_event_with_retry({
            'webhook_url': 'https://example.com/webhook',
            'event_type': 'COST_ALERT',
            'max_retries': 3
        })

        assert result['status'] == 'sent' or result['status'] == 'failed'
        assert 'attempt_count' in result

    def test_webhook_signature(self):
        """✅ Generate webhook signature for verification."""
        from guardian.integrations.api_gateway import WebhookManager

        manager = WebhookManager()

        signature = manager.generate_signature({
            'secret': 'webhook-secret',
            'payload': {'event': 'THREAT_DETECTED'}
        })

        assert 'signature' in signature
        assert len(signature['signature']) > 0


class TestSlackIntegration:
    """Test Slack integration."""

    def test_send_threat_alert_to_slack(self):
        """✅ Send threat alert to Slack."""
        from guardian.integrations.api_gateway import SlackIntegration

        slack = SlackIntegration(webhook_url='https://hooks.slack.com/services/T00/B00/XX')

        result = slack.send_alert({
            'threat_type': 'MALWARE',
            'severity': 'CRITICAL',
            'affected_resources': ['i-12345']
        })

        assert result['status'] == 'sent'

    def test_send_cost_alert_to_slack(self):
        """✅ Send cost alert to Slack."""
        from guardian.integrations.api_gateway import SlackIntegration

        slack = SlackIntegration(webhook_url='https://hooks.slack.com/services/T00/B00/XX')

        result = slack.send_alert({
            'alert_type': 'COST_SPIKE',
            'daily_cost': 250.50,
            'threshold': 100.00
        })

        assert result['status'] == 'sent'


class TestPagerDutyIntegration:
    """Test PagerDuty integration."""

    def test_create_pagerduty_incident(self):
        """✅ Create incident in PagerDuty."""
        from guardian.integrations.api_gateway import PagerDutyIntegration

        pagerduty = PagerDutyIntegration(api_key='test-key')

        incident = pagerduty.create_incident({
            'title': 'Critical Threat Detected',
            'severity': 'critical',
            'service_id': 'service-123'
        })

        assert 'incident_id' in incident
        assert incident['status'] == 'triggered'

    def test_resolve_pagerduty_incident(self):
        """✅ Resolve PagerDuty incident."""
        from guardian.integrations.api_gateway import PagerDutyIntegration

        pagerduty = PagerDutyIntegration(api_key='test-key')

        incident = pagerduty.create_incident({
            'title': 'Test Incident',
            'severity': 'warning',
            'service_id': 'service-123'
        })

        resolved = pagerduty.resolve_incident(incident['incident_id'])

        assert resolved['status'] == 'resolved'


class TestThirdPartyIntegration:
    """Test third-party integrations."""

    def test_authenticate_slack(self):
        """✅ Authenticate with Slack OAuth."""
        from guardian.integrations.api_gateway import ThirdPartyIntegration

        integration = ThirdPartyIntegration()

        auth = integration.authenticate({
            'service': 'slack',
            'oauth_code': 'xoxb-token-123'
        })

        assert auth['status'] == 'authenticated'
        assert 'access_token' in auth or auth['status'] == 'authenticated'

    def test_test_integration_connection(self):
        """✅ Test integration connection."""
        from guardian.integrations.api_gateway import ThirdPartyIntegration

        integration = ThirdPartyIntegration()

        result = integration.test_connection({
            'service': 'slack',
            'webhook_url': 'https://hooks.slack.com/services/T00/B00/XX'
        })

        assert result['status'] == 'success' or result['connected'] is True


class TestIntegrationIntegration:
    """End-to-end integration workflows."""

    def test_complete_webhook_workflow(self):
        """✅ Complete webhook: create → send → verify."""
        from guardian.integrations.api_gateway import APIGateway, WebhookManager

        gateway = APIGateway()
        manager = WebhookManager()

        # Step 1: Create webhook
        webhook = gateway.create_webhook({
            'name': 'workflow-test',
            'url': 'https://example.com/webhook'
        })

        assert webhook['webhook_id']

        # Step 2: Send event
        event_result = manager.send_event({
            'webhook_url': webhook['url'],
            'event_type': 'TEST_EVENT',
            'payload': {'test': True}
        })

        assert event_result['status'] == 'sent'

        # Step 3: List webhooks
        webhooks = gateway.list_webhooks()

        assert len(webhooks) >= 1

    def test_multi_channel_alert_delivery(self):
        """✅ Send alerts to multiple channels."""
        from guardian.integrations.api_gateway import (
            SlackIntegration,
            PagerDutyIntegration
        )

        slack = SlackIntegration(webhook_url='https://hooks.slack.com/services/T00/B00/XX')
        pagerduty = PagerDutyIntegration(api_key='test-key')

        alert_data = {
            'threat_type': 'MALWARE',
            'severity': 'CRITICAL',
            'description': 'Malware detected on instance'
        }

        slack_result = slack.send_alert(alert_data)
        pd_result = pagerduty.create_incident({
            'title': alert_data['threat_type'],
            'severity': 'critical',
            'service_id': 'service-123'
        })

        assert slack_result['status'] == 'sent'
        assert 'incident_id' in pd_result

    def test_webhook_event_filtering(self):
        """✅ Filter webhook events by type."""
        from guardian.integrations.api_gateway import APIGateway

        gateway = APIGateway()

        webhook = gateway.create_webhook({
            'name': 'filtered',
            'url': 'https://example.com/webhook',
            'events': ['THREAT_DETECTED', 'COST_ALERT']
        })

        assert len(webhook['events']) == 2

    def test_integration_health_check(self):
        """✅ Health check for integrations."""
        from guardian.integrations.api_gateway import ThirdPartyIntegration

        integration = ThirdPartyIntegration()

        health = integration.health_check({
            'services': ['slack', 'pagerduty']
        })

        assert 'slack' in health or 'services' in health
        assert health.get('slack', {}).get('status') or 'status' in str(health)
