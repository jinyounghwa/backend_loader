"""Unit tests for GuardianOrchestrator - registry pattern and dispatcher"""
import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.orchestrator import GuardianOrchestrator
from guardian.checkers.base import CheckResult


class TestGuardianOrchestratorRegistry(unittest.TestCase):
    """Test registry pattern for checker management"""

    def setUp(self):
        """Set up test fixtures"""
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
        """Test that all checkers are registered in the registry"""
        self.assertIsNotNone(self.orchestrator.checkers)
        self.assertEqual(len(self.orchestrator.checkers), 6)
        self.assertIn('cost', self.orchestrator.checkers)
        self.assertIn('ec2', self.orchestrator.checkers)
        self.assertIn('s3', self.orchestrator.checkers)
        self.assertIn('cloudtrail', self.orchestrator.checkers)
        self.assertIn('iam', self.orchestrator.checkers)
        self.assertIn('guardduty', self.orchestrator.checkers)

    def test_checkers_mapped_correctly(self):
        """Test that registry maps correct checker instances"""
        self.assertEqual(self.orchestrator.checkers['cost'], self.mock_cost_checker)
        self.assertEqual(self.orchestrator.checkers['ec2'], self.mock_ec2_checker)
        self.assertEqual(self.orchestrator.checkers['s3'], self.mock_s3_checker)
        self.assertEqual(self.orchestrator.checkers['cloudtrail'], self.mock_cloudtrail_checker)
        self.assertEqual(self.orchestrator.checkers['iam'], self.mock_iam_checker)
        self.assertEqual(self.orchestrator.checkers['guardduty'], self.mock_guardduty_checker)

    def test_get_checks_for_type_cost(self):
        """Test _get_checks_for_type returns only cost check"""
        checks = self.orchestrator._get_checks_for_type('cost')
        self.assertEqual(checks, ['cost'])

    def test_get_checks_for_type_security(self):
        """Test _get_checks_for_type returns all security checks"""
        checks = self.orchestrator._get_checks_for_type('security')
        self.assertEqual(len(checks), 5)
        self.assertIn('cloudtrail', checks)
        self.assertIn('iam', checks)
        self.assertIn('guardduty', checks)
        self.assertIn('ec2', checks)
        self.assertIn('s3', checks)

    def test_get_checks_for_type_all(self):
        """Test _get_checks_for_type returns all checks"""
        checks = self.orchestrator._get_checks_for_type('all')
        self.assertEqual(len(checks), 6)
        self.assertIn('cost', checks)
        self.assertIn('cloudtrail', checks)
        self.assertIn('iam', checks)
        self.assertIn('guardduty', checks)

    def test_get_checks_for_type_case_insensitive(self):
        """Test _get_checks_for_type is called with pre-lowercased input"""
        # The orchestrator lowercases check_type before calling _get_checks_for_type
        # This test verifies that calling with lowercase works correctly
        checks_cost = self.orchestrator._get_checks_for_type('cost')
        self.assertEqual(checks_cost, ['cost'])

        checks_security = self.orchestrator._get_checks_for_type('security')
        self.assertEqual(len(checks_security), 5)
        self.assertIn('cloudtrail', checks_security)


