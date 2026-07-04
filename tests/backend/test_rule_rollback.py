"""Sprint 35 Phase 3: Rule Rollback Tests

Tests for rule version management and rollback functionality.
Covers RuleVersionRepository, VersionManager, and rollback workflows.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.storage.rule_version import RuleVersionRepository, RuleVersion
from guardian.validators.version_manager import VersionManager


class TestRuleVersion:
    """Test RuleVersion data class"""

    def test_rule_version_creation(self):
        """Test creating a rule version object"""
        content = {"rule_type": "connection_spike", "threshold": 10}
        version = RuleVersion(
            rule_id="rule-1",
            version_id="ver-1",
            version_number=1,
            rule_content=content,
            created_at="2026-05-23T10:00:00Z",
            created_by="user-1"
        )

        assert version.rule_id == "rule-1"
        assert version.version_number == 1
        assert version.rule_content == content

    def test_rule_version_to_dict(self):
        """Test converting version to dictionary"""
        content = {"rule_type": "auth_failure", "threshold": 5}
        version = RuleVersion(
            rule_id="rule-2",
            version_id="ver-2",
            version_number=2,
            rule_content=content,
            created_at="2026-05-23T10:00:00Z"
        )

        data = version.to_dict()

        assert data["rule_id"] == "rule-2"
        assert data["version_id"] == "ver-2"
        assert data["rule_content"] == content
        assert "created_by" not in data  # None values excluded


class TestRuleVersionRepository:
    """Test RuleVersionRepository"""

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_table
            repo = RuleVersionRepository('test-versions-table')
            repo.table = mock_table
            return repo

    def test_save_version(self, repository, mock_table):
        """Test saving a new version"""
        mock_table.put_item = MagicMock()
        mock_table.query.return_value = {"Items": []}

        content = {"rule_type": "connection_spike", "threshold": 10}
        version = repository.save_version(
            rule_id="rule-1",
            rule_content=content,
            created_by="user-1",
            change_reason="Initial version"
        )

        assert version.rule_id == "rule-1"
        assert version.version_number == 1
        assert version.rule_content == content
        mock_table.put_item.assert_called_once()

    def test_get_version(self, repository, mock_table):
        """Test retrieving a specific version"""
        content = {"rule_type": "auth_failure", "threshold": 5}
        mock_table.get_item.return_value = {
            "Item": {
                "rule_id": "rule-2",
                "version_id": "ver-1",
                "version_number": 1,
                "rule_content": content,
                "created_at": "2026-05-23T10:00:00Z",
                "created_by": "system"
            }
        }

        version = repository.get_version("rule-2", "ver-1")

        assert version is not None
        assert version.rule_id == "rule-2"
        assert version.version_number == 1

    def test_list_versions(self, repository, mock_table):
        """Test listing all versions for a rule"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "rule_id": "rule-1",
                    "version_id": "ver-2",
                    "version_number": 2,
                    "rule_content": {"rule_type": "connection_spike"},
                    "created_at": "2026-05-23T11:00:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "version_id": "ver-1",
                    "version_number": 1,
                    "rule_content": {"rule_type": "auth_failure"},
                    "created_at": "2026-05-23T10:00:00Z"
                }
            ]
        }

        versions = repository.list_versions("rule-1", limit=10)

        assert len(versions) == 2
        assert versions[0].version_number == 2
        assert versions[1].version_number == 1

    def test_rollback_to_version(self, repository, mock_table):
        """Test rolling back to a previous version"""
        mock_table.get_item.return_value = {
            "Item": {
                "rule_id": "rule-1",
                "version_id": "ver-1",
                "version_number": 1,
                "rule_content": {"rule_type": "connection_spike", "threshold": 10},
                "created_at": "2026-05-23T10:00:00Z"
            }
        }
        mock_table.query.return_value = {"Items": []}
        mock_table.put_item = MagicMock()

        new_version = repository.rollback_to_version(
            rule_id="rule-1",
            version_id="ver-1",
            rolled_back_by="user-1"
        )

        assert new_version is not None
        assert new_version.version_number == 1
        assert new_version.change_reason == "Rollback to version ver-1"


class TestVersionManager:
    """Test VersionManager"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MagicMock(spec=RuleVersionRepository)

    @pytest.fixture
    def manager(self, mock_repo):
        """Create manager with mocked repository"""
        return VersionManager(mock_repo)

    def test_create_new_version(self, manager, mock_repo):
        """Test creating a new version"""
        content = {"rule_type": "unknown_region"}
        mock_version = MagicMock()
        mock_version.version_id = "ver-1"
        mock_version.version_number = 1
        mock_repo.save_version.return_value = mock_version

        version = manager.create_new_version(
            rule_id="rule-1",
            rule_content=content,
            user_id="user-1",
            reason="Manual update"
        )

        assert version.version_number == 1
        mock_repo.save_version.assert_called_once()

    def test_can_rollback_valid_version(self, manager, mock_repo):
        """Test checking if valid version can be rolled back"""
        old_version = MagicMock()
        old_version.version_id = "ver-1"
        old_version.rule_content = {"rule_type": "connection_spike"}

        current_version = MagicMock()
        current_version.version_id = "ver-2"

        mock_repo.get_version.return_value = old_version
        mock_repo.get_latest_version.return_value = current_version

        can_rollback, message = manager.can_rollback("rule-1", "ver-1")

        assert can_rollback is True
        assert "Ready to rollback" in message

    def test_can_rollback_current_version(self, manager, mock_repo):
        """Test that current version cannot be rolled back"""
        version = MagicMock()
        version.version_id = "ver-2"
        version.rule_content = {"rule_type": "connection_spike"}

        mock_repo.get_version.return_value = version
        mock_repo.get_latest_version.return_value = version

        can_rollback, message = manager.can_rollback("rule-1", "ver-2")

        assert can_rollback is False
        assert "Cannot rollback to current version" in message

    def test_perform_rollback(self, manager, mock_repo):
        """Test performing rollback"""
        old_version = MagicMock()
        old_version.version_id = "ver-1"
        old_version.version_number = 1
        old_version.rule_content = {"rule_type": "auth_failure"}

        current_version = MagicMock()
        current_version.version_id = "ver-2"

        new_version = MagicMock()
        new_version.version_id = "ver-3"
        new_version.version_number = 3

        mock_repo.get_version.return_value = old_version
        mock_repo.get_latest_version.return_value = current_version
        mock_repo.rollback_to_version.return_value = new_version

        success, message, result = manager.perform_rollback(
            rule_id="rule-1",
            version_id="ver-1",
            user_id="user-1"
        )

        assert success is True
        assert result.version_number == 3
        assert "Successfully rolled back" in message

    def test_get_version_history(self, manager, mock_repo):
        """Test getting formatted version history"""
        v1 = MagicMock()
        v1.version_id = "ver-1"
        v1.version_number = 1
        v1.created_at = "2026-05-23T10:00:00Z"
        v1.created_by = "user-1"
        v1.change_reason = "Initial"
        v1.rule_content = {}

        mock_repo.list_versions.return_value = [v1]

        history = manager.get_version_history("rule-1", limit=10)

        assert len(history) == 1
        assert history[0]["version_number"] == 1
        assert history[0]["created_by"] == "user-1"
