"""Unit tests for GuardianOrchestrator - unified check pipeline"""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from guardian.checkers.base import CheckResult
from guardian.orchestrator import GuardianOrchestrator


def _make_info_result(title="OK", message="No issues"):
    return CheckResult(severity="INFO", title=title, message=message, details={})


def _make_alert_result(severity="HIGH", title="Alert", message="Issue found", details=None):
    return CheckResult(severity=severity, title=title, message=message, details=details or {})


class TestGuardianOrchestratorRegistry(unittest.TestCase):

    def setUp(self):
        self.mock_logger = Mock()
        self.mock_cost_checker = Mock()
        self.mock_ec2_checker = Mock()
        self.mock_s3_checker = Mock()
        self.mock_cloudtrail_checker = Mock()
        self.mock_iam_checker = Mock()
        self.mock_guardduty_checker = Mock()
        self.mock_storage = Mock()
        self.mock_telegram = Mock()

        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
            telegram_responder=self.mock_telegram,
            cloudtrail_checker=self.mock_cloudtrail_checker,
            iam_checker=self.mock_iam_checker,
            guardduty_checker=self.mock_guardduty_checker,
        )

    def test_checkers_registry_initialized(self):
        self.assertIsNotNone(self.orchestrator.checkers)
        self.assertEqual(len(self.orchestrator.checkers), 6)
        self.assertIn("cost", self.orchestrator.checkers)
        self.assertIn("ec2", self.orchestrator.checkers)
        self.assertIn("s3", self.orchestrator.checkers)
        self.assertIn("cloudtrail", self.orchestrator.checkers)
        self.assertIn("iam", self.orchestrator.checkers)
        self.assertIn("guardduty", self.orchestrator.checkers)

    def test_checkers_mapped_correctly(self):
        self.assertEqual(self.orchestrator.checkers["cost"], self.mock_cost_checker)
        self.assertEqual(self.orchestrator.checkers["ec2"], self.mock_ec2_checker)
        self.assertEqual(self.orchestrator.checkers["s3"], self.mock_s3_checker)
        self.assertEqual(self.orchestrator.checkers["cloudtrail"], self.mock_cloudtrail_checker)
        self.assertEqual(self.orchestrator.checkers["iam"], self.mock_iam_checker)
        self.assertEqual(self.orchestrator.checkers["guardduty"], self.mock_guardduty_checker)

    def test_get_checks_for_type_cost(self):
        checks = self.orchestrator._get_checks_for_type("cost")
        self.assertEqual(checks, ["cost"])

    def test_get_checks_for_type_security(self):
        checks = self.orchestrator._get_checks_for_type("security")
        self.assertEqual(len(checks), 5)
        self.assertIn("ec2", checks)
        self.assertIn("s3", checks)
        self.assertIn("cloudtrail", checks)
        self.assertIn("iam", checks)
        self.assertIn("guardduty", checks)

    def test_get_checks_for_type_all(self):
        checks = self.orchestrator._get_checks_for_type("all")
        self.assertEqual(len(checks), 6)


class TestGuardianOrchestratorSingleCheck(unittest.TestCase):

    def setUp(self):
        self.mock_logger = Mock()
        self.mock_storage = Mock()
        self.mock_telegram = Mock()

        self.mock_cost_checker = Mock()
        self.mock_ec2_checker = Mock()
        self.mock_s3_checker = Mock()
        self.mock_cloudtrail_checker = Mock()
        self.mock_iam_checker = Mock()
        self.mock_guardduty_checker = Mock()

        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
            telegram_responder=self.mock_telegram,
            cloudtrail_checker=self.mock_cloudtrail_checker,
            iam_checker=self.mock_iam_checker,
            guardduty_checker=self.mock_guardduty_checker,
        )

    def test_run_single_check_cloudtrail_success(self):
        check_result = _make_alert_result(
            severity="HIGH", title="Suspicious API Call", details={"event_count": 1}
        )
        self.mock_cloudtrail_checker.check.return_value = check_result

        result = self.orchestrator._run_single_check("cloudtrail", self.mock_cloudtrail_checker)

        self.assertEqual(result.severity, "HIGH")
        self.mock_cloudtrail_checker.check.assert_called_once()

    def test_run_single_check_sends_alert_when_not_info(self):
        check_result = _make_alert_result(severity="HIGH")
        self.mock_cloudtrail_checker.check.return_value = check_result

        self.orchestrator._run_single_check("cloudtrail", self.mock_cloudtrail_checker)

        self.mock_telegram.send_alert.assert_called_once()

    def test_run_single_check_no_alert_when_info(self):
        check_result = _make_info_result()
        self.mock_cloudtrail_checker.check.return_value = check_result

        self.orchestrator._run_single_check("cloudtrail", self.mock_cloudtrail_checker)

        self.mock_telegram.send_alert.assert_not_called()

    def test_run_single_check_saves_event_when_not_info(self):
        check_result = _make_alert_result(severity="HIGH")
        self.mock_cloudtrail_checker.check.return_value = check_result

        self.orchestrator._run_single_check("cloudtrail", self.mock_cloudtrail_checker)

        self.mock_storage.save_event.assert_called_once()
        call_args = self.mock_storage.save_event.call_args
        self.assertEqual(call_args[0][0], "cloudtrail")
        self.assertEqual(call_args[0][1], "HIGH")

    def test_run_single_check_exception_handling(self):
        self.mock_cloudtrail_checker.check.side_effect = Exception("API error")

        with self.assertRaises(Exception):
            self.orchestrator._run_single_check("cloudtrail", self.mock_cloudtrail_checker)


