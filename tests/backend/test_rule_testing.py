"""Sprint 35 Phase 1: Rule Testing Tests

Tests for rule dry-run testing and validation.
Covers TestExecutor, test results, and threat generation.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.validators.test_executor import TestExecutor, TestResult


class TestTestResult:
    """Test TestResult data class"""

    def test_test_result_successful(self):
        """Test creating a successful test result"""
        result = TestResult(
            rule_id="rule-1",
            total_logs=10,
            matched_logs=3,
            detected_threats=[],
            execution_time_ms=42.5,
            success=True
        )

        assert result.rule_id == "rule-1"
        assert result.total_logs == 10
        assert result.matched_logs == 3
        assert result.success is True
        assert result.execution_time_ms == 42.5
        assert result.error_message is None

    def test_test_result_with_error(self):
        """Test creating a failed test result"""
        result = TestResult(
            rule_id="rule-1",
            total_logs=0,
            matched_logs=0,
            detected_threats=[],
            execution_time_ms=10.0,
            success=False,
            error_message="Rule validation failed"
        )

        assert result.success is False
        assert result.error_message == "Rule validation failed"

    def test_test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = TestResult(
            rule_id="rule-1",
            total_logs=5,
            matched_logs=2,
            detected_threats=[{"threat_id": "t1", "severity": 8}],
            execution_time_ms=25.5,
            success=True
        )

        data = result.to_dict()

        assert data["rule_id"] == "rule-1"
        assert data["total_logs"] == 5
        assert data["matched_logs"] == 2
        assert len(data["detected_threats"]) == 1
        assert data["success"] is True


class TestTestExecutor:
    """Test TestExecutor class"""

    @pytest.fixture
    def executor(self):
        """Create test executor"""
        return TestExecutor()

    def test_execute_test_connection_spike(self, executor):
        """Test executing connection_spike rule"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "condition": {"threshold": 2, "window_minutes": 5},
            "action": {"notify": ["telegram"]},
            "priority": 5
        }

        test_logs = [
            {"event_type": "$connect", "timestamp": "2026-05-23T10:00:00Z", "account_id": "acc-1"},
            {"event_type": "$connect", "timestamp": "2026-05-23T10:01:00Z", "account_id": "acc-1"},
            {"event_type": "$disconnect", "timestamp": "2026-05-23T10:02:00Z", "account_id": "acc-1"},
        ]

        result = executor.execute_test(rule, test_logs, "acc-1")

        assert result.success is True
        assert result.total_logs == 3
        assert result.matched_logs == 2
        assert result.execution_time_ms > 0

    def test_execute_test_auth_failure(self, executor):
        """Test executing auth_failure rule"""
        rule = {
            "rule_id": "rule-2",
            "rule_type": "auth_failure",
            "condition": {"threshold": 2},
            "action": {"notify": ["telegram"]},
            "priority": 8
        }

        test_logs = [
            {"event_type": "auth_login", "status": "failed", "timestamp": "2026-05-23T10:00:00Z"},
            {"event_type": "auth_login", "status": "success", "timestamp": "2026-05-23T10:01:00Z"},
            {"event_type": "auth_login", "status": "failed", "timestamp": "2026-05-23T10:02:00Z"},
        ]

        result = executor.execute_test(rule, test_logs, "acc-1")

        assert result.success is True
        assert result.matched_logs == 2

    def test_execute_test_unknown_region(self, executor):
        """Test executing unknown_region rule"""
        rule = {
            "rule_id": "rule-3",
            "rule_type": "unknown_region",
            "condition": {"allowed_regions": ["ap-northeast-1", "us-east-1"]},
            "action": {"notify": ["telegram"]},
            "priority": 7
        }

        test_logs = [
            {"region": "ap-northeast-1", "event_type": "ec2-run-instances"},
            {"region": "eu-west-1", "event_type": "ec2-run-instances"},
            {"region": "us-east-1", "event_type": "ec2-run-instances"},
        ]

        result = executor.execute_test(rule, test_logs, "acc-1")

        assert result.success is True
        assert result.matched_logs == 1

    def test_execute_test_public_bucket(self, executor):
        """Test executing public_bucket rule"""
        rule = {
            "rule_id": "rule-4",
            "rule_type": "public_bucket",
            "condition": {},
            "action": {"notify": ["telegram"]},
            "priority": 9
        }

        test_logs = [
            {"service": "s3", "event_type": "create-bucket", "bucket_name": "my-bucket"},
            {"service": "iam", "event_type": "create-user", "user_name": "user1"},
            {"service": "s3", "event_type": "update-bucket-policy", "bucket_name": "my-bucket"},
        ]

        result = executor.execute_test(rule, test_logs, "acc-1")

        assert result.success is True
        assert result.matched_logs == 2

    def test_execute_test_empty_logs(self, executor):
        """Test executing rule with empty logs"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "condition": {},
            "action": {},
            "priority": 5
        }

        result = executor.execute_test(rule, [], "acc-1")

        assert result.success is False
        assert result.error_message == "Rule or test logs are empty"

    def test_execute_test_missing_rule_fields(self, executor):
        """Test executing with incomplete rule (graceful handling)"""
        rule = {
            "rule_id": "rule-1"
            # Missing rule_type and condition - should handle gracefully
        }

        test_logs = [{"event_type": "$connect"}]

        result = executor.execute_test(rule, test_logs, "acc-1")

        # Should succeed but with 0 matches since rule_type is missing
        assert result.success is True
        assert result.matched_logs == 0

    def test_validate_test_input_valid(self, executor):
        """Test validation of valid test input"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {},
            "action": {}
        }

        test_logs = [{"event_type": "$connect"}]

        is_valid, error = executor.validate_test_input(rule, test_logs)

        assert is_valid is True
        assert error is None

    def test_validate_test_input_missing_rule(self, executor):
        """Test validation with missing rule"""
        is_valid, error = executor.validate_test_input(None, [{"event_type": "$connect"}])

        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_test_input_missing_logs(self, executor):
        """Test validation with missing logs"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {},
            "action": {}
        }

        is_valid, error = executor.validate_test_input(rule, [])

        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_test_input_invalid_type(self, executor):
        """Test validation with invalid log type"""
        rule = {
            "rule_type": "connection_spike",
            "condition": {},
            "action": {}
        }

        is_valid, error = executor.validate_test_input(rule, "not a list")

        assert is_valid is False
        assert "list" in error.lower()

    def test_generate_test_threats(self, executor):
        """Test threat generation from matched logs"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "priority": 8
        }

        matched_logs = [
            {"event_type": "$connect", "timestamp": "2026-05-23T10:00:00Z"},
            {"event_type": "$connect", "timestamp": "2026-05-23T10:01:00Z"},
        ]

        threats = executor._generate_test_threats(rule, matched_logs, "acc-1")

        assert len(threats) == 1
        assert threats[0]["rule_id"] == "rule-1"
        assert threats[0]["severity"] == 8
        assert threats[0]["account_id"] == "acc-1"
        assert threats[0]["evidence_count"] == 2

    def test_execute_test_performance(self, executor):
        """Test execution time tracking"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "condition": {},
            "action": {},
            "priority": 5
        }

        # Create 1000 test logs
        test_logs = [{"event_type": "$connect"} for _ in range(1000)]

        result = executor.execute_test(rule, test_logs, "acc-1")

        assert result.success is True
        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 5000  # Should complete within 5 seconds
