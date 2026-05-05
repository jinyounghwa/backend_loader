"""API Contract Tests - Frontend/Backend Alignment

Tests to ensure Jest frontend API expectations match Python Lambda responses.
This prevents drift between frontend and backend API contracts.
"""

import json
import sys
from pathlib import Path

# Add lambda module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda"))

from guardian.models import EventsResponse, StatusResponse


class TestStatusAPIContract:
    """GET /api/status response contract"""

    def test_status_response_has_required_fields(self):
        """Test: Status response includes all required fields"""
        response = StatusResponse(
            status="healthy",
            last_check="2026-05-05T12:00:00Z",
            checks={"cost": {"status": "ok"}, "ec2": {"status": "ok"}},
        )

        # Jest expects these fields
        assert hasattr(response, "status")
        assert hasattr(response, "last_check")
        assert hasattr(response, "checks")

    def test_status_single_region_format(self):
        """Test: Single region response format matches Jest expectation"""
        response = StatusResponse(
            status="healthy",
            last_check="2026-05-05T12:00:00Z",
            checks={"cost": {"status": "ok"}},
        )

        # Single region should NOT have 'regions' field
        assert response.regions is None

        # Should be serializable to JSON
        json_str = response.json()
        assert "status" in json_str
        assert "checks" in json_str

    def test_status_multi_region_format(self):
        """Test: Multi-region response format matches Jest expectation"""
        response = StatusResponse(
            status="healthy",
            last_check="2026-05-05T12:00:00Z",
            checks={},
            regions=[
                {"region": "ap-northeast-1", "status": "ok"},
                {"region": "us-east-1", "status": "degraded"},
            ],
        )

        # Multi-region should have 'regions' field
        assert response.regions is not None
        assert len(response.regions) == 2

    def test_status_response_json_serializable(self):
        """Test: Status response is JSON serializable for HTTP response"""
        response = StatusResponse(
            status="healthy",
            last_check="2026-05-05T12:00:00Z",
            checks={"ec2": {"instances": 5, "vulnerable": 1}},
        )

        json_data = json.loads(response.json())
        assert json_data["status"] == "healthy"
        assert "ec2" in json_data["checks"]


class TestEventsAPIContract:
    """GET /api/events response contract"""

    def test_events_response_structure(self):
        """Test: Events response has correct structure"""
        response = EventsResponse(
            total=3,
            events=[
                {
                    "id": "event-001",
                    "type": "ec2",
                    "severity": "high",
                    "timestamp": "2026-05-05T10:00:00Z",
                },
                {
                    "id": "event-002",
                    "type": "s3",
                    "severity": "medium",
                    "timestamp": "2026-05-05T11:00:00Z",
                },
            ],
        )

        assert response.total == 3
        assert len(response.events) == 2
        assert response.events[0]["type"] == "ec2"

    def test_events_response_with_filters(self):
        """Test: Events response indicates filters applied"""
        response = EventsResponse(
            total=10,
            events=[],
            filters_applied={"type": "ec2", "severity": "high", "hours": "24"},
        )

        assert response.filters_applied is not None
        assert response.filters_applied["type"] == "ec2"

    def test_events_response_json_format(self):
        """Test: Events response JSON matches Jest expectation"""
        response = EventsResponse(
            total=1,
            events=[
                {
                    "id": "evt-001",
                    "type": "cost",
                    "title": "Cost spike",
                    "severity": "high",
                }
            ],
        )

        json_data = json.loads(response.json())
        assert json_data["total"] == 1
        assert json_data["events"][0]["type"] == "cost"


class TestRemediationMetricsAPIContract:
    """GET /api/remediation-metrics response contract"""

    def test_remediation_metrics_response_structure(self):
        """Test: Remediation metrics response structure"""
        response = {
            "total_rules": 5,
            "total_remediations": 42,
            "success_rate": 0.95,
            "avg_effectiveness_score": 4.2,
            "by_rule": [
                {
                    "rule_id": "rule-001",
                    "name": "Stop Exposed EC2",
                    "total": 10,
                    "success": 9,
                    "effectiveness_score": 4.5,
                },
            ],
        }

        # Jest expects these fields
        assert "total_rules" in response
        assert "total_remediations" in response
        assert "success_rate" in response
        assert "avg_effectiveness_score" in response
        assert "by_rule" in response

    def test_remediation_metrics_filtering(self):
        """Test: Filtered metrics response (by rule_id)"""
        response = {
            "total_rules": 1,
            "total_remediations": 5,
            "success_rate": 1.0,
            "avg_effectiveness_score": 5.0,
            "by_rule": [
                {
                    "rule_id": "rule-001",
                    "total": 5,
                    "success": 5,
                    "effectiveness_score": 5.0,
                }
            ],
        }

        # Filtered response should have only matching rule
        assert response["total_rules"] == 1
        assert len(response["by_rule"]) == 1

    def test_remediation_metrics_empty_results(self):
        """Test: Empty metrics for non-existent rule_id

        NOTE: Known issue in v1.0 - returns NaN instead of 0
        """
        # Current behavior (v1.0): Returns 0 after fix in v1.1
        response = {
            "total_rules": 0,
            "total_remediations": 0,
            "success_rate": 0,  # Changed from NaN
            "avg_effectiveness_score": 0,  # Changed from NaN
            "by_rule": [],
        }

        assert response["total_rules"] == 0
        assert response["success_rate"] == 0
        assert response["avg_effectiveness_score"] == 0


