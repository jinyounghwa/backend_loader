"""Sprint 34 Phase 3: Alert Generation Tests

Tests for threat-to-alert conversion, batching, and notification sending.
Covers AlertHandler, AlertFormatter, and integration with responders.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.alert_handler import AlertHandler, AlertFormatter
from detectors.anomaly_detector import Threat


class TestAlertFormatter:
    """Test AlertFormatter utility class"""

    def test_format_telegram_message(self):
        """Test formatting alert for Telegram"""
        alert = {
            "title": "🚨 [acc-1] High severity threat",
            "rule_id": "rule-1",
            "severity": 8,
            "account_id": "acc-1",
            "evidence_count": 5,
            "message": "Connection spike detected",
        }

        message = AlertFormatter.format_telegram_message(alert)

        assert "🚨" in message
        assert "rule-1" in message
        assert "8/10" in message
        assert "acc-1" in message
        assert "Connection spike detected" in message

    def test_format_discord_embed(self):
        """Test formatting alert as Discord embed"""
        alert = {
            "title": "⚠️ [acc-1] Medium severity threat",
            "rule_id": "rule-2",
            "severity": 6,
            "account_id": "acc-1",
            "evidence_count": 3,
            "message": "Auth failures detected",
            "color": "#FFFF00",
            "timestamp": datetime.utcnow().isoformat(),
        }

        embed = AlertFormatter.format_discord_embed(alert)

        assert embed["title"] == alert["title"]
        assert embed["description"] == "Auth failures detected"
        assert embed["color"] == 16776960  # #FFFF00 as decimal
        assert any(f["name"] == "Rule ID" for f in embed["fields"])
        assert any(f["name"] == "Severity" for f in embed["fields"])


class TestAlertHandler:
    """Test AlertHandler class"""

    @pytest.fixture
    def mock_telegram(self):
        """Mock Telegram responder"""
        return MagicMock()

    @pytest.fixture
    def mock_discord(self):
        """Mock Discord responder"""
        return MagicMock()

    @pytest.fixture
    def mock_buffer(self):
        """Mock notification buffer"""
        return MagicMock()

    @pytest.fixture
    def alert_handler(self, mock_telegram, mock_discord, mock_buffer):
        """Create alert handler with mocks"""
        return AlertHandler(mock_telegram, mock_discord, mock_buffer)

    def test_threat_to_alert_conversion(self, alert_handler):
        """Test converting threat to alert format"""
        threat = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=8,
            account_id="acc-1",
            timestamp=datetime.utcnow(),
            message="Connection spike detected: 15 connections",
            evidence=[{"event": "connect"}, {"event": "connect"}],
        )

        alert = alert_handler._threat_to_alert(threat)

        assert alert["alert_id"] == "threat-1"
        assert alert["rule_id"] == "rule-1"
        assert alert["severity"] == 8
        assert alert["account_id"] == "acc-1"
        assert "Connection spike detected" in alert["title"]
        assert alert["evidence_count"] == 2

    def test_severity_emoji_assignment(self, alert_handler):
        """Test severity-based emoji assignment"""
        threat_critical = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=9,
            account_id="acc-1",
            timestamp=datetime.utcnow(),
            message="Critical threat",
            evidence=[],
        )

        alert = alert_handler._threat_to_alert(threat_critical)
        assert "🚨" in alert["title"]

    def test_severity_color_assignment(self, alert_handler):
        """Test severity-based color assignment"""
        threat_high = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=7,
            account_id="acc-1",
            timestamp=datetime.utcnow(),
            message="High severity threat",
            evidence=[],
        )

        alert = alert_handler._threat_to_alert(threat_high)
        assert alert["color"] == "#FF6600"

    def test_threat_to_alert_evidence_limit(self, alert_handler):
        """Test that alert evidence is limited to 3 items"""
        threat = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=5,
            account_id="acc-1",
            timestamp=datetime.utcnow(),
            message="Test threat",
            evidence=[{"id": i} for i in range(10)],
        )

        alert = alert_handler._threat_to_alert(threat)

        assert len(alert["evidence"]) == 3
        assert alert["evidence_count"] == 10

    def test_alert_contains_required_fields(self, alert_handler):
        """Test that alert contains all required fields"""
        threat = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=5,
            account_id="acc-1",
            timestamp=datetime.utcnow(),
            message="Test message",
            evidence=[],
        )

        alert = alert_handler._threat_to_alert(threat)

        required_fields = ["alert_id", "rule_id", "severity", "account_id", 
                          "timestamp", "title", "message", "color", "evidence_count", "evidence"]
        for field in required_fields:
            assert field in alert


class TestSeverityLevels:
    """Test threat severity classification"""

    @pytest.fixture
    def alert_handler(self):
        """Create alert handler"""
        mock_telegram = MagicMock()
        mock_discord = MagicMock()
        mock_buffer = MagicMock()
        return AlertHandler(mock_telegram, mock_discord, mock_buffer)

    @pytest.mark.parametrize("severity,expected_emoji", [
        (10, "🚨"),
        (9, "🚨"),
        (8, "⚠️"),
        (7, "⚠️"),
        (6, "⚡"),
        (5, "⚡"),
        (2, "ℹ️"),
        (1, "ℹ️"),
    ])
    def test_severity_emoji_levels(self, alert_handler, severity, expected_emoji):
        """Test emoji assignment for different severity levels"""
        emoji = alert_handler._get_severity_emoji(severity)
        assert emoji == expected_emoji

    @pytest.mark.parametrize("severity,expected_color", [
        (10, "#FF0000"),
        (9, "#FF0000"),
        (8, "#FF6600"),
        (7, "#FF6600"),
        (6, "#FFFF00"),
        (5, "#FFFF00"),
        (2, "#00FF00"),
        (1, "#00FF00"),
    ])
    def test_severity_color_levels(self, alert_handler, severity, expected_color):
        """Test color assignment for different severity levels"""
        color = alert_handler._get_severity_color(severity)
        assert color == expected_color
