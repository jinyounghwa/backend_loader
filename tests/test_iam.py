"""Unit tests for IAM checker"""
import unittest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from guardian.checkers.iam import IAMChecker
from guardian.checkers.base import CheckResult


class TestIAMChecker(unittest.TestCase):
    """Unit tests for IAMChecker"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_dynamodb_table = Mock()
        self.mock_dynamodb_resource = Mock()
        self.mock_dynamodb_resource.Table.return_value = self.mock_dynamodb_table

        self.mock_clients = {
            'iam': Mock(),
            'dynamodb_resource': self.mock_dynamodb_resource
        }
        self.config = {'iam_baseline_table': 'guardian-iam-baseline'}
        self.checker = IAMChecker(self.mock_clients, self.config)

    def test_initialization(self):
        """Test IAMChecker initialization"""
        self.assertEqual(self.checker.iam, self.mock_clients['iam'])
        self.assertEqual(self.checker.baseline_key, 'iam-baseline')

    def test_check_no_changes(self):
        """Test check() when no IAM changes detected"""
        self.checker._get_iam_users = Mock(return_value={'user1': {
            'arn': 'arn:aws:iam::123:user/user1',
            'create_date': datetime.now(timezone.utc).isoformat(),
            'path': '/'
        }})
        self.checker._get_access_keys = Mock(return_value={'user1': []})
        self.checker._get_baseline = Mock(return_value={
            'users': {'user1': {
                'arn': 'arn:aws:iam::123:user/user1',
                'create_date': datetime.now(timezone.utc).isoformat(),
                'path': '/'
            }},
            'keys': {'user1': []}
        })

        result = self.checker.check()

        self.assertEqual(result.severity, 'INFO')
        self.assertIn('No IAM', result.message)

    def test_check_new_user_detected(self):
        """Test check() when new user is created"""
        current_users = {
            'user1': {'arn': 'arn:aws:iam::123:user/user1', 'create_date': '2026-04-28', 'path': '/'},
            'attacker': {'arn': 'arn:aws:iam::123:user/attacker', 'create_date': '2026-04-28', 'path': '/'}
        }
        baseline_users = {
            'user1': {'arn': 'arn:aws:iam::123:user/user1', 'create_date': '2026-04-27', 'path': '/'}
        }

        self.checker._get_iam_users = Mock(return_value=current_users)
        self.checker._get_access_keys = Mock(return_value={'user1': [], 'attacker': []})
        self.checker._get_baseline = Mock(return_value={'users': baseline_users, 'keys': {'user1': []}})

        result = self.checker.check()

        # 1 new user (HIGH severity) → overall MEDIUM
        self.assertEqual(result.severity, 'MEDIUM')
        self.assertIn('change', result.message.lower())

    def test_check_new_access_key_detected(self):
        """Test check() when new access key is created"""
        current_keys = {
            'user1': [
                {'key_id': 'AKIAIOSFODNN7EXAMPLE1', 'status': 'Active', 'create_date': '2026-04-28'},
                {'key_id': 'AKIAIOSFODNN7EXAMPLE2', 'status': 'Active', 'create_date': '2026-04-28'}
            ]
        }
        baseline_keys = {
            'user1': [
                {'key_id': 'AKIAIOSFODNN7EXAMPLE1', 'status': 'Active', 'create_date': '2026-04-27'}
            ]
        }

        self.checker._get_iam_users = Mock(return_value={'user1': {}})
        self.checker._get_access_keys = Mock(return_value=current_keys)
        self.checker._get_baseline = Mock(return_value={
            'users': {'user1': {}},
            'keys': baseline_keys
        })

        result = self.checker.check()

        # NEW_ACCESS_KEY (MEDIUM severity) → overall LOW
        self.assertEqual(result.severity, 'LOW')
        self.assertIn('change', result.message.lower())

    def test_get_iam_users_success(self):
        """Test _get_iam_users() retrieves users successfully"""
        mock_users = {
            'Users': [
                {
                    'UserName': 'user1',
                    'Arn': 'arn:aws:iam::123:user/user1',
                    'CreateDate': datetime.now(timezone.utc),
                    'Path': '/'
                }
            ]
        }
        paginator_mock = Mock()
        paginator_mock.paginate.return_value = [mock_users]
        self.mock_clients['iam'].get_paginator.return_value = paginator_mock

        users = self.checker._get_iam_users()

        self.assertEqual(len(users), 1)
        self.assertIn('user1', users)

    def test_get_access_keys_success(self):
        """Test _get_access_keys() retrieves access keys"""
        users = {'user1': {}}
        mock_keys = {
            'AccessKeyMetadata': [
                {
                    'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                    'Status': 'Active',
                    'CreateDate': datetime.now(timezone.utc)
                }
            ]
        }
        paginator_mock = Mock()
        paginator_mock.paginate.return_value = [mock_keys]
        self.mock_clients['iam'].get_paginator.return_value = paginator_mock

        keys = self.checker._get_access_keys(users)

        self.assertIn('user1', keys)
        self.assertEqual(len(keys['user1']), 1)

    def test_get_baseline_empty(self):
        """Test _get_baseline() returns empty when baseline not found"""
        self.mock_dynamodb_table.get_item.return_value = {}

        baseline = self.checker._get_baseline()

        self.assertEqual(baseline, {'users': {}, 'keys': {}})

    def test_get_baseline_existing(self):
        """Test _get_baseline() retrieves existing baseline"""
        self.mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'users': json.dumps({'user1': {}}),
                'keys': json.dumps({'user1': []})
            }
        }

        baseline = self.checker._get_baseline()

        self.assertIn('user1', baseline['users'])

    def test_detect_changes_new_user(self):
        """Test _detect_changes() identifies new users"""
        current_users = {'new_user': {}}
        baseline = {'users': {}, 'keys': {}}

        changes = self.checker._detect_changes(current_users, {}, baseline)

        self.assertGreater(len(changes), 0)
        self.assertEqual(changes[0]['type'], 'NEW_USER')

    def test_detect_changes_deleted_user(self):
        """Test _detect_changes() identifies deleted users"""
        current_users = {}
        baseline = {'users': {'deleted_user': {}}, 'keys': {'deleted_user': []}}

        changes = self.checker._detect_changes(current_users, {}, baseline)

        self.assertGreater(len(changes), 0)
        self.assertEqual(changes[0]['type'], 'DELETED_USER')

    def test_detect_changes_new_access_key(self):
        """Test _detect_changes() identifies new access keys"""
        current_keys = {
            'user1': [
                {'key_id': 'AKIAIOSFODNN7EXAMPLE1', 'status': 'Active', 'create_date': '2026-04-28'},
                {'key_id': 'AKIAIOSFODNN7EXAMPLE2', 'status': 'Active', 'create_date': '2026-04-28'}
            ]
        }
        baseline = {
            'users': {},
            'keys': {'user1': [{'key_id': 'AKIAIOSFODNN7EXAMPLE1', 'status': 'Active', 'create_date': '2026-04-27'}]}
        }

        changes = self.checker._detect_changes({}, current_keys, baseline)

        self.assertGreater(len(changes), 0)
        self.assertEqual(changes[0]['type'], 'NEW_ACCESS_KEY')

    def test_determine_severity_high(self):
        """Test _determine_severity() returns HIGH for multiple new users"""
        changes = [
            {'type': 'NEW_USER', 'severity': 'HIGH'},
            {'type': 'NEW_USER', 'severity': 'HIGH'}
        ]

        severity = self.checker._determine_severity(changes)

        self.assertEqual(severity, 'HIGH')

    def test_determine_severity_medium(self):
        """Test _determine_severity() returns MEDIUM for single new user"""
        changes = [
            {'type': 'NEW_USER', 'severity': 'HIGH'}
        ]

        severity = self.checker._determine_severity(changes)

        self.assertEqual(severity, 'MEDIUM')

    def test_determine_severity_low(self):
        """Test _determine_severity() returns LOW for access key changes"""
        changes = [
            {'type': 'NEW_ACCESS_KEY', 'severity': 'MEDIUM'}
        ]

        severity = self.checker._determine_severity(changes)

        self.assertEqual(severity, 'LOW')

    def test_save_baseline_success(self):
        """Test _save_baseline() saves current state"""
        users = {'user1': {'arn': 'arn:aws:iam::123:user/user1', 'create_date': '2026-04-28', 'path': '/'}}
        keys = {'user1': []}

        self.checker._save_baseline(users, keys)

        self.mock_dynamodb_table.put_item.assert_called_once()

    def test_check_result_structure(self):
        """Test check() returns properly structured CheckResult"""
        self.checker._get_iam_users = Mock(return_value={})
        self.checker._get_access_keys = Mock(return_value={})
        self.checker._get_baseline = Mock(return_value={'users': {}, 'keys': {}})

        result = self.checker.check()

        self.assertIsInstance(result, CheckResult)
        self.assertIn(result.severity, ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        self.assertIsNotNone(result.title)
        self.assertIsNotNone(result.message)

    def test_check_error_handling(self):
        """Test check() handles exceptions gracefully"""
        self.checker._get_iam_users = Mock(side_effect=Exception('API error'))

        result = self.checker.check()

        # CheckResult.error() returns HIGH severity
        self.assertEqual(result.severity, 'HIGH')
        self.assertIn('Failed', result.message)


if __name__ == '__main__':
    unittest.main()
