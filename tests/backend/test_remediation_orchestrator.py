"""Sprint 37 Phase 4: Remediation Orchestrator Tests

Tests for remediation orchestration with safety checks and approval workflows.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.responders.remediation_orchestrator import (
    RemediationOrchestrator, OrchestrationResult, RemediationImpact,
    RemediationApprovalStatus
)
from guardian.detectors.anomaly_detector import Threat


class TestRemediationOrchestrator:
    """Test RemediationOrchestrator"""

    @pytest.fixture
    def mock_aws_executor(self):
        """Create mock AWSActionExecutor"""
        return MagicMock()

    @pytest.fixture
    def orchestrator(self, mock_aws_executor):
        """Create orchestrator with mocked executor"""
        return RemediationOrchestrator(aws_executor=mock_aws_executor)

    @pytest.fixture
    def sample_threat(self):
        """Create sample threat"""
        return Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=8,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Security threat detected",
            evidence=[
                {
                    "instance_id": "i-1234567890abcdef0",
                    "region": "us-east-1"
                }
            ]
        )

    # Impact Assessment Tests

    def test_assess_action_impact_critical(self, orchestrator):
        """Test impact assessment for critical actions"""
        impact = orchestrator._assess_action_impact('LAMBDA_DISABLE')
        assert impact == RemediationImpact.CRITICAL

        impact = orchestrator._assess_action_impact('LAMBDA_LAYER_REMOVE')
        assert impact == RemediationImpact.CRITICAL

        impact = orchestrator._assess_action_impact('VPC_ISOLATE')
        assert impact == RemediationImpact.CRITICAL

    def test_assess_action_impact_high(self, orchestrator):
        """Test impact assessment for high impact actions"""
        impact = orchestrator._assess_action_impact('EC2_STOP')
        assert impact == RemediationImpact.HIGH

        impact = orchestrator._assess_action_impact('RDS_DISABLE_PUBLIC')
        assert impact == RemediationImpact.HIGH

        impact = orchestrator._assess_action_impact('ELB_DEREGISTER')
        assert impact == RemediationImpact.HIGH

    def test_assess_action_impact_medium(self, orchestrator):
        """Test impact assessment for medium impact actions"""
        impact = orchestrator._assess_action_impact('LAMBDA_CONCURRENCY_LIMIT')
        assert impact == RemediationImpact.MEDIUM

        impact = orchestrator._assess_action_impact('RDS_BACKUP_ENABLE')
        assert impact == RemediationImpact.MEDIUM

        impact = orchestrator._assess_action_impact('S3_BLOCK_PUBLIC')
        assert impact == RemediationImpact.MEDIUM

    def test_assess_total_impact_mixed(self, orchestrator):
        """Test total impact assessment with mixed actions"""
        actions = [
            {"type": "S3_BLOCK_PUBLIC"},  # MEDIUM
            {"type": "EC2_STOP"}  # HIGH
        ]

        impact = orchestrator._assess_total_impact(actions)
        assert impact == RemediationImpact.HIGH

    def test_assess_total_impact_with_critical(self, orchestrator):
        """Test total impact with critical action"""
        actions = [
            {"type": "S3_BLOCK_PUBLIC"},  # MEDIUM
            {"type": "EC2_STOP"},  # HIGH
            {"type": "LAMBDA_DISABLE"}  # CRITICAL
        ]

        impact = orchestrator._assess_total_impact(actions)
        assert impact == RemediationImpact.CRITICAL

    # Approval Status Tests

    def test_determine_approval_status_auto_approved(self, orchestrator):
        """Test auto-approval for low/medium impact"""
        status = orchestrator._determine_approval_status(
            RemediationImpact.MEDIUM, False, None
        )
        assert status == RemediationApprovalStatus.AUTO_APPROVED

    def test_determine_approval_status_pending_high_impact(self, orchestrator):
        """Test approval pending for high impact"""
        status = orchestrator._determine_approval_status(
            RemediationImpact.HIGH, False, None
        )
        assert status == RemediationApprovalStatus.PENDING

    def test_determine_approval_status_pending_critical(self, orchestrator):
        """Test approval pending for critical impact"""
        status = orchestrator._determine_approval_status(
            RemediationImpact.CRITICAL, False, None
        )
        assert status == RemediationApprovalStatus.PENDING

    def test_determine_approval_status_approved(self, orchestrator):
        """Test approved status when approval is provided"""
        status = orchestrator._determine_approval_status(
            RemediationImpact.CRITICAL, True, "user-123"
        )
        assert status == RemediationApprovalStatus.APPROVED

    # Execution Tests

    def test_execute_remediation_disabled(self, orchestrator, sample_threat):
        """Test that disabled remediation is not executed"""
        rule = {
            "rule_id": "rule-1",
            "action": {
                "auto_remediate": False  # Disabled
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.total_actions == 0
        assert result.executed_actions == 0
        assert result.failed_actions == 0

    def test_execute_remediation_no_actions(self, orchestrator, sample_threat):
        """Test that rules without remediation_actions return empty"""
        rule = {
            "rule_id": "rule-1",
            "action": {
                "auto_remediate": True,
                "remediation_actions": []
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.total_actions == 0
        assert result.executed_actions == 0

    def test_execute_remediation_single_action(self, orchestrator, mock_aws_executor, sample_threat):
        """Test execution of single remediation action"""
        mock_aws_executor.stop_ec2_instance.return_value = True

        rule = {
            "rule_id": "rule-1",
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

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.total_actions == 1
        assert result.executed_actions == 1
        assert result.failed_actions == 0

    def test_execute_remediation_multiple_actions(self, orchestrator, mock_aws_executor):
        """Test execution of multiple remediation actions"""
        mock_aws_executor.stop_ec2_instance.return_value = True
        mock_aws_executor.block_s3_public_access.return_value = True

        threat = Threat(
            threat_id="threat-multi",
            rule_id="rule-multi",
            severity=8,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Multi-service threat",
            evidence=[
                {
                    "instance_id": "i-1234567890abcdef0",
                    "bucket_name": "my-public-bucket",
                    "region": "us-east-1"
                }
            ]
        )

        rule = {
            "rule_id": "rule-multi",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "EC2_STOP",
                        "enabled": True,
                        "parameters": {"region": "us-east-1"}
                    },
                    {
                        "type": "S3_BLOCK_PUBLIC",
                        "enabled": True
                    }
                ]
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(rule, threat)

        assert result.total_actions == 2
        assert result.executed_actions == 2
        assert result.failed_actions == 0

    def test_execute_remediation_with_disabled_action(self, orchestrator, mock_aws_executor):
        """Test that disabled actions are skipped"""
        mock_aws_executor.block_s3_public_access.return_value = True

        threat = Threat(
            threat_id="threat-mixed",
            rule_id="rule-mixed",
            severity=8,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Mixed threat",
            evidence=[
                {
                    "instance_id": "i-1234567890abcdef0",
                    "bucket_name": "my-public-bucket",
                    "region": "us-east-1"
                }
            ]
        )

        rule = {
            "rule_id": "rule-mixed",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "EC2_STOP",
                        "enabled": False  # Disabled
                    },
                    {
                        "type": "S3_BLOCK_PUBLIC",
                        "enabled": True
                    }
                ]
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(rule, threat)

        assert result.total_actions == 2
        assert result.executed_actions == 1  # Only S3 action
        assert result.failed_actions == 0

    # Dry-Run Tests

    def test_dry_run_remediation(self, orchestrator, sample_threat):
        """Test dry-run execution"""
        rule = {
            "rule_id": "rule-1",
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

        result = orchestrator.execute_remediation_with_orchestration(
            rule, sample_threat, dry_run=True
        )

        assert result.total_actions == 1
        assert result.results[0]['dry_run'] is True
        assert "[DRY-RUN]" in result.results[0]['message']

    # Approval Workflow Tests

    def test_approval_workflow_high_impact(self, orchestrator, mock_aws_executor, sample_threat):
        """Test approval workflow for high impact actions"""
        rule = {
            "rule_id": "rule-1",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "ELB_DEREGISTER",
                        "enabled": True,
                        "parameters": {
                            "load_balancer_arn": "arn:aws:...",
                            "target_id": "i-123"
                        }
                    }
                ]
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(
            rule, sample_threat, approval_required=False
        )

        assert result.approval_status == RemediationApprovalStatus.PENDING

    def test_approval_workflow_approved(self, orchestrator, mock_aws_executor, sample_threat):
        """Test approval workflow with user approval"""
        rule = {
            "rule_id": "rule-1",
            "action": {
                "auto_remediate": True,
                "remediation_actions": [
                    {
                        "type": "LAMBDA_DISABLE",
                        "enabled": True,
                        "parameters": {
                            "function_name": "my-function",
                            "region": "us-east-1"
                        }
                    }
                ]
            }
        }

        result = orchestrator.execute_remediation_with_orchestration(
            rule, sample_threat, approval_required=True, approved_by="user-123"
        )

        assert result.approval_status == RemediationApprovalStatus.APPROVED

    # Integration Tests

    def test_extract_target_from_parameters(self, orchestrator):
        """Test target extraction from action parameters"""
        threat = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=5,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Test",
            evidence=[]
        )

        action = {
            "parameters": {
                "function_name": "my-function"
            }
        }

        target = orchestrator._extract_target(action, threat)
        assert target == "my-function"

    def test_extract_target_from_evidence(self, orchestrator):
        """Test target extraction from threat evidence"""
        threat = Threat(
            threat_id="threat-1",
            rule_id="rule-1",
            severity=5,
            account_id="test-account",
            timestamp=datetime.now(timezone.utc),
            message="Test",
            evidence=[
                {"instance_id": "i-abcdef"}
            ]
        )

        action = {
            "parameters": {}
        }

        target = orchestrator._extract_target(action, threat)
        assert target == "i-abcdef"

    def test_execution_result_contains_timestamp(self, orchestrator, mock_aws_executor, sample_threat):
        """Test that execution result contains valid timestamp"""
        mock_aws_executor.stop_ec2_instance.return_value = True

        rule = {
            "rule_id": "rule-1",
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

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.timestamp is not None
        parsed_ts = datetime.fromisoformat(result.timestamp)
        assert parsed_ts is not None

    def test_execution_result_contains_timing(self, orchestrator, mock_aws_executor, sample_threat):
        """Test that execution result includes execution time"""
        mock_aws_executor.stop_ec2_instance.return_value = True

        rule = {
            "rule_id": "rule-1",
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

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.execution_time_seconds >= 0
        assert isinstance(result.execution_time_seconds, float)

    def test_failed_actions_tracked(self, orchestrator, mock_aws_executor, sample_threat):
        """Test that failed actions are properly tracked"""
        mock_aws_executor.stop_ec2_instance.return_value = False

        rule = {
            "rule_id": "rule-1",
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

        result = orchestrator.execute_remediation_with_orchestration(rule, sample_threat)

        assert result.total_actions == 1
        assert result.executed_actions == 0
        assert result.failed_actions == 1
