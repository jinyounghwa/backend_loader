"""Pytest configuration and fixtures for Lambda integration tests."""

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

# SAM local invoke 환경 설정
os.environ["AWS_REGION"] = "ap-northeast-1"
os.environ["AWS_ENV"] = "localstack"
os.environ["AWS_ACCOUNT_ID"] = "123456789012"


@pytest.fixture
def lambda_event_base() -> Dict[str, Any]:
    """기본 Lambda event (EventBridge scheduled event) fixture."""
    return {
        "version": "0",
        "id": "12345678-1234-1234-1234-123456789012",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "2026-05-05T12:00:00Z",
        "region": "ap-northeast-1",
        "resources": [],
        "detail": {},
    }


@pytest.fixture
def eventbridge_cost_event(lambda_event_base) -> Dict[str, Any]:
    """Cost check EventBridge event."""
    event = lambda_event_base.copy()
    event["id"] = "cost-event-001"
    event["detail"] = {
        "checker_type": "cost",
        "regions": ["ap-northeast-1", "us-east-1"],
    }
    return event


@pytest.fixture
def eventbridge_ec2_event(lambda_event_base) -> Dict[str, Any]:
    """EC2 check EventBridge event."""
    event = lambda_event_base.copy()
    event["id"] = "ec2-event-001"
    event["detail"] = {
        "checker_type": "ec2",
        "regions": ["ap-northeast-1"],
    }
    return event


@pytest.fixture
def eventbridge_s3_event(lambda_event_base) -> Dict[str, Any]:
    """S3 check EventBridge event."""
    event = lambda_event_base.copy()
    event["id"] = "s3-event-001"
    event["detail"] = {
        "checker_type": "s3",
        "regions": ["ap-northeast-1"],
    }
    return event


@pytest.fixture
def eventbridge_multi_region_event(lambda_event_base) -> Dict[str, Any]:
    """Multi-region check EventBridge event."""
    event = lambda_event_base.copy()
    event["id"] = "multi-region-event-001"
    event["detail"] = {
        "regions": ["ap-northeast-1", "ap-southeast-1", "us-east-1", "eu-west-1"],
    }
    return event


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for LocalStack."""
    return {
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "AWS_DEFAULT_REGION": "ap-northeast-1",
        "AWS_ENV": "localstack",
    }


@pytest.fixture
def load_event_fixture():
    """Load event fixture from JSON file."""

    def _load(filename: str) -> Dict[str, Any]:
        fixture_path = Path(__file__).parent / "fixtures" / "events" / filename
        if not fixture_path.exists():
            raise FileNotFoundError(f"Event fixture not found: {fixture_path}")
        with open(fixture_path) as f:
            return json.load(f)

    return _load


@pytest.fixture(scope="session")
def sam_template_exists():
    """Verify SAM template exists before running tests."""
    project_root = Path(__file__).parent.parent.parent
    sam_file = project_root / "sam.yaml"

    if not sam_file.exists():
        pytest.skip("SAM template not found - skipping Lambda harness tests")

    return True
