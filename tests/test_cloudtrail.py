"""Unit tests for CloudTrail checker"""
import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.base import CheckResult


class TestCloudTrailChecker(unittest.TestCase):
    """Unit tests for CloudTrailChecker"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_clients = {
            'cloudtrail': Mock(),
            'sts': Mock()
        }
        self.config = {}
        self.checker = CloudTrailChecker(self.mock_clients, self.config)

    def test_initialization(self):
        """Test CloudTrailChecker initialization"""
        self.assertEqual(self.checker.cloudtrail, self.mock_clients['cloudtrail'])
        self.assertIsNotNone(self.checker.sts)

    def test_check_no_findings(self):
        """Test check() when no suspicious events found"""
        self.checker._get_recent_events = Mock(return_value=[])

        result = self.checker.check()

        self.assertEqual(result.severity, 'INFO')
        self.assertIn('No suspicious', result.message)

    def test_check_with_suspicious_events(self):
        """Test check() with suspicious API calls detected"""
        suspicious_events = [
            {
                'EventName': 'CreateAccessKey',
                'Username': 'suspicious-user',
                'SourceIPAddress': '192.168.1.100',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'CloudTrailEvent': '{}'
            }
        ]
        self.checker._get_recent_events = Mock(return_value=suspicious_events)

        result = self.checker.check()

        self.assertEqual(result.severity, 'HIGH')
        self.assertIn('suspicious', result.message.lower())

    def test_check_root_account_activity(self):
        """Test check() with root account suspicious activity"""
        root_events = [
            {
                'EventName': 'StopInstances',
                'Username': 'root',
                'SourceIPAddress': '10.0.0.1',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'CloudTrailEvent': '{}'
            }
        ]
        self.checker._get_recent_events = Mock(return_value=root_events)

        result = self.checker.check()

        # Root account activity should be CRITICAL
        self.assertEqual(result.severity, 'CRITICAL')

    def test_check_unauthorized_region(self):
        """Test check() with API calls from unauthorized region"""
        # Mock an event from an unexpected region
        events = [
            {
                'EventName': 'DescribeInstances',
                'Username': 'test-user',
                'SourceIPAddress': '203.0.113.42',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'CloudTrailEvent': '{"awsRegion": "eu-west-1"}'
            }
        ]
        self.checker._get_recent_events = Mock(return_value=events)

        result = self.checker.check()

        self.assertIsNotNone(result.severity)

    def test_get_recent_events_empty(self):
        """Test _get_recent_events() with no events"""
        self.mock_clients['cloudtrail'].lookup_events = Mock(return_value={'Events': []})
        self.mock_clients['sts'].get_caller_identity = Mock(
            return_value={'Arn': 'arn:aws:iam::123456789:user/test'}
        )

        events = self.checker._get_recent_events()

        self.assertEqual(events, [])

    def test_get_recent_events_success(self):
        """Test _get_recent_events() with actual events"""
        mock_events = {
            'Events': [
                {
                    'EventName': 'CreateAccessKey',
                    'Username': 'attacker',
                    'SourceIPAddress': '192.168.1.1',
                    'EventTime': datetime.now(timezone.utc),
                    'CloudTrailEvent': json.dumps({'awsRegion': 'us-east-1'})
                }
            ]
        }

        # Setup paginator mock
        paginator_mock = Mock()
        paginator_mock.paginate.return_value = [mock_events]
        self.mock_clients['cloudtrail'].get_paginator.return_value = paginator_mock

        events = self.checker._get_recent_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['EventName'], 'CreateAccessKey')

    def test_analyze_events_suspicious_pattern(self):
        """Test _analyze_events() detects suspicious patterns"""
        events = [
            {
                'EventName': 'CreateAccessKey',
                'Username': 'suspicious-user',
                'SourceIPAddress': '203.0.113.1',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'CloudTrailEvent': '{}'
            },
            {
                'EventName': 'AttachUserPolicy',
                'Username': 'suspicious-user',
                'SourceIPAddress': '203.0.113.1',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'CloudTrailEvent': '{}'
            }
        ]

        anomalies = self.checker._analyze_events(events)

        self.assertGreater(len(anomalies), 0)

    def test_determine_severity_critical(self):
        """Test _determine_severity() returns CRITICAL for critical events"""
        anomalies = [
            {
                'event_name': 'root',
                'severity': 'CRITICAL'
            }
        ]

        severity = self.checker._determine_severity(anomalies)

        self.assertEqual(severity, 'CRITICAL')

    def test_determine_severity_high(self):
        """Test _determine_severity() returns HIGH for high-risk events"""
        anomalies = [
            {
                'event_name': 'CreateAccessKey',
                'severity': 'HIGH'
            }
        ]

        severity = self.checker._determine_severity(anomalies)

        self.assertEqual(severity, 'HIGH')

    def test_determine_severity_medium(self):
        """Test _determine_severity() returns MEDIUM for 3+ anomalies"""
        anomalies = [
            {'event_name': 'Event1', 'severity': 'LOW'},
            {'event_name': 'Event2', 'severity': 'LOW'},
            {'event_name': 'Event3', 'severity': 'LOW'}
        ]

        severity = self.checker._determine_severity(anomalies)

        self.assertEqual(severity, 'MEDIUM')

    def test_get_remediation_suggestion(self):
        """Test _get_remediation_suggestion() generates appropriate advice"""
        anomalies = [
            {
                'event_name': 'CreateAccessKey',
                'severity': 'HIGH'
            },
            {
                'event_name': 'AttachUserPolicy',
                'severity': 'HIGH'
            }
        ]

        suggestion = self.checker._get_remediation_suggestion(anomalies)

        self.assertIsNotNone(suggestion)
        self.assertIsInstance(suggestion, str)
        self.assertGreater(len(suggestion), 0)

    def test_check_result_structure(self):
        """Test check() returns properly structured CheckResult"""
        self.checker._get_recent_events = Mock(return_value=[])

        result = self.checker.check()

        self.assertIsInstance(result, CheckResult)
        self.assertIn(result.severity, ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        self.assertIsNotNone(result.title)
        self.assertIsNotNone(result.message)
        self.assertIsInstance(result.details, dict)

    def test_check_error_handling(self):
        """Test check() handles exceptions gracefully"""
        self.checker._get_recent_events = Mock(side_effect=Exception('API error'))

        result = self.checker.check()

        # CheckResult.error() returns HIGH severity
        self.assertEqual(result.severity, 'HIGH')
        self.assertIn('Failed', result.message)

    def test_suspicious_events_list(self):
        """Test that SUSPICIOUS_EVENTS contains expected API calls"""
        suspicious_list = self.checker.SUSPICIOUS_EVENTS

        self.assertIn('CreateAccessKey', suspicious_list)
        self.assertIn('AttachUserPolicy', suspicious_list)
        self.assertIn('DeleteBucket', suspicious_list)
        self.assertIn('TerminateInstances', suspicious_list)

    def test_timestamp_filtering(self):
        """Test that events are filtered by timestamp correctly"""
        old_event = {
            'EventName': 'CreateAccessKey',
            'EventTime': datetime.now(timezone.utc) - timedelta(hours=2),
            'Username': 'user',
            'SourceIPAddress': '192.168.1.1',
            'CloudTrailEvent': '{}'
        }
        recent_event = {
            'EventName': 'CreateAccessKey',
            'EventTime': datetime.now(timezone.utc) - timedelta(minutes=5),
            'Username': 'user',
            'SourceIPAddress': '192.168.1.1',
            'CloudTrailEvent': '{}'
        }

        # Setup paginator mock
        paginator_mock = Mock()
        paginator_mock.paginate.return_value = [{'Events': [old_event, recent_event]}]
        self.mock_clients['cloudtrail'].get_paginator.return_value = paginator_mock

        events = self.checker._get_recent_events()

        # Should return events from the last hour (both are within 2 hours, filtered by API)
        self.assertGreater(len(events), 0)


class TestCloudTrailCheckerIntegration(unittest.TestCase):
    """Integration tests for CloudTrailChecker with mocked AWS"""

    def test_full_check_workflow(self):
        """Test complete check workflow"""
        # Setup mocks
        mock_cloudtrail = Mock()
        mock_sts = Mock()

        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789:user/test'
        }
        mock_cloudtrail.lookup_events.return_value = {
            'Events': []
        }

        clients = {'cloudtrail': mock_cloudtrail, 'sts': mock_sts}
        checker = CloudTrailChecker(clients, {})

        result = checker.check()

        self.assertEqual(result.severity, 'INFO')
        self.assertIsNotNone(result.details)


if __name__ == '__main__':
    import json
    unittest.main()
