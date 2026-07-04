"""Sprint 35 Phase 4: Rule Audit Logging Tests

Tests for rule audit logging functionality.
Covers RuleAuditRepository and audit trail management.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.storage.rule_audit import RuleAuditRepository, AuditLog


class TestAuditLog:
    """Test AuditLog data class"""

    def test_audit_log_creation(self):
        """Test creating an audit log object"""
        log = AuditLog(
            rule_id="rule-1",
            audit_id="audit-1",
            action="CREATE",
            timestamp="2026-05-23T10:00:00Z",
            user_id="user-1",
            status="SUCCESS"
        )

        assert log.rule_id == "rule-1"
        assert log.action == "CREATE"
        assert log.status == "SUCCESS"

    def test_audit_log_to_dict(self):
        """Test converting audit log to dictionary"""
        details = {"rule_type": "connection_spike"}
        log = AuditLog(
            rule_id="rule-2",
            audit_id="audit-2",
            action="UPDATE",
            timestamp="2026-05-23T10:00:00Z",
            details=details,
            status="SUCCESS"
        )

        data = log.to_dict()

        assert data["rule_id"] == "rule-2"
        assert data["action"] == "UPDATE"
        assert data["details"] == details
        assert "user_id" not in data  # None values excluded


class TestRuleAuditRepository:
    """Test RuleAuditRepository"""

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_table
            repo = RuleAuditRepository('test-audit-table')
            repo.table = mock_table
            return repo

    def test_log_create_action(self, repository, mock_table):
        """Test logging a CREATE action"""
        mock_table.put_item = MagicMock()

        log = repository.log_action(
            rule_id="rule-1",
            action="CREATE",
            user_id="user-1",
            details={"rule_type": "connection_spike"}
        )

        assert log.rule_id == "rule-1"
        assert log.action == "CREATE"
        assert log.status == "SUCCESS"
        mock_table.put_item.assert_called_once()

    def test_log_deploy_action(self, repository, mock_table):
        """Test logging a DEPLOY action"""
        mock_table.put_item = MagicMock()

        log = repository.log_action(
            rule_id="rule-2",
            action="DEPLOY",
            user_id="system",
            status="SUCCESS"
        )

        assert log.action == "DEPLOY"
        assert log.user_id == "system"

    def test_log_rollback_action(self, repository, mock_table):
        """Test logging a ROLLBACK action"""
        mock_table.put_item = MagicMock()

        log = repository.log_action(
            rule_id="rule-3",
            action="ROLLBACK",
            user_id="user-2",
            details={"previous_version": "v1"}
        )

        assert log.action == "ROLLBACK"
        assert log.details["previous_version"] == "v1"

    def test_log_failed_action(self, repository, mock_table):
        """Test logging a failed action"""
        mock_table.put_item = MagicMock()

        log = repository.log_action(
            rule_id="rule-4",
            action="UPDATE",
            user_id="user-3",
            status="FAILURE",
            error_message="Invalid rule configuration"
        )

        assert log.status == "FAILURE"
        assert log.error_message == "Invalid rule configuration"

    def test_list_audit_logs(self, repository, mock_table):
        """Test listing audit logs"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-2",
                    "action": "UPDATE",
                    "timestamp": "2026-05-23T11:00:00Z",
                    "user_id": "user-1",
                    "status": "SUCCESS"
                },
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-1",
                    "action": "CREATE",
                    "timestamp": "2026-05-23T10:00:00Z",
                    "user_id": "user-1",
                    "status": "SUCCESS"
                }
            ]
        }

        logs = repository.list_audit_logs("rule-1", limit=10)

        assert len(logs) == 2
        assert logs[0].action == "UPDATE"
        assert logs[1].action == "CREATE"

    def test_get_audit_summary(self, repository, mock_table):
        """Test getting audit summary"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-3",
                    "action": "DEPLOY",
                    "timestamp": "2026-05-23T12:00:00Z",
                    "status": "SUCCESS"
                },
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-2",
                    "action": "UPDATE",
                    "timestamp": "2026-05-23T11:00:00Z",
                    "status": "SUCCESS"
                },
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-1",
                    "action": "CREATE",
                    "timestamp": "2026-05-23T10:00:00Z",
                    "status": "SUCCESS"
                }
            ]
        }

        summary = repository.get_audit_summary("rule-1")

        assert summary["rule_id"] == "rule-1"
        assert summary["total_logs"] == 3
        assert summary["action_counts"]["CREATE"] == 1
        assert summary["action_counts"]["UPDATE"] == 1
        assert summary["action_counts"]["DEPLOY"] == 1
        assert summary["status_counts"]["SUCCESS"] == 3

    def test_count_actions(self, repository, mock_table):
        """Test counting actions"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-2",
                    "action": "UPDATE",
                    "timestamp": "2026-05-23T11:00:00Z",
                    "status": "SUCCESS"
                },
                {
                    "rule_id": "rule-1",
                    "audit_id": "audit-1",
                    "action": "CREATE",
                    "timestamp": "2026-05-23T10:00:00Z",
                    "status": "SUCCESS"
                }
            ]
        }

        count = repository.count_actions("rule-1", "UPDATE")

        assert count == 1
