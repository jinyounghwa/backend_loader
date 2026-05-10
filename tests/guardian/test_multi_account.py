"""Tests for multi-account support in orchestrator."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from guardian.orchestrator import GuardianOrchestrator
from guardian.checkers.base import CheckResult
from guardian.storage.dynamodb import DynamoDBStorage


class AsyncTestCase(unittest.TestCase):
    """Base test case for async tests."""

    def setUp(self):
        """Set up event loop for each test."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop after each test."""
        self.loop.close()

    def async_test(self, coro):
        """Helper to run async functions in tests."""
        return self.loop.run_until_complete(coro)


class TestMultiAccountOrchestrator(AsyncTestCase):
    """Test multi-account support in orchestrator."""

    def setUp(self):
        """Set up orchestrator with mock dependencies."""
        super().setUp()
        self.mock_logger = MagicMock()
        self.mock_storage = MagicMock(spec=DynamoDBStorage)
        self.mock_cost_checker = MagicMock()
        self.mock_ec2_checker = MagicMock()
        self.mock_s3_checker = MagicMock()
        self.mock_telegram = None
        self.mock_discord = None

        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
            telegram_responder=self.mock_telegram,
            discord_responder=self.mock_discord,
        )

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    @patch("guardian.orchestrator.AWSClientProvider.get_async_client")
    def test_get_accounts_async_single_account(self, mock_get_client, mock_is_orgs_enabled):
        """Test _get_accounts_async with single account."""
        mock_is_orgs_enabled.return_value = False

        result = self.async_test(self.orchestrator._get_accounts_async())

        self.assertEqual(result, [])

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    @patch("guardian.orchestrator.AWSClientProvider.get_async_client")
    def test_get_accounts_async_multiple_accounts(self, mock_get_client, mock_is_orgs_enabled):
        """Test _get_accounts_async retrieves multiple accounts from Organizations."""
        mock_is_orgs_enabled.return_value = True
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_paginator = AsyncMock()
        mock_client.get_paginator.return_value = mock_paginator

        async def mock_paginate(*args, **kwargs):
            yield {
                "Accounts": [
                    {
                        "Id": "123456789",
                        "Name": "Production",
                        "Status": "ACTIVE",
                    },
                    {
                        "Id": "987654321",
                        "Name": "Development",
                        "Status": "ACTIVE",
                    },
                ]
            }

        mock_paginator.paginate.return_value = mock_paginate()

        result = self.async_test(self.orchestrator._get_accounts_async())

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["account_id"], "123456789")
        self.assertEqual(result[0]["account_name"], "Production")

    @patch("guardian.orchestrator.AWSClientProvider.assume_role_async")
    def test_assume_role_async_success(self, mock_assume_role):
        """Test successful cross-account role assumption."""
        mock_assume_role.return_value = {
            "account_id": "987654321",
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "aws_session_token": "token123",
            },
        }

        result = self.async_test(AWSClientProvider.assume_role_async("987654321"))

        self.assertIsNotNone(result)
        self.assertEqual(result["account_id"], "987654321")
        self.assertIn("credentials", result)

    @patch("guardian.orchestrator.AWSClientProvider.assume_role_async")
    def test_assume_role_async_failure(self, mock_assume_role):
        """Test role assumption failure handling."""
        mock_assume_role.return_value = None

        result = self.async_test(AWSClientProvider.assume_role_async("invalid-account"))

        self.assertIsNone(result)

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    @patch("guardian.orchestrator.AWSClientProvider.assume_role_async")
    def test_create_account_checkers_async(self, mock_assume_role, mock_is_orgs_enabled):
        """Test creating account-specific checkers with cross-account credentials."""
        credentials = {
            "aws_access_key_id": "AKIA...",
            "aws_secret_access_key": "secret...",
            "aws_session_token": "token...",
        }

        result = self.async_test(
            self.orchestrator._create_account_checkers_async("987654321", credentials)
        )

        self.assertIsNotNone(result)
        self.assertIn("cost", result)

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    @patch("guardian.orchestrator.AWSClientProvider.get_async_client")
    @patch("guardian.orchestrator.AWSClientProvider.assume_role_async")
    def test_run_all_checks_multi_account(
        self, mock_assume_role, mock_get_client, mock_is_orgs_enabled
    ):
        """Test running checks across multiple AWS accounts."""
        mock_is_orgs_enabled.return_value = True
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_paginator = AsyncMock()
        mock_client.get_paginator.return_value = mock_paginator

        async def mock_paginate(*args, **kwargs):
            yield {
                "Accounts": [
                    {"Id": "111111111", "Name": "Account1", "Status": "ACTIVE"},
                    {"Id": "222222222", "Name": "Account2", "Status": "ACTIVE"},
                ]
            }

        mock_paginator.paginate.return_value = mock_paginate()

        mock_assume_role.return_value = {
            "account_id": "222222222",
            "credentials": {"aws_access_key_id": "key", "aws_secret_access_key": "secret"},
        }

        self.mock_cost_checker.check_async = AsyncMock(
            return_value=CheckResult(
                severity="INFO",
                title="Cost Check",
                message="All good",
            )
        )

        event = {"check_type": "cost", "time": "2024-01-01T00:00:00Z"}

        result = self.async_test(self.orchestrator._async_run_all_checks(event))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("accounts", body)

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    def test_run_all_checks_single_account(self, mock_is_orgs_enabled):
        """Test running checks on single account (non-Organizations)."""
        mock_is_orgs_enabled.return_value = False

        self.mock_cost_checker.check_async = AsyncMock(
            return_value=CheckResult(
                severity="INFO",
                title="Cost Check",
                message="Normal costs",
            )
        )

        event = {"check_type": "cost"}

        result = self.async_test(self.orchestrator._async_run_all_checks(event))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("accounts", body)
        self.assertGreater(len(body["accounts"]), 0)


