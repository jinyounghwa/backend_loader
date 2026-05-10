"""Event Payload Contract Validation Tests

Tests to ensure EventBridge event format and Lambda response format
remain consistent between Jest (frontend) and Python (backend).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add lambda module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda"))

from guardian.models import (
    AuditLogRecord,
    CheckerResponse,
    EventBridgeScheduledEvent,
    Finding,
    RemediationAction,
    RemediationMetricRecord,
    ResponderInput,
    StatusResponse,
)


class TestEventBridgePayloadContract:
    """EventBridge event format validation"""

    def test_eventbridge_scheduled_event_schema(self, lambda_event_base):
        """Test: EventBridge scheduled event matches schema"""
        event_data = lambda_event_base.copy()
        event_data["detail"] = {"checker_type": "cost", "regions": ["ap-northeast-1"]}

        # Parse with Pydantic model
        event = EventBridgeScheduledEvent(**event_data)

        assert event.version == "0"
        assert event.source == "aws.events"
        assert event.detail.checker_type == "cost"
        assert "ap-northeast-1" in event.detail.regions

    def test_eventbridge_multi_region_event(self, eventbridge_multi_region_event):
        """Test: Multi-region event validation"""
        event = EventBridgeScheduledEvent(**eventbridge_multi_region_event)

        assert len(event.detail.regions) == 4
        assert "ap-northeast-1" in event.detail.regions
        assert "us-east-1" in event.detail.regions

    def test_eventbridge_missing_required_fields(self):
        """Test: Event missing required fields fails validation"""
        incomplete_event = {
            "version": "0",
            "id": "test-id",
            # missing: detail-type, source, account, time, region, detail
        }

        with pytest.raises(ValueError):
            EventBridgeScheduledEvent(**incomplete_event)

    def test_eventbridge_invalid_timestamp(self):
        """Test: Invalid timestamp format caught"""
        event_data = {
            "version": "0",
            "id": "test-id",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "not-a-valid-datetime",  # Invalid
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {},
        }

        with pytest.raises(ValueError):
            EventBridgeScheduledEvent(**event_data)

    def test_eventbridge_default_regions(self):
        """Test: Default region is applied if not specified"""
        event_data = {
            "version": "0",
            "id": "test-id",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {},  # No regions specified
        }

        event = EventBridgeScheduledEvent(**event_data)

        assert event.detail.regions == ["ap-northeast-1"]


class TestCheckerResponseContract:
    """Checker response format validation"""

    def test_checker_response_valid(self):
        """Test: Valid checker response"""
        response = CheckerResponse(
            checker_name="cost",
            findings=[],
            region="ap-northeast-1",
        )

        assert response.checker_name == "cost"
        assert response.status == "success"
        assert len(response.findings) == 0

    def test_checker_response_with_findings(self):
        """Test: Checker response with findings"""
        finding = Finding(
            severity="high",
            title="High cost detected",
            description="Daily cost exceeds threshold",
            resource="aws-account",
            resource_type="account",
            region="ap-northeast-1",
        )

        response = CheckerResponse(
            checker_name="cost",
            findings=[finding],
            region="ap-northeast-1",
        )

        assert len(response.findings) == 1
        assert response.findings[0].severity == "high"

    def test_checker_response_with_error(self):
        """Test: Checker response with error status"""
        response = CheckerResponse(
            checker_name="ec2",
            findings=[],
            region="ap-northeast-1",
            status="error",
            error_message="Failed to call EC2 API",
        )

        assert response.status == "error"
        assert response.error_message is not None

    def test_finding_severity_values(self):
        """Test: Finding severity validation"""
        valid_severities = ["critical", "high", "medium", "low", "info"]

        for severity in valid_severities:
            finding = Finding(
                severity=severity,
                title="Test",
                description="Test finding",
                resource="test-resource",
                resource_type="test",
                region="ap-northeast-1",
            )
            assert finding.severity == severity

    def test_checker_response_timestamp_auto_set(self):
        """Test: CheckerResponse timestamp is auto-set"""
        response = CheckerResponse(
            checker_name="s3",
            region="ap-northeast-1",
        )

        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)


class TestResponderInputContract:
    """Responder (Telegram/Discord) input validation"""

    def test_responder_input_valid(self):
        """Test: Valid responder input"""
        finding = Finding(
            severity="critical",
            title="Security issue",
            description="Public S3 bucket detected",
            resource="s3://my-bucket",
            resource_type="s3",
            region="ap-northeast-1",
        )

        responder_input = ResponderInput(
            findings=[finding],
        )

        assert len(responder_input.findings) == 1
        assert responder_input.findings[0].resource_type == "s3"

    def test_responder_input_with_actions(self):
        """Test: Responder input with remediation actions"""
        action = RemediationAction(
            action_type="block_s3",
            resource="s3://my-bucket",
            region="ap-northeast-1",
            reason="Public bucket detected",
        )

        responder_input = ResponderInput(
            findings=[],
            actions=[action],
        )

        assert len(responder_input.actions) == 1
        assert responder_input.actions[0].auto_remediate is True

    def test_remediation_action_types(self):
        """Test: Valid remediation action types"""
        valid_actions = ["stop_ec2", "block_s3", "revoke_iam", "isolate_vpc"]

        for action_type in valid_actions:
            action = RemediationAction(
                action_type=action_type,
                resource="test-resource",
                region="ap-northeast-1",
                reason="Test",
            )
            assert action.action_type == action_type


class TestDynamoDBRecordContract:
    """DynamoDB record format validation"""

    def test_audit_log_record_valid(self):
        """Test: Valid audit log record"""
        record = AuditLogRecord(
            log_id="log-001",
            action="auto_remediate",
            resource="i-1234567890abcdef0",
            severity="high",
        )

        assert record.log_id == "log-001"
        assert record.action == "auto_remediate"

    def test_remediation_metric_record_valid(self):
        """Test: Valid remediation metric record"""
        record = RemediationMetricRecord(
            metric_id="metric-001",
            rule_id="rule-001",
            action_type="stop_ec2",
            execution_time_ms=1250,
            affected_resources=3,
        )

        assert record.metric_id == "metric-001"
        assert record.execution_time_ms == 1250
        assert record.affected_resources == 3

    def test_remediation_metric_success(self):
        """Test: Successful remediation metric"""
        record = RemediationMetricRecord(
            metric_id="metric-002",
            rule_id="rule-001",
            action_type="block_s3",
            execution_time_ms=800,
            affected_resources=2,
            success=True,
        )

        assert record.success is True
        assert record.error_message is None

    def test_remediation_metric_failure(self):
        """Test: Failed remediation metric"""
        record = RemediationMetricRecord(
            metric_id="metric-003",
            rule_id="rule-001",
            action_type="revoke_iam",
            execution_time_ms=500,
            success=False,
            error_message="AccessDenied: User lacks permission",
        )

        assert record.success is False
        assert record.error_message is not None


class TestAPIResponseContract:
    """API response format validation"""

    def test_status_response_valid(self):
        """Test: Valid status response"""
        response = StatusResponse(
            status="healthy",
            last_check=datetime.now(timezone.utc),
            checks={
                "cost": {"status": "ok"},
                "ec2": {"status": "ok"},
                "s3": {"status": "ok"},
            },
        )

        assert response.status == "healthy"
        assert "cost" in response.checks

    def test_status_response_degraded(self):
        """Test: Degraded status response"""
        response = StatusResponse(
            status="degraded",
            last_check=datetime.now(timezone.utc),
            checks={
                "cost": {"status": "ok"},
                "ec2": {"status": "error", "message": "API throttled"},
            },
        )

        assert response.status == "degraded"

    def test_status_response_multi_region(self):
        """Test: Status response with multi-region data"""
        response = StatusResponse(
            status="healthy",
            last_check=datetime.now(timezone.utc),
            checks={},
            regions=[
                {"region": "ap-northeast-1", "status": "ok"},
                {"region": "us-east-1", "status": "ok"},
                {"region": "eu-west-1", "status": "degraded"},
            ],
        )

        assert response.regions is not None
        assert len(response.regions) == 3
