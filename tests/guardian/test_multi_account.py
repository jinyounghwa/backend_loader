"""Tests for multi-account support in orchestrator (sync-first model)."""

import json
import unittest
from unittest.mock import MagicMock, patch

from guardian.checkers.base import CheckResult
from guardian.orchestrator import GuardianOrchestrator
from guardian.storage.dynamodb import DynamoDBStorage


class TestMultiAccountOrchestrator(unittest.TestCase):
    """Test multi-account support in orchestrator."""

    def setUp(self):
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
    def test_get_accounts_single_account(self, mock_is_orgs_enabled):
        """Test _get_accounts with single account (non-Orgs)."""
        mock_is_orgs_enabled.return_value = False

        result = self.orchestrator._get_accounts()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["account_id"], "current")

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    @patch("guardian.orchestrator.AWSClientProvider.get_client")
    def test_get_accounts_multiple_accounts(self, mock_get_client, mock_is_orgs_enabled):
        """Test _get_accounts retrieves multiple accounts from Organizations."""
        mock_is_orgs_enabled.return_value = True
        mock_orgs = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {"Id": "123456789", "Name": "Production", "Status": "ACTIVE"},
                    {"Id": "987654321", "Name": "Development", "Status": "ACTIVE"},
                ]
            }
        ]
        mock_orgs.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_orgs

        result = self.orchestrator._get_accounts()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["account_id"], "123456789")
        self.assertEqual(result[0]["account_name"], "Production")

    @patch("guardian.orchestrator.AWSClientProvider.get_client")
    def test_assume_role_success(self, mock_get_client):
        """Test successful cross-account role assumption."""
        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "SessionToken": "token123",
            }
        }
        mock_get_client.return_value = mock_sts

        result = self.orchestrator._assume_role_for_account("987654321")

        self.assertIsNotNone(result)
        self.assertIn("credentials", result)

    @patch("guardian.orchestrator.AWSClientProvider.get_client")
    def test_assume_role_failure(self, mock_get_client):
        """Test role assumption failure handling."""
        mock_sts = MagicMock()
        mock_sts.assume_role.side_effect = Exception("Access denied")
        mock_get_client.return_value = mock_sts

        result = self.orchestrator._assume_role_for_account("invalid-account")

        self.assertIsNone(result)

    def test_create_account_checkers(self):
        """Test creating account-specific checkers with cross-account credentials."""
        credentials = {
            "aws_access_key_id": "AKIA...",
            "aws_secret_access_key": "secret...",
            "aws_session_token": "token...",
        }

        with patch("guardian.orchestrator.AWSClientProvider.get_client_for_account") as mock:
            mock.return_value = MagicMock()
            result = self.orchestrator._create_account_checkers("987654321", credentials)

        self.assertIsNotNone(result)
        self.assertIn("cost", result)

    @patch("guardian.orchestrator.Config.is_organizations_enabled")
    def test_run_all_checks_single_account(self, mock_is_orgs_enabled):
        """Test running checks on single account (non-Organizations)."""
        mock_is_orgs_enabled.return_value = False

        self.mock_cost_checker.check.return_value = CheckResult(
            severity="INFO",
            title="Cost Check",
            message="Normal costs",
        )

        event = {"check_type": "cost"}

        result = self.orchestrator.run_all_checks(event)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("accounts", body)
        self.assertGreater(len(body["accounts"]), 0)


class TestAccountCheckAggregation(unittest.TestCase):
    """Test aggregation of results across accounts."""

    def setUp(self):
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
        checks = {"ec2": {"severity": "CRITICAL"}, "s3": {"severity": "INFO"}}
        health = self.orchestrator._determine_system_health(checks)
        self.assertEqual(health, "critical")

    def test_determine_system_health_warning(self):
        checks = {"ec2": {"severity": "MEDIUM"}, "s3": {"severity": "LOW"}}
        health = self.orchestrator._determine_system_health(checks)
        self.assertEqual(health, "warning")

    def test_determine_system_health_high_is_critical(self):
        """HIGH severity maps to 'critical' (priority 2 >= 2)."""
        checks = {"ec2": {"severity": "HIGH"}, "s3": {"severity": "LOW"}}
        health = self.orchestrator._determine_system_health(checks)
        self.assertEqual(health, "critical")

    def test_determine_system_health_healthy(self):
        checks = {"ec2": {"severity": "INFO"}, "s3": {"severity": "INFO"}}
        health = self.orchestrator._determine_system_health(checks)
        self.assertEqual(health, "healthy")


if __name__ == "__main__":
    unittest.main()
