"""Sprint 33 Phase 3: Alert Generation Tests

Tests for converting threats to alerts and sending notifications.
Covers AlertHandler, AlertHistory, and notification formatting.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.alert_handler import AlertHandler, AlertFormatter
from storage.alert_history import AlertHistory, AlertHistoryRepository
from detectors.anomaly_detector import Threat


class MockThreat:
    """Mock Threat for testing"""

    def __init__(
        self,
        threat_id: str,
        rule_id: str,
        severity: int,
        account_id: str,
        message: str,
    ):
        self.threat_id = threat_id
        self.rule_id = rule_id
        self.severity = severity
        self.account_id = account_id
        self.timestamp = datetime.utcnow()
        self.message = message
        self.evidence = [{"event": "test-event-1"}, {"event": "test-event-2"}]


class TestAlertHandler:
    """Test AlertHandler threat-to-alert conversion"""

    @pytest.fixture
    def mock_responders(self):
        """Mock Telegram and Discord responders"""
        telegram = AsyncMock()
        discord = AsyncMock()
        return telegram, discord

    @pytest.fixture
    def mock_buffer(self):
        """Mock NotificationBuffer"""
        buffer = AsyncMock()
        buffer.add = AsyncMock()
        buffer.flush = AsyncMock(return_value=[])
        return buffer

    @pytest.fixture
    def handler(self, mock_responders, mock_buffer):
        """Create AlertHandler with mocks"""
        telegram, discord = mock_responders
        return AlertHandler(telegram, discord, mock_buffer)

    def test_threat_to_alert_critical(self, handler):
        """Test converting critical threat to alert"""
        threat = MockThreat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=10,
            account_id="123456789",
            message="Critical security issue detected",
        )

        alert = handler._threat_to_alert(threat)

        assert alert["alert_id"] == "threat-1"
        assert alert["rule_id"] == "rule-1"
        assert alert["severity"] == 10
        assert alert["account_id"] == "123456789"
        assert "🚨" in alert["title"]  # Critical emoji

    def test_threat_to_alert_low(self, handler):
        """Test converting low-severity threat to alert"""
        threat = MockThreat(
            threat_id="threat-2",
            rule_id="rule-2",
            severity=2,
            account_id="123456789",
            message="Low priority event",
        )

        alert = handler._threat_to_alert(threat)

        assert alert["severity"] == 2
        assert "ℹ️" in alert["title"]  # Info emoji

    def test_process_threats(self, handler, mock_buffer):
        """Test processing multiple threats"""

        async def run_test():
            threats = [
                MockThreat("t1", "r1", 9, "acc1", "Threat 1"),
                MockThreat("t2", "r2", 7, "acc1", "Threat 2"),
                MockThreat("t3", "r3", 5, "acc2", "Threat 3"),
            ]

            count = await handler.process_threats(threats)

            assert count == 3
            assert mock_buffer.add.call_count == 3

        asyncio.run(run_test())

    def test_flush_alerts_success(self, handler, mock_responders, mock_buffer):
        """Test flushing alerts successfully"""
        async def run_test():
            telegram, discord = mock_responders
            telegram.send_alert = AsyncMock(return_value=True)
            discord.send_alert = AsyncMock(return_value=True)

            test_alerts = [
                {
                    "alert_id": "alert-1",
                    "rule_id": "rule-1",
                    "severity": 9,
                    "account_id": "123456789",
                    "timestamp": datetime.utcnow().isoformat(),
                    "title": "🚨 Alert",
                    "message": "Test alert",
                    "evidence_count": 2,
                    "evidence": [],
                }
            ]

            mock_buffer.flush = AsyncMock(return_value=test_alerts)

            count = await handler.flush_alerts()

            assert count == 1
            telegram.send_alert.assert_called_once()
            discord.send_alert.assert_called_once()

        asyncio.run(run_test())

    def test_severity_emoji_mapping(self, handler):
        """Test emoji assignment based on severity"""
        assert "🚨" in handler._get_severity_emoji(10)
        assert "🚨" in handler._get_severity_emoji(9)
        assert "⚠️" in handler._get_severity_emoji(7)
        assert "⚡" in handler._get_severity_emoji(5)
        assert "ℹ️" in handler._get_severity_emoji(1)


class TestAlertFormatter:
    """Test alert formatting for Telegram and Discord"""

    def test_format_telegram_message(self):
        """Test Telegram message formatting"""
        alert = {
            "title": "🚨 Alert Title",
            "rule_id": "rule-1",
            "severity": 9,
            "account_id": "123456789",
            "message": "Test message",
            "evidence_count": 2,
        }

        message = AlertFormatter.format_telegram_message(alert)

        assert "rule-1" in message
        assert "9" in message
        assert "123456789" in message
        assert "Test message" in message

    def test_format_discord_embed(self):
        """Test Discord embed formatting"""
        alert = {
            "title": "🚨 Alert Title",
            "message": "Test message",
            "color": "#FF0000",
            "rule_id": "rule-1",
            "severity": 9,
            "account_id": "123456789",
            "evidence_count": 2,
            "timestamp": "2026-05-23T10:00:00",
        }

        embed = AlertFormatter.format_discord_embed(alert)

        assert embed["title"] == "🚨 Alert Title"
        assert embed["description"] == "Test message"
        assert isinstance(embed["color"], int)
        assert len(embed["fields"]) == 4


class TestAlertHistory:
    """Test AlertHistory storage"""

    def test_alert_history_model(self):
        """Test AlertHistory data model"""
        history = AlertHistory(
            alert_id="alert-1",
            rule_id="rule-1",
            severity=9,
            account_id="123456789",
            timestamp="2026-05-23T10:00:00",
            message="Test alert",
            status="sent",
        )

        assert history.alert_id == "alert-1"
        assert history.severity == 9
        assert history.status == "sent"

    def test_alert_history_to_dynamodb(self):
        """Test converting AlertHistory to DynamoDB format"""
        history = AlertHistory(
            alert_id="alert-1",
            rule_id="rule-1",
            severity=9,
            account_id="123456789",
            timestamp="2026-05-23T10:00:00",
            message="Test alert",
        )

        item = history.to_dynamodb_item()

        assert item["alert_id"] == "alert-1"
        assert item["severity"] == 9
        assert "created_at" in item

    @pytest.fixture
    def mock_history_table(self):
        """Mock DynamoDB table for alert history"""
        return MagicMock()

    @pytest.fixture
    def history_repo(self, mock_history_table):
        """Create AlertHistoryRepository with mock"""
        with patch("guardian.storage.alert_history.boto3.resource") as mock_boto3:
            mock_boto3.return_value.Table.return_value = mock_history_table
            repo = AlertHistoryRepository("test-table")
            repo.table = mock_history_table
            return repo

    def test_save_alert(self, history_repo, mock_history_table):
        """Test saving alert to history"""
        history = AlertHistory(
            alert_id="alert-1",
            rule_id="rule-1",
            severity=9,
            account_id="123456789",
            timestamp="2026-05-23T10:00:00",
            message="Test alert",
        )

        success = history_repo.save_alert(history)

        assert success is True
        mock_history_table.put_item.assert_called_once()

    def test_list_alerts_by_account(self, history_repo, mock_history_table):
        """Test listing alerts by account"""
        mock_history_table.query.return_value = {
            "Items": [
                {
                    "alert_id": "alert-1",
                    "rule_id": "rule-1",
                    "severity": 9,
                    "account_id": "123456789",
                    "timestamp": "2026-05-23T10:00:00",
                    "message": "Alert 1",
                    "status": "sent",
                    "created_at": "2026-05-23T10:00:00",
                },
                {
                    "alert_id": "alert-2",
                    "rule_id": "rule-2",
                    "severity": 7,
                    "account_id": "123456789",
                    "timestamp": "2026-05-23T10:01:00",
                    "message": "Alert 2",
                    "status": "sent",
                    "created_at": "2026-05-23T10:01:00",
                },
            ]
        }

        alerts = history_repo.list_alerts_by_account("123456789")

        assert len(alerts) == 2
        assert alerts[0].alert_id == "alert-1"
        assert alerts[1].severity == 7
