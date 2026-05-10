"""Shared test fixtures for AWS Guardian test suite."""

import os
import sys
from unittest.mock import Mock

import pytest

# Ensure lambda package is importable from all tests
_LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "lambda")
if _LAMBDA_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_LAMBDA_DIR))


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def mock_storage():
    return Mock()


@pytest.fixture
def aws_env(monkeypatch):
    """Set up LocalStack environment for tests."""
    monkeypatch.setenv("AWS_ENV", "localstack")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "aws-guardian-events")


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Reset Config and AWSClientProvider caches between tests."""
    from guardian.aws_client_provider import AWSClientProvider
    from guardian.config import Config
    yield
    Config.reset_cache()
    AWSClientProvider.clear_cache()


@pytest.fixture
def mock_telegram():
    t = Mock()
    t.send_alert = Mock(return_value=True)
    t.send_cost_alert = Mock(return_value=True)
    t.send_ec2_alert = Mock(return_value=True)
    t.send_s3_alert = Mock(return_value=True)
    t.send_summary = Mock(return_value=True)
    return t


@pytest.fixture
def mock_discord():
    d = Mock()
    d.send_cost_alert = Mock(return_value=True)
    d.send_ec2_alert = Mock(return_value=True)
    d.send_s3_alert = Mock(return_value=True)
    d.send_summary_embed = Mock(return_value=True)
    return d
