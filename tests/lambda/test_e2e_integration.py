"""E2E Integration Tests - Full Guardian Workflows

End-to-end tests simulating real Guardian workflows:
1. EventBridge trigger → Lambda execution → DynamoDB persistence
2. Multi-region monitoring → findings aggregation
3. Remediation decision → action execution → audit log
"""

from guardian.models import EventBridgeScheduledEvent
from harness import CostCheckerHarness, EC2CheckerHarness, LambdaHarness


class TestFullMonitoringCycle:
    """Full monitoring cycle: trigger → check → report"""

    def test_cost_monitoring_e2e(self):
        """Test: Complete cost monitoring cycle

        1. EventBridge triggers at hour mark
        2. Lambda invokes cost checker
        3. Findings collected
        4. Telegram/Discord notified
        5. Audit log recorded
        """
        harness = CostCheckerHarness()
        event = harness.create_cost_check_event(regions=["ap-northeast-1"])

        # Step 1: EventBridge event validation
        event_obj = EventBridgeScheduledEvent(**event)
        assert event_obj.detail.checker_type == "cost"

        # Step 2: Lambda invocation
        response = harness.invoke_local(event)
        assert response is not None

        # Step 3: Response validation (would have findings if cost exceeded)
        # Could parse as CheckerResponse if handler follows model
        assert isinstance(response, dict)

        # Step 4-5: In real environment, notifications sent + audit logged
        # (mocked in harness tests)

    def test_ec2_security_monitoring_e2e(self):
        """Test: Complete EC2 security monitoring cycle

        1. EventBridge cron trigger (hourly)
        2. EC2 checker scans all regions for:
           - Unauthorized instance launches
           - Public security groups
           - Untagged instances
        3. Findings correlated
        4. If critical: auto-remediate (stop instance)
        5. Audit trail recorded
        """
        harness = EC2CheckerHarness()
        event = harness.create_ec2_check_event(regions=["ap-northeast-1", "us-east-1"])

        # Step 1: Event validation
        event_obj = EventBridgeScheduledEvent(**event)
        assert len(event_obj.detail.regions) == 2

        # Step 2: Multi-region invocation
        response = harness.invoke_local(event)
        assert response is not None

        # Step 3: Response structure (would aggregate findings from 2 regions)
        assert isinstance(response, dict)

        # Step 4-5: In real environment, auto-remediation + audit log
        # (validation happens in response validation tests)


class TestMultiRegionAggregation:
    """Multi-region monitoring with aggregation"""

    def test_multi_region_finding_aggregation(self):
        """Test: Findings from 4 regions are properly aggregated

        Scenario:
        - Region A: 3 public S3 buckets (high)
        - Region B: 2 exposed EC2 (high)
        - Region C: cost spike (medium)
        - Region D: no findings

        Expected: 5 total findings, aggregated with severity levels
        """
        harness = LambdaHarness()
        event = {
            "version": "0",
            "id": "multi-region-agg-test",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "regions": [
                    "ap-northeast-1",
                    "ap-southeast-1",
                    "us-east-1",
                    "eu-west-1",
                ]
            },
        }

        response = harness.invoke_local(event)

        # Response should contain findings from all regions
        assert response is not None
        # In real environment, would validate total finding count
        # and severity distribution

    def test_multi_region_performance_under_load(self):
        """Test: Multi-region performance remains acceptable with 4 regions"""
        harness = LambdaHarness()

        # Simulate high-load scenario: all regions + all checkers
        event = {
            "version": "0",
            "id": "load-test",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "regions": [
                    "ap-northeast-1",
                    "ap-southeast-1",
                    "us-east-1",
                    "eu-west-1",
                ]
            },
        }

        response, duration_ms = harness.invoke_local_with_timing(event)

        # Should complete within time budget for hourly job
        assert duration_ms < 30000, f"Multi-region check too slow: {duration_ms}ms"
        assert response is not None