class TestAccountCheckAggregation(AsyncTestCase):
    """Test aggregation of results across accounts."""

    def setUp(self):
        """Set up orchestrator."""
        super().setUp()
        self.mock_logger = MagicMock()
        self.mock_storage = MagicMock(spec=DynamoDBStorage)
        self.mock_cost_checker = MagicMock()
        self.mock_ec2_checker = MagicMock()
        self.mock_s3_checker = MagicMock()

        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
        )

    def test_determine_system_health_critical(self):
        """Test system health determination with critical findings."""
        checks = {
            "ec2": {"severity": "CRITICAL"},
            "s3": {"severity": "INFO"},
        }

        health = self.orchestrator._determine_system_health(checks)

        self.assertEqual(health, "critical")

    def test_determine_system_health_warning(self):
        """Test system health determination with warning findings."""
        checks = {
            "ec2": {"severity": "HIGH"},
            "s3": {"severity": "LOW"},
        }

        health = self.orchestrator._determine_system_health(checks)

        self.assertEqual(health, "warning")

    def test_determine_system_health_healthy(self):
        """Test system health determination when healthy."""
        checks = {
            "ec2": {"severity": "INFO"},
            "s3": {"severity": "INFO"},
        }

        health = self.orchestrator._determine_system_health(checks)

        self.assertEqual(health, "healthy")


class TestAccountRoleAssumption(AsyncTestCase):
    """Test cross-account role assumption error handling."""

    def setUp(self):
        """Set up orchestrator."""
        super().setUp()
        self.mock_logger = MagicMock()
        self.mock_storage = MagicMock(spec=DynamoDBStorage)
        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=MagicMock(),
            ec2_checker=MagicMock(),
            s3_checker=MagicMock(),
            storage=self.mock_storage,
        )

    @patch("guardian.orchestrator.AWSClientProvider.assume_role_async")
    def test_role_assumption_failure_skips_account(self, mock_assume_role):
        """Test that failed role assumption skips the account."""
        mock_assume_role.return_value = None

        result = self.async_test(
            self.orchestrator._assume_role_for_account_async("invalid-account")
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