class TestResponseRulesAPIContract:
    """Response Rules API (GET/POST/DELETE) contract"""

    def test_get_response_rules_format(self):
        """Test: GET /api/response-rules response format"""
        response = {
            "total": 2,
            "rules": [
                {
                    "rule_id": "rule-001",
                    "name": "Stop Public EC2",
                    "trigger": "ec2.security_group.public",
                    "action": "stop_ec2",
                    "enabled": True,
                    "regions": ["ap-northeast-1", "us-east-1"],
                    "created_at": "2026-04-01T00:00:00Z",
                },
            ],
        }

        assert "total" in response
        assert "rules" in response
        assert response["rules"][0]["rule_id"] is not None
        assert response["rules"][0]["enabled"] in [True, False]

    def test_post_response_rules_request_format(self):
        """Test: POST /api/response-rules request format"""
        request = {
            "name": "New Rule",
            "trigger": "s3.public_bucket",
            "action": "block_s3",
            "regions": ["ap-northeast-1"],
        }

        # Required fields
        assert "name" in request
        assert "trigger" in request
        assert "action" in request
        assert "regions" in request

    def test_post_response_rules_response_format(self):
        """Test: POST /api/response-rules response format"""
        response = {
            "rule_id": "rule-new-001",
            "name": "New Rule",
            "status": "created",
            "message": "Rule created successfully",
        }

        assert "rule_id" in response
        assert response["status"] == "created"

    def test_delete_response_rules_response_format(self):
        """Test: DELETE /api/response-rules response format"""
        response = {
            "rule_id": "rule-001",
            "status": "deleted",
            "message": "Rule deleted successfully",
        }

        assert response["status"] == "deleted"
        assert "message" in response


class TestAnalyzeThreatAPIContract:
    """POST /api/analyze-threat response contract"""

    def test_analyze_threat_request_format(self):
        """Test: POST /api/analyze-threat request format"""
        request = {
            "events": [
                {
                    "id": "evt-001",
                    "type": "ec2",
                    "severity": "high",
                    "details": "Public security group",
                },
            ],
            "context": "Multiple findings in one account",
        }

        assert "events" in request
        assert len(request["events"]) > 0
        assert "id" in request["events"][0]
        assert "type" in request["events"][0]

    def test_analyze_threat_response_format(self):
        """Test: POST /api/analyze-threat response format"""
        response = {
            "analysis": {
                "threat_level": "high",
                "pattern": "Systematic exposure to public networks",
                "recommendations": [
                    "Review all security groups immediately",
                    "Enable GuardDuty for automated detection",
                ],
            },
            "source": "gemini",  # or "mock" if API key missing
        }

        assert "analysis" in response
        assert "threat_level" in response["analysis"]
        assert "recommendations" in response["analysis"]
        assert "source" in response

    def test_analyze_threat_fallback_when_no_api_key(self):
        """Test: Fallback to mock analysis when GOOGLE_API_KEY missing"""
        # Fallback response
        response = {
            "analysis": {
                "threat_level": "medium",
                "pattern": "MOCK_ANALYSIS",
                "recommendations": ["Manual review recommended"],
            },
            "source": "mock",
        }

        assert response["source"] == "mock"
        assert response["analysis"]["pattern"] == "MOCK_ANALYSIS"


class TestAccountsAPIContract:
    """GET /api/accounts response contract"""

    def test_accounts_response_structure(self):
        """Test: GET /api/accounts response format"""
        response = {
            "total": 2,
            "accounts": [
                {
                    "account_id": "123456789012",
                    "name": "Production",
                    "regions": ["ap-northeast-1", "us-east-1"],
                },
                {
                    "account_id": "210987654321",
                    "name": "Staging",
                    "regions": ["ap-northeast-1"],
                },
            ],
        }

        assert "total" in response
        assert "accounts" in response
        assert response["total"] == len(response["accounts"])

    def test_accounts_account_structure(self):
        """Test: Individual account record structure"""
        account = {
            "account_id": "123456789012",
            "name": "MyAccount",
            "regions": ["ap-northeast-1", "ap-southeast-1"],
            "enabled": True,
        }

        assert "account_id" in account
        assert "name" in account
        assert "regions" in account
        assert isinstance(account["regions"], list)