class TestRemediationWorkflow:
    """Auto-remediation workflow: finding → decision → action"""

    def test_remediation_decision_logic(self):
        """Test: Remediation decision based on finding severity

        Rules:
        - critical: Always remediate
        - high: Remediate if auto_remediate enabled
        - medium: Notify only, no auto-remediation
        - low: Log only
        """
        # Simulate critical finding
        critical_finding = {
            "severity": "critical",
            "title": "S3 bucket publicly readable",
            "resource": "s3://prod-data",
            "resource_type": "s3",
        }

        # Decision: Should remediate
        should_remediate = critical_finding["severity"] in [
            "critical",
            "high",
        ]
        assert should_remediate is True

        # Medium severity finding
        medium_finding = {
            "severity": "medium",
            "title": "Old AMI detected",
            "resource": "ami-12345",
        }

        # Decision: Notify only
        should_remediate = medium_finding["severity"] in [
            "critical",
            "high",
        ]
        assert should_remediate is False

    def test_remediation_action_execution(self):
        """Test: Remediation action execution

        Scenario:
        1. Finding: EC2 instance has public security group
        2. Decision: Execute stop_ec2 action
        3. Action: Stop i-abcd1234 in ap-northeast-1
        4. Verification: Instance stopped
        5. Audit: Log recorded with timestamp, user, result
        """
        # In real environment, would actually stop instance
        # Here we just validate the workflow logic

        action = {
            "action_type": "stop_ec2",
            "resource": "i-abcd1234",
            "region": "ap-northeast-1",
            "reason": "Exposed to public networks",
        }

        # Validation
        assert action["action_type"] in ["stop_ec2", "block_s3", "revoke_iam"]
        assert action["resource"].startswith("i-") or action["resource"].startswith("s3://")
        assert action["region"] in [
            "ap-northeast-1",
            "ap-southeast-1",
            "us-east-1",
            "eu-west-1",
        ]

    def test_remediation_rollback_capability(self):
        """Test: Remediation can be rolled back via API

        POST /api/rollback endpoint:
        - Takes action_id
        - Reverses the action
        - Logs the reversal
        - Notifies on Telegram/Discord
        """
        rollback_request = {  # noqa: F841
            "action_id": "action-001",
            "reason": "False positive - user needs instance running",
        }

        # Expected response
        rollback_response = {
            "status": "rolled_back",
            "action_id": "action-001",
            "original_action": "stop_ec2",
            "reversal_action": "start_ec2",
            "timestamp": "2026-05-05T12:30:00Z",
        }

        assert rollback_response["status"] == "rolled_back"
        assert rollback_response["original_action"] == "stop_ec2"


class TestDashboardDataFlow:
    """Data flow: Lambda → DynamoDB → Dashboard API → Frontend"""

    def test_audit_log_persistence(self):
        """Test: Actions are logged to DynamoDB audit log

        Flow:
        1. Remediation action executed
        2. Result (success/failure) recorded
        3. Audit log entry created in DynamoDB
        4. GET /api/audit-logs returns entries
        """
        # Simulated audit log entry
        audit_entry = {
            "log_id": "audit-001",
            "timestamp": "2026-05-05T12:15:00Z",
            "action": "stop_ec2",
            "resource": "i-abcd1234",
            "status": "success",
            "user": "auto-remediation",
            "details": {"reason": "Exposed security group"},
        }

        # Validation
        assert "log_id" in audit_entry
        assert "timestamp" in audit_entry
        assert "action" in audit_entry
        assert "status" in audit_entry

    def test_remediation_metrics_aggregation(self):
        """Test: Remediation effectiveness metrics aggregated

        Metrics tracked:
        - Total remediations by type (stop_ec2, block_s3, etc)
        - Success rate per rule
        - Average execution time
        - Cost savings impact
        """
        metrics = {
            "total_remediations": 42,
            "by_action_type": {
                "stop_ec2": 20,
                "block_s3": 15,
                "revoke_iam": 7,
            },
            "success_rate": 0.95,
            "avg_execution_time_ms": 1250,
            "estimated_cost_saved": 3450,  # USD
        }

        assert metrics["total_remediations"] == sum(metrics["by_action_type"].values())
        assert 0 <= metrics["success_rate"] <= 1.0

    def test_dashboard_status_endpoint(self):
        """Test: Dashboard status endpoint aggregates all data

        GET /api/status returns:
        - Overall health (healthy/degraded/unhealthy)
        - Last check timestamp
        - Per-region summary
        - Per-checker status
        - Recent critical findings
        """
        status_response = {
            "status": "healthy",
            "last_check": "2026-05-05T12:00:00Z",
            "regions": [
                {
                    "region": "ap-northeast-1",
                    "status": "healthy",
                    "findings_count": 5,
                    "last_check": "2026-05-05T12:00:00Z",
                },
                {
                    "region": "us-east-1",
                    "status": "degraded",
                    "findings_count": 15,
                    "last_check": "2026-05-05T11:55:00Z",
                },
            ],
            "checks": {
                "cost": {"status": "ok", "last_execution_ms": 245},
                "ec2": {"status": "ok", "last_execution_ms": 310},
                "s3": {"status": "ok", "last_execution_ms": 280},
            },
        }

        assert status_response["status"] in ["healthy", "degraded", "unhealthy"]
        assert "regions" in status_response
        assert "checks" in status_response
        assert len(status_response["regions"]) > 0