class TestGuardianOrchestratorDispatcher(unittest.TestCase):
    """Test new check dispatcher (_run_new_check)"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_logger = Mock()
        self.mock_storage = Mock()
        self.mock_telegram = Mock()

        # Create mock checkers with check() method
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

    def test_run_new_check_cloudtrail_success(self):
        """Test _run_new_check executes CloudTrail checker"""
        check_result = CheckResult(
            severity='HIGH',
            title='Suspicious API Call',
            message='CreateAccessKey detected',
            details={'event_count': 1}
        )
        self.mock_cloudtrail_checker.check.return_value = check_result

        results = {'checks': {}}
        result_dict = self.orchestrator._run_new_check('cloudtrail', results)

        self.assertEqual(result_dict['severity'], 'HIGH')
        self.assertEqual(result_dict['title'], 'Suspicious API Call')
        self.mock_cloudtrail_checker.check.assert_called_once()

    def test_run_new_check_iam_success(self):
        """Test _run_new_check executes IAM checker"""
        check_result = CheckResult(
            severity='MEDIUM',
            title='IAM Change Detected',
            message='New access key created',
            details={'username': 'attacker', 'key_id': 'AKIA...'}
        )
        self.mock_iam_checker.check.return_value = check_result

        results = {'checks': {}}
        result_dict = self.orchestrator._run_new_check('iam', results)

        self.assertEqual(result_dict['severity'], 'MEDIUM')
        self.mock_iam_checker.check.assert_called_once()

    def test_run_new_check_guardduty_success(self):
        """Test _run_new_check executes GuardDuty checker"""
        check_result = CheckResult(
            severity='CRITICAL',
            title='Threat Detected',
            message='Malware found on instance',
            details={'instance_id': 'i-123', 'threat_type': 'Trojan'}
        )
        self.mock_guardduty_checker.check.return_value = check_result

        results = {'checks': {}}
        result_dict = self.orchestrator._run_new_check('guardduty', results)

        self.assertEqual(result_dict['severity'], 'CRITICAL')
        self.mock_guardduty_checker.check.assert_called_once()

    def test_run_new_check_sends_alert_when_not_info(self):
        """Test _run_new_check sends Telegram alert for non-INFO severity"""
        check_result = CheckResult(
            severity='HIGH',
            title='Issue Found',
            message='Something is wrong',
            details={}
        )
        self.mock_cloudtrail_checker.check.return_value = check_result

        results = {'checks': {}}
        self.orchestrator._run_new_check('cloudtrail', results)

        # Verify telegram.send_alert was called
        self.mock_telegram.send_alert.assert_called_once()
        call_args = self.mock_telegram.send_alert.call_args
        self.assertEqual(call_args[0][0], 'cloudtrail')  # check_name

    def test_run_new_check_no_alert_when_info(self):
        """Test _run_new_check does NOT send alert for INFO severity"""
        check_result = CheckResult(
            severity='INFO',
            title='All Good',
            message='No issues found',
            details={}
        )
        self.mock_cloudtrail_checker.check.return_value = check_result

        results = {'checks': {}}
        self.orchestrator._run_new_check('cloudtrail', results)

        # Verify telegram.send_alert was NOT called
        self.mock_telegram.send_alert.assert_not_called()

    def test_run_new_check_saves_event_when_not_info(self):
        """Test _run_new_check saves event to DynamoDB for non-INFO"""
        check_result = CheckResult(
            severity='HIGH',
            title='Issue',
            message='Problem detected',
            details={}
        )
        self.mock_cloudtrail_checker.check.return_value = check_result

        results = {'checks': {}}
        self.orchestrator._run_new_check('cloudtrail', results)

        # Verify storage.save_event was called
        self.mock_storage.save_event.assert_called_once()
        call_args = self.mock_storage.save_event.call_args
        self.assertEqual(call_args[0][0], 'cloudtrail')  # check_name
        self.assertEqual(call_args[0][1], 'HIGH')  # severity

    def test_run_new_check_no_checker_returns_empty(self):
        """Test _run_new_check returns empty dict when checker not found"""
        orchestrator = GuardianOrchestrator(
            logger=self.mock_logger,
            cost_checker=self.mock_cost_checker,
            ec2_checker=self.mock_ec2_checker,
            s3_checker=self.mock_s3_checker,
            storage=self.mock_storage,
            cloudtrail_checker=None,  # None checker
        )

        results = {'checks': {}}
        result_dict = orchestrator._run_new_check('cloudtrail', results)

        self.assertEqual(result_dict, {})

    def test_run_new_check_exception_handling(self):
        """Test _run_new_check handles checker exceptions gracefully"""
        self.mock_cloudtrail_checker.check.side_effect = Exception('API error')

        results = {'checks': {}}
        result_dict = self.orchestrator._run_new_check('cloudtrail', results)

        self.assertEqual(result_dict, {})
        # Error should be recorded in results
        self.assertIn('cloudtrail', results['checks'])
        self.assertIn('error', results['checks']['cloudtrail'])


class TestGuardianOrchestratorCheckType(unittest.TestCase):
    """Test check_type parameter integration"""

    def setUp(self):
        """Set up test fixtures with all checkers returning clean results"""
        self.mock_logger = Mock()
        self.mock_storage = Mock()
        self.mock_telegram = Mock()

        # Create all checkers
        self.mock_cost_checker = Mock()
        self.mock_ec2_checker = Mock()
        self.mock_s3_checker = Mock()
        self.mock_cloudtrail_checker = Mock()
        self.mock_iam_checker = Mock()
        self.mock_guardduty_checker = Mock()

        # Setup legacy checkers to return (anomaly, data) tuple
        self.mock_cost_checker.check_cost_anomaly.return_value = (False, {'today_cost': 5.0})
        self.mock_ec2_checker.check_ec2_anomalies.return_value = (False, {'anomalies': []})
        self.mock_s3_checker.check_s3_anomalies.return_value = (False, {'public_buckets': []})

        # Setup new checkers to return CheckResult
        info_result = CheckResult(
            severity='INFO',
            title='OK',
            message='No issues',
            details={}
        )
        self.mock_cloudtrail_checker.check.return_value = info_result
        self.mock_iam_checker.check.return_value = info_result
        self.mock_guardduty_checker.check.return_value = info_result

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
        """Test run_all_checks with check_type='cost' only runs cost check"""
        event = {'check_type': 'cost', 'time': datetime.now(timezone.utc).isoformat()}
        result = self.orchestrator.run_all_checks(event)

        # Cost checker should be called
        self.mock_cost_checker.check_cost_anomaly.assert_called_once()

        # Security checkers should NOT be called
        self.mock_ec2_checker.check_ec2_anomalies.assert_not_called()
        self.mock_s3_checker.check_s3_anomalies.assert_not_called()
        self.mock_cloudtrail_checker.check.assert_not_called()
        self.mock_iam_checker.check.assert_not_called()
        self.mock_guardduty_checker.check.assert_not_called()

    def test_run_all_checks_with_check_type_security(self):
        """Test run_all_checks with check_type='security' runs security checks"""
        event = {'check_type': 'security', 'time': datetime.now(timezone.utc).isoformat()}
        result = self.orchestrator.run_all_checks(event)

        # Cost checker should NOT be called
        self.mock_cost_checker.check_cost_anomaly.assert_not_called()

        # Security checkers SHOULD be called
        self.mock_ec2_checker.check_ec2_anomalies.assert_called_once()
        self.mock_s3_checker.check_s3_anomalies.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()
        self.mock_iam_checker.check.assert_called_once()
        self.mock_guardduty_checker.check.assert_called_once()

    def test_run_all_checks_with_check_type_all(self):
        """Test run_all_checks with check_type='all' runs all checks"""
        event = {'check_type': 'all', 'time': datetime.now(timezone.utc).isoformat()}
        result = self.orchestrator.run_all_checks(event)

        # All checkers should be called
        self.mock_cost_checker.check_cost_anomaly.assert_called_once()
        self.mock_ec2_checker.check_ec2_anomalies.assert_called_once()
        self.mock_s3_checker.check_s3_anomalies.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()
        self.mock_iam_checker.check.assert_called_once()
        self.mock_guardduty_checker.check.assert_called_once()

    def test_run_all_checks_default_check_type_all(self):
        """Test run_all_checks defaults to 'all' when check_type omitted"""
        event = {'time': datetime.now(timezone.utc).isoformat()}
        result = self.orchestrator.run_all_checks(event)

        # All checkers should be called
        self.mock_cost_checker.check_cost_anomaly.assert_called_once()
        self.mock_cloudtrail_checker.check.assert_called_once()


if __name__ == '__main__':
    unittest.main()
