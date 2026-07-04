"""Sprint 36 Phase 3: Response Audit System Tests

Tests for advanced response tracking with rollback capability.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.storage.response_audit import ResponseAuditRepository, ResponseAction


class TestResponseAuditRepository:
    """Test ResponseAuditRepository"""

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_table
            repo = ResponseAuditRepository('response-audit-table')
            return repo

    def test_record_response_success(self, repository, mock_table):
        """Test recording a successful response"""
        mock_table.put_item = MagicMock()

        action = repository.record_response(
            threat_id="threat-1",
            rule_id="rule-1",
            action_type="EC2_STOP",
            target="i-1234567890abcdef0",
            success=True,
            message="Stopped suspicious instance"
        )

        assert action.threat_id == "threat-1"
        assert action.action_type == "EC2_STOP"
        assert action.success is True
        assert action.status == "EXECUTED"
        assert action.executed_by == "system"
        mock_table.put_item.assert_called_once()

    def test_record_response_failed(self, repository, mock_table):
        """Test recording a failed response"""
        mock_table.put_item = MagicMock()

        action = repository.record_response(
            threat_id="threat-2",
            rule_id="rule-2",
            action_type="S3_BLOCK_PUBLIC",
            target="malicious-bucket",
            success=False,
            message="Failed to block - bucket not found"
        )

        assert action.success is False
        assert action.status == "FAILED"

    def test_record_response_with_rollback_metadata(self, repository, mock_table):
        """Test recording response with rollback information"""
        mock_table.put_item = MagicMock()

        rollback_metadata = {
            "original_state": "running",
            "region": "us-east-1"
        }

        action = repository.record_response(
            threat_id="threat-ec2",
            rule_id="rule-ec2",
            action_type="EC2_STOP",
            target="i-abc123",
            success=True,
            message="Stopped instance",
            rollback_action_type="EC2_START",
            rollback_metadata=rollback_metadata
        )

        assert action.rollback_action_type == "EC2_START"
        assert action.rollback_metadata == rollback_metadata

    def test_record_response_with_state_snapshots(self, repository, mock_table):
        """Test recording response with pre/post action state"""
        mock_table.put_item = MagicMock()

        pre_state = {"State": "running", "InstanceType": "t2.micro"}
        post_state = {"State": "stopped"}

        action = repository.record_response(
            threat_id="threat-3",
            rule_id="rule-3",
            action_type="EC2_STOP",
            target="i-xyz789",
            success=True,
            message="Instance stopped",
            pre_action_state=pre_state,
            post_action_state=post_state
        )

        assert action.pre_action_state == pre_state
        assert action.post_action_state == post_state

    def test_get_response_by_id(self, repository, mock_table):
        """Test retrieving a response by ID"""
        mock_table.get_item.return_value = {
            "Item": {
                "response_id": "resp-1",
                "threat_id": "threat-1",
                "rule_id": "rule-1",
                "action_type": "EC2_STOP",
                "target": "i-123",
                "success": True,
                "status": "EXECUTED",
                "timestamp": "2026-05-23T12:00:00Z",
                "executed_by": "system",
                "message": "Stopped instance",
                "can_rollback": True
            }
        }

        action = repository.get_response("resp-1")

        assert action.response_id == "resp-1"
        assert action.action_type == "EC2_STOP"
        assert action.target == "i-123"

    def test_list_responses_by_threat(self, repository, mock_table):
        """Test listing responses for a threat"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "response_id": "resp-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-123",
                    "success": True,
                    "status": "EXECUTED",
                    "timestamp": "2026-05-23T12:00:00Z",
                    "executed_by": "system",
                    "message": "Stopped",
                    "can_rollback": True
                }
            ]
        }

        responses = repository.list_responses_by_threat("threat-1")

        assert len(responses) == 1
        assert responses[0].threat_id == "threat-1"

    def test_list_responses_by_rule(self, repository, mock_table):
        """Test listing responses for a rule"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "response_id": "resp-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-ec2",
                    "action_type": "EC2_STOP",
                    "target": "i-123",
                    "success": True,
                    "status": "EXECUTED",
                    "timestamp": "2026-05-23T12:00:00Z",
                    "executed_by": "system",
                    "message": "Stopped",
                    "can_rollback": True
                },
                {
                    "response_id": "resp-2",
                    "threat_id": "threat-2",
                    "rule_id": "rule-ec2",
                    "action_type": "EC2_STOP",
                    "target": "i-456",
                    "success": False,
                    "status": "FAILED",
                    "timestamp": "2026-05-23T12:05:00Z",
                    "executed_by": "system",
                    "message": "Failed",
                    "can_rollback": True
                }
            ]
        }

        responses = repository.list_responses_by_rule("rule-ec2")

        assert len(responses) == 2
        assert responses[0].success is True
        assert responses[1].success is False

    def test_mark_rollback_executed_success(self, repository, mock_table):
        """Test marking rollback as executed successfully"""
        mock_table.update_item = MagicMock()

        success = repository.mark_rollback_executed(
            response_id="resp-1",
            rollback_status="SUCCESS",
            executed_by="user-123",
            message="Instance restarted"
        )

        assert success is True
        mock_table.update_item.assert_called_once()

    def test_mark_rollback_executed_failure(self, repository, mock_table):
        """Test marking rollback as executed with failure"""
        mock_table.update_item = MagicMock()

        success = repository.mark_rollback_executed(
            response_id="resp-2",
            rollback_status="FAILED",
            executed_by="user-456",
            message="Instance not found for restart"
        )

        assert success is True

    def test_approve_response(self, repository, mock_table):
        """Test approving a response"""
        mock_table.update_item = MagicMock()

        success = repository.approve_response(
            response_id="resp-1",
            approved_by="security-admin",
            message="Approved rollback"
        )

        assert success is True
        mock_table.update_item.assert_called_once()

    def test_get_response_summary(self, repository, mock_table):
        """Test getting response summary for a rule"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "response_id": "resp-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-1",
                    "success": True,
                    "status": "EXECUTED",
                    "timestamp": "2026-05-23T12:00:00Z",
                    "executed_by": "system",
                    "message": "Success",
                    "can_rollback": True
                },
                {
                    "response_id": "resp-2",
                    "threat_id": "threat-2",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-2",
                    "success": True,
                    "status": "EXECUTED",
                    "timestamp": "2026-05-23T12:05:00Z",
                    "executed_by": "system",
                    "message": "Success",
                    "can_rollback": True
                },
                {
                    "response_id": "resp-3",
                    "threat_id": "threat-3",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-3",
                    "success": False,
                    "status": "FAILED",
                    "timestamp": "2026-05-23T12:10:00Z",
                    "executed_by": "system",
                    "message": "Failed",
                    "can_rollback": True
                },
                {
                    "response_id": "resp-4",
                    "threat_id": "threat-4",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-4",
                    "success": True,
                    "status": "ROLLED_BACK",
                    "timestamp": "2026-05-23T12:15:00Z",
                    "executed_by": "system",
                    "message": "Rolled back",
                    "can_rollback": True,
                    "rollback_executed_at": "2026-05-23T12:20:00Z",
                    "rollback_status": "SUCCESS"
                }
            ]
        }

        summary = repository.get_response_summary("rule-1")

        assert summary["rule_id"] == "rule-1"
        assert summary["total_responses"] == 4
        assert summary["executed"] == 2
        assert summary["failed"] == 1
        assert summary["rolled_back"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["action_counts"]["EC2_STOP"] == 4

    def test_response_requires_approval_flag(self, repository, mock_table):
        """Test recording response that requires approval"""
        mock_table.put_item = MagicMock()

        action = repository.record_response(
            threat_id="threat-sensitive",
            rule_id="rule-sensitive",
            action_type="EC2_STOP",
            target="i-prod",
            success=True,
            message="High-risk remediation executed",
            requires_approval=True
        )

        assert action.requires_approval is True
        assert action.approved_at is None
        assert action.approved_by is None
