"""Sprint 36 Phase 2: Rule-Based Remediation Tests

Tests for automatic remediation execution based on rule definitions.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import json
import sys
from pathlib import Path
from guardian.responders.rule_remediation import RuleRemediationExecutor, RemediationResult
from guardian.storage.remediation_audit import RemediationAuditRepository, RemediationLog
from guardian.detectors.anomaly_detector import Threat


class TestRuleRemediationExecutor:
    """Test RuleRemediationExecutor"""

    @pytest.fixture
    def mock_aws_executor(self):
        """Create mock AWSActionExecutor"""
        return MagicMock()

    @pytest.fixture
    def executor(self, mock_aws_executor):
        """Create RuleRemediationExecutor with mocked AWS executor"""
        return RuleRemediationExecutor(aws_executor=mock_aws_executor)

    @pytest.fixture
    def sample_threat(self):
        """Create sample threat for testing"""
        return Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=8,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Public bucket detected",
            evidence=[
                {
                    "bucket_name": "my-public-bucket",
                    "region": "us-east-1",
                    "public_acl": True
                }
            ]
        )

    def test_remediation_disabled_returns_empty(self, executor, sample_threat):
        """Test that disabled remediation returns empty list"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "public_bucket",
            "action": {
                "auto_remediate": False  # Disabled
            }
        }

        results = executor.execute_remediation(rule, sample_threat)

        assert results == []

    def test_no_remediation_actions_returns_empty(self, executor, sample_threat):
        """Test that rules without remediation_actions return empty list"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "public_bucket",
            "action": {
                "auto_remediate": True,
                "remediation_actions": []  # Empty
            }
        }

        results = executor.execute_remediation(rule, sample_threat)

        assert results == []

    def test_ec2_stop_remediation(self, executor, mock_aws_executor):
        """Test EC2 stop remediation"""
        threat = Threat(
            threat_id="threat-ec2",
            rule_id="rule-ec2",
            severity=9,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Suspicious EC2 instance",
            evidence=[
                {
                    "instance_id": "i-1234567890abcdef0",
                    "region": "us-east-1"
                }
            ]
        )

        rule = {
            "rule_id": "rule-ec2",
            "rule_type": "anomalous_ec2",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "EC2_STOP",
                        "enabled": True,
                        "parameters": {"region": "us-east-1"}
                    }
                ]
            }
        }

        mock_aws_executor.stop_ec2_instance.return_value = True

        results = executor.execute_remediation(rule, threat)

        assert len(results) == 1
        assert results[0].action_type == "EC2_STOP"
        assert results[0].target == "i-1234567890abcdef0"
        assert results[0].success is True
        mock_aws_executor.stop_ec2_instance.assert_called_once_with(
            "i-1234567890abcdef0", "us-east-1"
        )

    def test_s3_block_remediation(self, executor, mock_aws_executor, sample_threat):
        """Test S3 block public access remediation"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "public_bucket",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "S3_BLOCK_PUBLIC",
                        "enabled": True
                    }
                ]
            }
        }

        mock_aws_executor.block_s3_public_access.return_value = True

        results = executor.execute_remediation(rule, sample_threat)

        assert len(results) == 1
        assert results[0].action_type == "S3_BLOCK_PUBLIC"
        assert results[0].target == "my-public-bucket"
        assert results[0].success is True
        mock_aws_executor.block_s3_public_access.assert_called_once_with("my-public-bucket")

    def test_multiple_remediation_actions(self, executor, mock_aws_executor):
        """Test executing multiple remediation actions for one threat"""
        threat = Threat(
            threat_id="threat-multi",
            rule_id="rule-multi",
            severity=10,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Critical security issue",
            evidence=[
                {"instance_id": "i-0123456789abcdef", "bucket_name": "bad-bucket"}
            ]
        )

        rule = {
            "rule_id": "rule-multi",
            "rule_type": "critical",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {"type": "EC2_STOP", "enabled": True, "parameters": {"region": "us-east-1"}},
                    {"type": "S3_BLOCK_PUBLIC", "enabled": True}
                ]
            }
        }

        mock_aws_executor.stop_ec2_instance.return_value = True
        mock_aws_executor.block_s3_public_access.return_value = True

        results = executor.execute_remediation(rule, threat)

        assert len(results) == 2
        assert results[0].action_type == "EC2_STOP"
        assert results[1].action_type == "S3_BLOCK_PUBLIC"
        assert all(r.success for r in results)

    def test_disabled_actions_skipped(self, executor, mock_aws_executor, sample_threat):
        """Test that disabled remediation actions are skipped"""
        rule = {
            "rule_id": "rule-1",
            "rule_type": "public_bucket",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "S3_BLOCK_PUBLIC",
                        "enabled": False  # Disabled
                    }
                ]
            }
        }

        results = executor.execute_remediation(rule, sample_threat)

        assert results == []
        mock_aws_executor.block_s3_public_access.assert_not_called()

    def test_failed_action_captured(self, executor, mock_aws_executor):
        """Test that failed remediation is properly captured"""
        threat = Threat(
            threat_id="threat-fail",
            rule_id="rule-fail",
            severity=8,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Public bucket",
            evidence=[{"bucket_name": "invalid-bucket-!!!"}]
        )

        rule = {
            "rule_id": "rule-fail",
            "rule_type": "public_bucket",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {"type": "S3_BLOCK_PUBLIC", "enabled": True}
                ]
            }
        }

        mock_aws_executor.block_s3_public_access.return_value = False

        results = executor.execute_remediation(rule, threat)

        assert len(results) == 1
        assert results[0].success is False

    def test_missing_target_in_evidence(self, executor):
        """Test handling when target cannot be extracted from evidence"""
        threat = Threat(
            threat_id="threat-nomatch",
            rule_id="rule-nomatch",
            severity=5,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Unknown threat",
            evidence=[]  # No evidence
        )

        rule = {
            "rule_id": "rule-nomatch",
            "rule_type": "unknown",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {"type": "S3_BLOCK_PUBLIC", "enabled": True}
                ]
            }
        }

        results = executor.execute_remediation(rule, threat)

        assert len(results) == 1
        assert results[0].success is False
        assert "Could not extract" in results[0].message


