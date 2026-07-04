"""Sprint 35 Phase 2: Rule Deployment Tests

Tests for rule deployment system and state tracking.
Covers RuleDeploymentRepository and deployment workflows.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.storage.rule_deployment import RuleDeploymentRepository, Deployment


class TestDeployment:
    """Test Deployment data class"""

    def test_deployment_creation(self):
        """Test creating a deployment object"""
        deployment = Deployment(
            rule_id="rule-1",
            deployment_id="deploy-1",
            status="ACTIVE",
            deployment_date="2026-05-23T10:00:00Z",
            deployed_by="user-1"
        )

        assert deployment.rule_id == "rule-1"
        assert deployment.status == "ACTIVE"
        assert deployment.deployed_by == "user-1"

    def test_deployment_to_dict(self):
        """Test converting deployment to dictionary"""
        deployment = Deployment(
            rule_id="rule-1",
            deployment_id="deploy-1",
            status="PENDING",
            deployment_date="2026-05-23T10:00:00Z"
        )

        data = deployment.to_dict()

        assert data["rule_id"] == "rule-1"
        assert data["deployment_id"] == "deploy-1"
        assert data["status"] == "PENDING"
        assert data["deployment_date"] == "2026-05-23T10:00:00Z"
        assert "deployed_by" not in data  # None values excluded


class TestRuleDeploymentRepository:
    """Test RuleDeploymentRepository"""

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table"""
        table = MagicMock()
        return table

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_table
            repo = RuleDeploymentRepository('test-table')
            repo.table = mock_table
            return repo

    def test_create_deployment_pending(self, repository, mock_table):
        """Test creating a PENDING deployment"""
        mock_table.put_item = MagicMock()

        deployment = repository.create_deployment(
            rule_id="rule-1",
            status="PENDING",
            deployed_by="user-1"
        )

        assert deployment.rule_id == "rule-1"
        assert deployment.status == "PENDING"
        assert deployment.deployed_by == "user-1"
        assert deployment.deployment_id is not None
        mock_table.put_item.assert_called_once()

    def test_create_deployment_active(self, repository, mock_table):
        """Test creating an ACTIVE deployment"""
        mock_table.put_item = MagicMock()

        rule_content = {
            "rule_type": "connection_spike",
            "condition": {"threshold": 10},
            "action": {"notify": ["telegram"]}
        }

        deployment = repository.create_deployment(
            rule_id="rule-2",
            status="ACTIVE",
            rule_content=rule_content,
            deployed_by="user-1"
        )

        assert deployment.status == "ACTIVE"
        assert deployment.rule_content == rule_content

    def test_get_deployment(self, repository, mock_table):
        """Test retrieving a specific deployment"""
        mock_table.get_item = MagicMock(return_value={
            "Item": {
                "rule_id": "rule-1",
                "deployment_id": "deploy-1",
                "status": "ACTIVE",
                "deployment_date": "2026-05-23T10:00:00Z",
                "deployed_by": "user-1"
            }
        })

        deployment = repository.get_deployment("rule-1", "deploy-1")

        assert deployment is not None
        assert deployment.rule_id == "rule-1"
        assert deployment.status == "ACTIVE"

    def test_get_deployment_not_found(self, repository, mock_table):
        """Test retrieving a non-existent deployment"""
        mock_table.get_item = MagicMock(return_value={})

        deployment = repository.get_deployment("rule-1", "deploy-999")

        assert deployment is None

    def test_list_deployments(self, repository, mock_table):
        """Test listing deployments for a rule"""
        mock_table.query = MagicMock(return_value={
            "Items": [
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-3",
                    "status": "ACTIVE",
                    "deployment_date": "2026-05-23T10:02:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-2",
                    "status": "ROLLED_BACK",
                    "deployment_date": "2026-05-23T10:01:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-1",
                    "status": "ACTIVE",
                    "deployment_date": "2026-05-23T10:00:00Z"
                }
            ]
        })

        deployments = repository.list_deployments("rule-1")

        assert len(deployments) == 3
        assert deployments[0].deployment_id == "deploy-3"
        mock_table.query.assert_called_once()

    def test_list_deployments_empty(self, repository, mock_table):
        """Test listing deployments when none exist"""
        mock_table.query = MagicMock(return_value={"Items": []})

        deployments = repository.list_deployments("rule-1")

        assert len(deployments) == 0

    def test_update_deployment_status(self, repository, mock_table):
        """Test updating deployment status"""
        mock_table.update_item = MagicMock(return_value={
            "Attributes": {
                "rule_id": "rule-1",
                "deployment_id": "deploy-1",
                "status": "ACTIVE",
                "deployment_date": "2026-05-23T10:00:00Z"
            }
        })

        deployment = repository.update_deployment_status(
            "rule-1", "deploy-1", "ACTIVE"
        )

        assert deployment is not None
        assert deployment.status == "ACTIVE"

    def test_update_deployment_status_with_error(self, repository, mock_table):
        """Test updating deployment status with error message"""
        mock_table.update_item = MagicMock(return_value={
            "Attributes": {
                "rule_id": "rule-1",
                "deployment_id": "deploy-1",
                "status": "FAILED",
                "deployment_date": "2026-05-23T10:00:00Z",
                "error_message": "Rule validation failed"
            }
        })

        deployment = repository.update_deployment_status(
            "rule-1", "deploy-1", "FAILED",
            error_message="Rule validation failed"
        )

        assert deployment.status == "FAILED"
        assert deployment.error_message == "Rule validation failed"

    def test_get_active_deployment(self, repository, mock_table):
        """Test retrieving the active deployment for a rule"""
        mock_table.query = MagicMock(return_value={
            "Items": [
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-2",
                    "status": "ACTIVE",
                    "deployment_date": "2026-05-23T10:01:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-1",
                    "status": "ROLLED_BACK",
                    "deployment_date": "2026-05-23T10:00:00Z"
                }
            ]
        })

        deployment = repository.get_active_deployment("rule-1")

        assert deployment is not None
        assert deployment.status == "ACTIVE"
        assert deployment.deployment_id == "deploy-2"

    def test_count_active_deployments(self, repository, mock_table):
        """Test counting active deployments"""
        mock_table.query = MagicMock(return_value={
            "Items": [
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-3",
                    "status": "PENDING",
                    "deployment_date": "2026-05-23T10:02:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-2",
                    "status": "ACTIVE",
                    "deployment_date": "2026-05-23T10:01:00Z"
                },
                {
                    "rule_id": "rule-1",
                    "deployment_id": "deploy-1",
                    "status": "ACTIVE",
                    "deployment_date": "2026-05-23T10:00:00Z"
                }
            ]
        })

        count = repository.count_active_deployments("rule-1")

        # Note: In real scenario, there should only be 1 active deployment
        # This test shows the count of all ACTIVE status deployments
        assert count == 2