class TestGuardianOrchestratorCheckType(unittest.TestCase):

    def setUp(self):
        self.mock_logger = Mock()
        self.mock_storage = Mock()
        self.mock_telegram = Mock()

        self.mock_cost_checker = Mock()
        self.mock_ec2_checker = Mock()
        self.mock_s3_checker = Mock()
        self.mock_cloudtrail_checker = Mock()
        self.mock_iam_checker = Mock()
        self.mock_guardduty_checker = Mock()

        info_result = _make_info_result()
        self.mock_cost_checker.check.return_value = info_result
        self.mock_cost_checker.check_async = AsyncMock(return_value=info_result)
        self.mock_ec2_checker.check.return_value = info_result
        self.mock_ec2_checker.check_async = AsyncMock(return_value=info_result)
        self.mock_s3_checker.check.return_value = info_result
        self.mock_s3_checker.check_async = AsyncMock(return_value=info_result)
        self.mock_cloudtrail_checker.check.return_value = info_result
        self.mock_cloudtrail_checker.check_async = AsyncMock(return_value=info_result)
        self.mock_iam_checker.check.return_value = info_result
        self.mock_iam_checker.check_async = AsyncMock(return_value=info_result)
        self.mock_guardduty_checker.check.return_value = info_result
        self.mock_guardduty_checker.check_async = AsyncMock(return_value=info_result)

        self.orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
            telegram_responder=self.mock_telegram,
            cloudtrail_checker=self.mock_cloudtrail_checker,
            iam_checker=self.mock_iam_checker,
            guardduty_checker=self.mock_guardduty_checker,
        )

    def test_run_all_checks_with_check_type_cost(self):
        event = {"check_type": "cost", "time": datetime.now(timezone.utc).isoformat()}
        self.orchestrator.run_all_checks(event)  # noqa: F841

        self.mock_cost_checker.check.assert_called_once()
        self.mock_ec2_checker.check.assert_not_called()
        self.mock_s3_checker.check.assert_not_called()
        self.mock_cloudtrail_checker.check.assert_not_called()
        self.mock_iam_checker.check.assert_not_called()
        self.mock_guardduty_checker.check.assert_not_called()

    def test_run_all_checks_with_check_type_security(self):
        event = {"check_type": "security", "time": datetime.now(timezone.utc).isoformat()}
        self.orchestrator.run_all_checks(event)  # noqa: F841

        self.mock_cost_checker.check.assert_not_called()
        self.mock_ec2_checker.check.assert_called_once()
        self.mock_s3_checker.check.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()
        self.mock_iam_checker.check.assert_called_once()
        self.mock_guardduty_checker.check.assert_called_once()

    def test_run_all_checks_with_check_type_all(self):
        event = {"check_type": "all", "time": datetime.now(timezone.utc).isoformat()}
        self.orchestrator.run_all_checks(event)  # noqa: F841

        self.mock_cost_checker.check.assert_called_once()
        self.mock_ec2_checker.check.assert_called_once()
        self.mock_s3_checker.check.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()
        self.mock_iam_checker.check.assert_called_once()
        self.mock_guardduty_checker.check.assert_called_once()

    def test_run_all_checks_default_check_type_all(self):
        event = {"time": datetime.now(timezone.utc).isoformat()}
        self.orchestrator.run_all_checks(event)  # noqa: F841

        self.mock_cost_checker.check.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()


if __name__ == "__main__":
    unittest.main()
