"""Sprint 34 Phase 2: Rule Validation Tests

Tests for rule validation, schema checking, and dry-run testing.
Covers RuleValidator, ValidationResult, and validation_handler.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from validators.rule_validator import RuleValidator
from validators.validation_result import ValidationResult
from storage.rule_template import RuleTemplate, TemplateRepository


class TestValidationResult:
    """Test ValidationResult data class"""

    def test_validation_result_valid(self):
        """Test creating a valid validation result"""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.dry_run_threats) == 0

    def test_add_error(self):
        """Test adding errors to result"""
        result = ValidationResult(is_valid=True)
        result.add_error("Invalid threshold")

        assert result.is_valid is False
        assert "Invalid threshold" in result.errors
        assert len(result.errors) == 1

    def test_add_warning(self):
        """Test adding warnings to result"""
        result = ValidationResult(is_valid=True)
        result.add_warning("Priority should be between 1-10")

        assert result.is_valid is True
        assert "Priority should be between 1-10" in result.warnings

    def test_add_dry_run_threat(self):
        """Test adding dry-run threat"""
        result = ValidationResult(is_valid=True)
        threat = {
            "threat_id": "threat-1",
            "rule_id": "rule-1",
            "severity": 5,
            "message": "Test threat",
            "account_id": "acc-1",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "evidence_count": 3,
        }
        result.add_dry_run_threat(threat)

        assert len(result.dry_run_threats) == 1
        assert result.dry_run_threats[0]["threat_id"] == "threat-1"

    def test_validation_result_to_dict(self):
        """Test converting result to dictionary"""
        result = ValidationResult(is_valid=True, execution_time_ms=42.5)
        result.add_warning("Test warning")

        data = result.to_dict()

        assert data["is_valid"] is True
        assert "Test warning" in data["warnings"]
        assert data["execution_time_ms"] == 42.5
        assert "validated_at" in data


class TestRuleValidator:
    """Test RuleValidator class"""

    @pytest.fixture
    def mock_template_repo(self):
        """Mock template repository"""
        return MagicMock(spec=TemplateRepository)

    @pytest.fixture
    def mock_anomaly_detector(self):
        """Mock anomaly detector"""
        return MagicMock()

    @pytest.fixture
    def validator(self, mock_template_repo, mock_anomaly_detector):
        """Create validator with mocks"""
        return RuleValidator(mock_template_repo, mock_anomaly_detector)

    def test_validate_rule_valid_connection_spike(self, validator):
        """Test validating a valid connection_spike rule"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {
                "threshold": 10,
                "window_minutes": 5,
            },
            "action": {
                "notify": ["telegram", "discord"],
            },
        }

        result = validator.validate(rule)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_rule_missing_required_field(self, validator):
        """Test validating rule with missing required field"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {"threshold": 10},
            # Missing 'action' field
        }

        result = validator.validate(rule)

        assert result.is_valid is False
        assert "Missing required field: action" in result.errors

    def test_validate_rule_invalid_threshold(self, validator):
        """Test validating rule with invalid threshold"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {
                "threshold": -1,  # Invalid: should be positive
                "window_minutes": 5,
            },
            "action": {
                "notify": ["telegram"],
            },
        }

        result = validator.validate(rule)

        assert result.is_valid is False
        assert any("threshold" in error.lower() for error in result.errors)

    def test_validate_rule_invalid_notification_channel(self, validator):
        """Test validating rule with unknown notification channel"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {
                "threshold": 10,
                "window_minutes": 5,
            },
            "action": {
                "notify": ["telegram", "unknown_channel"],
            },
        }

        result = validator.validate(rule)

        assert result.is_valid is True  # Still valid, just warning
        assert "Unknown notification channel: unknown_channel" in result.warnings

    def test_test_rule_with_dry_run(self, validator, mock_anomaly_detector):
        """Test dry-run evaluation of rule"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {
                "threshold": 2,
                "window_minutes": 5,
            },
            "action": {
                "notify": ["telegram"],
            },
            "priority": 5,
            "enabled": True,
        }

        test_logs = [
            {
                "event_type": "$connect",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "account_id": "acc-1",
            },
            {
                "event_type": "$connect",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "account_id": "acc-1",
            },
        ]

        # Mock the anomaly detector to return a threat
        mock_threat = MagicMock()
        mock_threat.threat_id = "threat-1"
        mock_threat.rule_id = "rule-1"
        mock_threat.severity = 5
        mock_threat.message = "Connection spike detected"
        mock_threat.account_id = "acc-1"
        mock_threat.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        mock_threat.evidence = test_logs

        mock_anomaly_detector.detect_anomalies.return_value = [mock_threat]

        result = validator.test_rule(rule, test_logs, "acc-1")

        assert result.is_valid is True
        assert len(result.dry_run_threats) > 0

    def test_validate_auth_failure_rule(self, validator):
        """Test validating auth_failure rule"""
        rule = {
            "rule_type": "auth_failure",
            "condition": {
                "threshold": 5,
            },
            "action": {
                "notify": ["discord"],
            },
        }

        result = validator.validate(rule)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_unknown_region_rule(self, validator):
        """Test validating unknown_region rule"""
        rule = {
            "rule_type": "unknown_region",
            "condition": {
                "allowed_regions": ["ap-northeast-1", "us-east-1"],
            },
            "action": {
                "notify": ["telegram"],
            },
        }

        result = validator.validate(rule)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_rule_invalid_priority(self, validator):
        """Test validating rule with invalid priority"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {"threshold": 10},
            "action": {"notify": ["telegram"]},
            "priority": 15,  # Invalid: should be 1-10
        }

        result = validator.validate(rule)

        assert result.is_valid is True  # Still valid, just warning
        assert any("Priority should be between 1-10" in w for w in result.warnings)


class TestValidationHandler:
    """Test validation Lambda handler"""

    def test_validate_rule_handler_valid(self):
        """Test validation handler with valid rule"""
        from handlers.validation_handler import validate_rule
        from validators.rule_validator import RuleValidator

        mock_template_repo = MagicMock()
        mock_anomaly_detector = MagicMock()
        validator = RuleValidator(mock_template_repo, mock_anomaly_detector)

        body = {
            "rule": {
                "rule_type": "connection_spike",
                "condition": {"threshold": 10, "window_minutes": 5},
                "action": {"notify": ["telegram"]},
            }
        }

        response = validate_rule(validator, body)

        assert response["statusCode"] == 200
        data = response["body"]
        # Body is JSON string, parse it
        import json
        parsed = json.loads(data)
        assert parsed["is_valid"] is True

    def test_validate_rule_handler_missing_field(self):
        """Test validation handler with missing rule field"""
        from handlers.validation_handler import validate_rule
        from validators.rule_validator import RuleValidator

        mock_template_repo = MagicMock()
        mock_anomaly_detector = MagicMock()
        validator = RuleValidator(mock_template_repo, mock_anomaly_detector)

        body = {}  # Missing 'rule' field

        response = validate_rule(validator, body)

        assert response["statusCode"] == 400
        assert "Missing required field: rule" in response["body"]
