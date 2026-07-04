"""Sprint 43 Phase 3: Slack/Teams Multi-Channel Integration"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.responders.slack_responder import SlackResponder
from guardian.responders.teams_responder import TeamsResponder
from guardian.responders.notification_orchestrator import NotificationOrchestrator


# ==========================================
# Test Group 1: Slack Message Format (3 tests)
# ==========================================

def test_slack_responder_initialization():
    """Test Slack responder initialization"""
    slack_client = MagicMock()

    responder = SlackResponder(slack_client)

    assert responder is not None
    assert responder.client is not None


def test_create_slack_alert_block():
    """Test creating Slack alert block (message block format)"""
    slack_client = MagicMock()

    responder = SlackResponder(slack_client)

    threat = {
        'threatType': 'unauthorized_deletion',
        'severity': 9,
        'principal': 'arn:aws:iam::123456789012:user/testuser',
        'resource': 'arn:aws:s3:::my-bucket',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    block = responder.create_alert_block(threat)

    assert block is not None
    assert isinstance(block, dict)


def test_send_alert_to_slack():
    """Test sending alert to Slack channel"""
    slack_client = MagicMock()
    slack_client.chat_postMessage.return_value = {'ok': True, 'ts': '1234567890.123456'}

    responder = SlackResponder(slack_client)

    alert = {
        'alert_id': 'alert-001',
        'severity': 'high',
        'message': 'Suspicious API call detected',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = responder.send_alert(alert, channel='#security-alerts')

    assert result is not None
    assert isinstance(result, dict)


# ==========================================
# Test Group 2: Teams Adaptive Card (3 tests)
# ==========================================

def test_teams_responder_initialization():
    """Test Teams responder initialization"""
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    responder = TeamsResponder(teams_webhook)

    assert responder is not None
    assert responder.webhook_url == teams_webhook


def test_create_teams_adaptive_card():
    """Test creating Teams adaptive card"""
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    responder = TeamsResponder(teams_webhook)

    threat = {
        'threatType': 'unauthorized_deletion',
        'severity': 9,
        'principal': 'arn:aws:iam::123456789012:user/testuser',
        'resource': 'arn:aws:s3:::my-bucket',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    card = responder.create_adaptive_card(threat)

    assert card is not None
    assert isinstance(card, dict)


def test_send_alert_to_teams():
    """Test sending alert to Teams webhook"""
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    responder = TeamsResponder(teams_webhook)

    alert = {
        'alert_id': 'alert-001',
        'severity': 'high',
        'message': 'Suspicious API call detected',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = responder.send_alert(alert)

    assert result is not None
    assert isinstance(result, dict)


# ==========================================
# Test Group 3: Interactive Buttons/Actions (2 tests)
# ==========================================

def test_slack_add_action_buttons():
    """Test adding action buttons to Slack message"""
    slack_client = MagicMock()

    responder = SlackResponder(slack_client)

    message = {
        'text': 'Alert message',
        'blocks': []
    }

    actions = [
        {'label': 'Investigate', 'action_id': 'investigate'},
        {'label': 'Remediate', 'action_id': 'remediate'},
        {'label': 'Dismiss', 'action_id': 'dismiss'}
    ]

    result = responder.add_buttons(message, actions)

    assert result is not None
    assert isinstance(result, dict)


def test_teams_add_action_buttons():
    """Test adding action buttons to Teams adaptive card"""
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    responder = TeamsResponder(teams_webhook)

    card = {
        'type': 'message',
        'attachments': []
    }

    actions = [
        {'label': 'Investigate', 'action_id': 'investigate'},
        {'label': 'Remediate', 'action_id': 'remediate'}
    ]

    result = responder.add_action_buttons(card, actions)

    assert result is not None
    assert isinstance(result, dict)


# ==========================================
# Test Group 4: Multi-Channel Deployment (2 tests)
# ==========================================

def test_notification_orchestrator_initialization():
    """Test notification orchestrator initialization"""
    slack_client = MagicMock()
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    orchestrator = NotificationOrchestrator(slack_client, teams_webhook)

    assert orchestrator is not None
    assert orchestrator.slack is not None
    assert orchestrator.teams is not None


def test_send_to_all_channels():
    """Test sending alert to all configured channels"""
    slack_client = MagicMock()
    slack_client.chat_postMessage.return_value = {'ok': True}

    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    orchestrator = NotificationOrchestrator(slack_client, teams_webhook)

    alert = {
        'alert_id': 'alert-001',
        'severity': 'high',
        'message': 'Suspicious API call detected',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = orchestrator.send_to_all_channels(alert)

    assert result is not None
    assert isinstance(result, dict)


def test_notification_throttling():
    """Test notification throttling to prevent spam"""
    slack_client = MagicMock()
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    orchestrator = NotificationOrchestrator(slack_client, teams_webhook)

    # Send multiple alerts rapidly
    alerts = [
        {'alert_id': f'alert-{i}', 'severity': 'high', 'message': f'Alert {i}'}
        for i in range(5)
    ]

    throttled = orchestrator.throttle_notifications(alerts)

    assert throttled is not None
    assert isinstance(throttled, list)
    assert len(throttled) <= len(alerts)


def test_notification_delivery_tracking():
    """Test tracking notification delivery status"""
    slack_client = MagicMock()
    teams_webhook = 'https://outlook.webhook.office.com/webhookb2/xxx'

    orchestrator = NotificationOrchestrator(slack_client, teams_webhook)

    notification = {
        'alert_id': 'alert-001',
        'slack_status': 'sent',
        'teams_status': 'sent',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    delivery_status = orchestrator.track_notification_delivery(notification)

    assert delivery_status is not None
    assert isinstance(delivery_status, dict)