class TestRemediationAuditRepository:
    """Test RemediationAuditRepository"""

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_table
            repo = RemediationAuditRepository('remediation-table')
            return repo

    def test_log_remediation_creation(self, repository, mock_table):
        """Test logging a remediation action"""
        mock_table.put_item = MagicMock()

        log = repository.log_remediation(
            threat_id="threat-1",
            rule_id="rule-1",
            action_type="S3_BLOCK_PUBLIC",
            target="my-bucket",
            success=True,
            message="Successfully blocked public access"
        )

        assert log.threat_id == "threat-1"
        assert log.rule_id == "rule-1"
        assert log.action_type == "S3_BLOCK_PUBLIC"
        assert log.target == "my-bucket"
        assert log.success is True
        mock_table.put_item.assert_called_once()

    def test_log_remediation_with_parameters(self, repository, mock_table):
        """Test logging remediation with additional parameters"""
        mock_table.put_item = MagicMock()

        params = {"region": "us-east-1", "instance_type": "t2.micro"}
        log = repository.log_remediation(
            threat_id="threat-2",
            rule_id="rule-2",
            action_type="EC2_STOP",
            target="i-1234567890abcdef0",
            success=True,
            message="Stopped instance",
            parameters=params
        )

        assert log.parameters == params

    def test_get_remediation_log(self, repository, mock_table):
        """Test retrieving a remediation log"""
        mock_table.get_item.return_value = {
            "Item": {
                "remediation_id": "rem-1",
                "threat_id": "threat-1",
                "rule_id": "rule-1",
                "action_type": "S3_BLOCK_PUBLIC",
                "target": "my-bucket",
                "success": True,
                "message": "Blocked",
                "timestamp": "2026-05-23T12:00:00Z"
            }
        }

        log = repository.get_remediation_log("rem-1")

        assert log.remediation_id == "rem-1"
        assert log.action_type == "S3_BLOCK_PUBLIC"

    def test_list_remediation_logs(self, repository, mock_table):
        """Test listing remediation logs"""
        mock_table.scan.return_value = {
            "Items": [
                {
                    "remediation_id": "rem-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-1",
                    "action_type": "S3_BLOCK_PUBLIC",
                    "target": "bucket-1",
                    "success": True,
                    "message": "Blocked",
                    "timestamp": "2026-05-23T12:00:00Z"
                },
                {
                    "remediation_id": "rem-2",
                    "threat_id": "threat-2",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-123",
                    "success": False,
                    "message": "Failed",
                    "timestamp": "2026-05-23T12:05:00Z"
                }
            ]
        }

        logs = repository.list_remediation_logs(rule_id="rule-1")

        assert len(logs) == 2
        assert logs[0].action_type == "S3_BLOCK_PUBLIC"
        assert logs[1].success is False

    def test_get_remediation_summary(self, repository, mock_table):
        """Test getting remediation summary"""
        mock_table.scan.return_value = {
            "Items": [
                {
                    "remediation_id": "rem-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-1",
                    "action_type": "S3_BLOCK_PUBLIC",
                    "target": "bucket-1",
                    "success": True,
                    "message": "Success",
                    "timestamp": "2026-05-23T12:00:00Z"
                },
                {
                    "remediation_id": "rem-2",
                    "threat_id": "threat-2",
                    "rule_id": "rule-1",
                    "action_type": "S3_BLOCK_PUBLIC",
                    "target": "bucket-2",
                    "success": True,
                    "message": "Success",
                    "timestamp": "2026-05-23T12:05:00Z"
                },
                {
                    "remediation_id": "rem-3",
                    "threat_id": "threat-3",
                    "rule_id": "rule-1",
                    "action_type": "EC2_STOP",
                    "target": "i-123",
                    "success": False,
                    "message": "Failed",
                    "timestamp": "2026-05-23T12:10:00Z"
                }
            ]
        }

        summary = repository.get_remediation_summary("rule-1")

        assert summary["rule_id"] == "rule-1"
        assert summary["total_remediations"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == pytest.approx(2/3)
        assert summary["action_counts"]["S3_BLOCK_PUBLIC"] == 2
        assert summary["action_counts"]["EC2_STOP"] == 1

    def test_count_successful_remediations(self, repository, mock_table):
        """Test counting successful remediations"""
        mock_table.scan.return_value = {
            "Items": [
                {
                    "remediation_id": "rem-1",
                    "threat_id": "threat-1",
                    "rule_id": "rule-1",
                    "action_type": "S3_BLOCK_PUBLIC",
                    "target": "bucket",
                    "success": True,
                    "message": "Success",
                    "timestamp": "2026-05-23T12:00:00Z"
                },
                {
                    "remediation_id": "rem-2",
                    "threat_id": "threat-2",
                    "rule_id": "rule-1",
                    "action_type": "S3_BLOCK_PUBLIC",
                    "target": "bucket2",
                    "success": False,
                    "message": "Failed",
                    "timestamp": "2026-05-23T12:05:00Z"
                }
            ]
        }

        count = repository.count_successful_remediations("rule-1")

        assert count == 1
