"""Sprint 33 Phase 1: Security Rules Tests

Tests for security rule storage and management.
Covers CRUD operations and rule listing/filtering.
"""

import pytest
from unittest.mock import MagicMock, patch
import json
import sys
from pathlib import Path
from guardian.storage.security_rules import SecurityRule, SecurityRuleRepository


class TestSecurityRuleModel:
    """Test SecurityRule data class"""

    def test_create_rule_model(self):
        """Test creating a SecurityRule instance"""
        rule = SecurityRule(
            rule_id='rule-1',
            rule_type='connection_spike',
            condition={'threshold': 10, 'window_minutes': 5},
            action={'notify': ['telegram', 'discord']},
            priority=8,
            account_id='123456789',
            enabled=True,
        )

        assert rule.rule_id == 'rule-1'
        assert rule.rule_type == 'connection_spike'
        assert rule.priority == 8
        assert rule.account_id == '123456789'
        assert rule.enabled is True

    def test_rule_to_dynamodb_item(self):
        """Test converting rule to DynamoDB item format"""
        rule = SecurityRule(
            rule_id='rule-1',
            rule_type='connection_spike',
            condition={'threshold': 10, 'window_minutes': 5},
            action={'notify': ['telegram']},
            priority=5,
            account_id='123456789',
        )

        item = rule.to_dynamodb_item()

        assert item['rule_id'] == 'rule-1'
        assert item['rule_type'] == 'connection_spike'
        assert item['priority'] == 5
        assert item['account_id'] == '123456789'
        assert isinstance(item['condition'], str)  # JSON string
        assert isinstance(item['action'], str)  # JSON string

    def test_rule_from_dynamodb_item(self):
        """Test creating rule from DynamoDB item"""
        item = {
            'rule_id': 'rule-1',
            'rule_type': 'auth_failure',
            'condition': json.dumps({'threshold': 5}),
            'action': json.dumps({'notify': ['telegram']}),
            'priority': 7,
            'account_id': '123456789',
            'enabled': True,
            'created_at': '2026-05-23T10:00:00',
            'updated_at': '2026-05-23T10:00:00',
        }

        rule = SecurityRule.from_dynamodb_item(item)

        assert rule.rule_id == 'rule-1'
        assert rule.rule_type == 'auth_failure'
        assert rule.condition == {'threshold': 5}
        assert rule.action == {'notify': ['telegram']}
        assert rule.priority == 7


class TestSecurityRuleRepository:
    """Test SecurityRuleRepository CRUD operations"""

    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_dynamodb_table):
        """Create repository with mocked DynamoDB"""
        with patch('guardian.storage.security_rules.boto3.resource') as mock_boto3:
            mock_boto3.return_value.Table.return_value = mock_dynamodb_table
            repo = SecurityRuleRepository('test-rules-table')
            repo.table = mock_dynamodb_table
            return repo

    def test_create_rule(self, repository, mock_dynamodb_table):
        """Test creating a new rule"""
        rule = SecurityRule(
            rule_id='',  # Will be generated
            rule_type='connection_spike',
            condition={'threshold': 10, 'window_minutes': 5},
            action={'notify': ['telegram', 'discord']},
            priority=8,
            account_id='123456789',
        )

        created_rule = repository.create_rule(rule)

        assert created_rule.rule_id is not None
        assert created_rule.rule_type == 'connection_spike'
        assert created_rule.created_at is not None
        mock_dynamodb_table.put_item.assert_called_once()

    def test_get_rule(self, repository, mock_dynamodb_table):
        """Test getting a rule by ID"""
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'rule_id': 'rule-1',
                'rule_type': 'connection_spike',
                'condition': json.dumps({'threshold': 10}),
                'action': json.dumps({'notify': ['telegram']}),
                'priority': 8,
                'account_id': '123456789',
                'enabled': True,
                'created_at': '2026-05-23T10:00:00',
                'updated_at': '2026-05-23T10:00:00',
            }
        }

        rule = repository.get_rule('rule-1')

        assert rule is not None
        assert rule.rule_id == 'rule-1'
        assert rule.rule_type == 'connection_spike'
        assert rule.priority == 8

    def test_get_rule_not_found(self, repository, mock_dynamodb_table):
        """Test getting a non-existent rule"""
        mock_dynamodb_table.get_item.return_value = {}

        rule = repository.get_rule('nonexistent')

        assert rule is None

    def test_update_rule(self, repository, mock_dynamodb_table):
        """Test updating a rule"""
        # Mock get_item to return existing rule
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'rule_id': 'rule-1',
                'rule_type': 'connection_spike',
                'condition': json.dumps({'threshold': 10}),
                'action': json.dumps({'notify': ['telegram']}),
                'priority': 8,
                'account_id': '123456789',
                'enabled': True,
                'created_at': '2026-05-23T10:00:00',
                'updated_at': '2026-05-23T10:00:00',
            }
        }

        updated_rule = repository.update_rule('rule-1', {
            'priority': 9,
            'enabled': False,
        })

        assert updated_rule.priority == 9
        assert updated_rule.enabled is False
        mock_dynamodb_table.put_item.assert_called_once()

    def test_delete_rule(self, repository, mock_dynamodb_table):
        """Test deleting a rule"""
        mock_dynamodb_table.delete_item.return_value = {
            'Attributes': {'rule_id': 'rule-1'}
        }

        success = repository.delete_rule('rule-1')

        assert success is True
        mock_dynamodb_table.delete_item.assert_called_once_with(
            Key={'rule_id': 'rule-1'},
            ReturnValues='ALL_OLD',
        )

    def test_list_rules_by_type(self, repository, mock_dynamodb_table):
        """Test listing rules by type"""
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-1',
                    'rule_type': 'connection_spike',
                    'condition': json.dumps({'threshold': 10}),
                    'action': json.dumps({'notify': ['telegram']}),
                    'priority': 8,
                    'account_id': 'all',
                    'enabled': True,
                    'created_at': '2026-05-23T10:00:00',
                    'updated_at': '2026-05-23T10:00:00',
                },
                {
                    'rule_id': 'rule-2',
                    'rule_type': 'connection_spike',
                    'condition': json.dumps({'threshold': 20}),
                    'action': json.dumps({'notify': ['discord']}),
                    'priority': 5,
                    'account_id': 'all',
                    'enabled': False,
                    'created_at': '2026-05-23T10:01:00',
                    'updated_at': '2026-05-23T10:01:00',
                }
            ]
        }

        rules = repository.list_rules_by_type('connection_spike')

        assert len(rules) == 2
        assert rules[0].rule_id == 'rule-1'
        assert rules[1].rule_id == 'rule-2'

    def test_list_rules_by_account(self, repository, mock_dynamodb_table):
        """Test listing rules by account"""
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-1',
                    'rule_type': 'connection_spike',
                    'condition': json.dumps({}),
                    'action': json.dumps({}),
                    'priority': 8,
                    'account_id': '123456789',
                    'enabled': True,
                    'created_at': '2026-05-23T10:00:00',
                    'updated_at': '2026-05-23T10:00:00',
                }
            ]
        }

        rules = repository.list_rules_by_account('123456789')

        assert len(rules) == 1
        assert rules[0].account_id == '123456789'
        mock_dynamodb_table.query.assert_called_once()


class TestRuleManagementIntegration:
    """Integration tests for rule management"""

    def test_rule_lifecycle(self):
        """Test complete rule lifecycle: create, read, update, delete"""
        with patch('guardian.storage.security_rules.boto3.resource') as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            repo = SecurityRuleRepository('test-table')
            repo.table = mock_table

            # Create
            rule = SecurityRule(
                rule_id='',
                rule_type='auth_failure',
                condition={'threshold': 5},
                action={'notify': ['telegram']},
                priority=7,
                account_id='111111111111',
            )
            created = repo.create_rule(rule)
            assert created.rule_id is not None

            # Read
            mock_table.get_item.return_value = {
                'Item': {
                    'rule_id': created.rule_id,
                    'rule_type': 'auth_failure',
                    'condition': json.dumps({'threshold': 5}),
                    'action': json.dumps({'notify': ['telegram']}),
                    'priority': 7,
                    'account_id': '111111111111',
                    'enabled': True,
                    'created_at': created.created_at.isoformat(),
                    'updated_at': created.updated_at.isoformat(),
                }
            }
            fetched = repo.get_rule(created.rule_id)
            assert fetched.priority == 7

            # Update
            mock_table.get_item.return_value = {'Item': fetched.to_dynamodb_item()}
            updated = repo.update_rule(created.rule_id, {'priority': 9})
            assert updated.priority == 9

            # Delete
            mock_table.delete_item.return_value = {'Attributes': {}}
            success = repo.delete_rule(created.rule_id)
            assert success is True
