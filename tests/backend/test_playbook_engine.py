"""Sprint 56 Phase 1: Playbook Engine Tests (8 backend tests)"""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock
import pytest
from guardian.services.playbook_definition_service import PlaybookDefinitionService
from guardian.engines.playbook_execution_engine import PlaybookExecutionEngine
from guardian.services.playbook_builder_service import PlaybookBuilderService
from guardian.services.playbook_approval_service import PlaybookApprovalService


class TestPlaybookDefinitionService:
    """Playbook definition and management tests."""

    def test_create_playbook(self):
        """✅ Create new remediation playbook."""
        service = PlaybookDefinitionService()

        triggers = [
            {
                'threat_type': 'Unauthorized EC2',
                'severity_range': [7, 10]
            }
        ]

        actions = [
            {
                'order': 1,
                'action_type': 'ec2_stop',
                'parameters': {'instance_ids': ['i-12345']},
                'skip_on_failure': True
            }
        ]

        playbook = service.create_playbook(
            name='EC2 Unauthorized Response',
            description='Respond to unauthorized EC2 detection',
            triggers=triggers,
            actions=actions,
            priority=5
        )

        assert playbook['playbook_id'] is not None
        assert playbook['name'] == 'EC2 Unauthorized Response'
        assert playbook['enabled'] is True
        assert playbook['priority'] == 5
        assert len(playbook['triggers']) == 1
        assert len(playbook['actions']) == 1
        assert 'created_at' in playbook

    def test_update_playbook(self):
        """✅ Update existing playbook."""
        service = PlaybookDefinitionService()

        # Create playbook
        playbook = service.create_playbook(
            name='Original Name',
            description='Original description',
            triggers=[],
            actions=[],
            priority=5
        )

        # Update playbook
        updated = service.update_playbook(
            playbook['playbook_id'],
            {'name': 'Updated Name', 'priority': 8}
        )

        assert updated['name'] == 'Updated Name'
        assert updated['priority'] == 8
        assert updated['updated_at'] is not None

    def test_validate_playbook(self):
        """✅ Validate playbook structure."""
        service = PlaybookDefinitionService()

        # Valid playbook
        valid_playbook = {
            'name': 'Valid Playbook',
            'triggers': [{'threat_type': 'Test', 'severity_range': [5, 10]}],
            'actions': [{'action_type': 'ec2_stop', 'order': 1}],
            'priority': 5
        }

        result = service.validate_playbook(valid_playbook)
        assert result['is_valid'] is True
        assert len(result['errors']) == 0

        # Invalid playbook (missing name)
        invalid_playbook = {
            'triggers': [{'threat_type': 'Test'}],
            'actions': [{'action_type': 'ec2_stop'}],
            'priority': 5
        }

        result = service.validate_playbook(invalid_playbook)
        assert result['is_valid'] is False
        assert 'name' in str(result['errors'])


class TestPlaybookExecutionEngine:
    """Playbook execution and action sequencing tests."""

    def test_match_applicable_playbooks(self):
        """✅ Find playbooks matching threat."""
        service = PlaybookDefinitionService()
        engine = PlaybookExecutionEngine()

        # Create playbook
        playbook = service.create_playbook(
            name='Test Playbook',
            description='Test',
            triggers=[
                {
                    'threat_type': 'Unauthorized EC2',
                    'severity_range': [7, 10]
                }
            ],
            actions=[],
            priority=5
        )

        # Threat that matches
        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 8
        }

        playbooks = [playbook]
        matching = engine.match_applicable_playbooks(threat, playbooks)

        assert len(matching) == 1
        assert matching[0][0]['playbook_id'] == playbook['playbook_id']
        assert matching[0][1] == 5  # priority

    def test_execute_playbook(self):
        """✅ Execute playbook for threat."""
        service = PlaybookDefinitionService()
        engine = PlaybookExecutionEngine()

        playbook = service.create_playbook(
            name='Test Playbook',
            description='Test',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_stop',
                    'parameters': {'instance_ids': ['i-12345']},
                    'skip_on_failure': True
                }
            ],
            priority=5
        )

        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Test',
            'severity': 7
        }

        execution = engine.execute_playbook(threat, playbook)

        assert execution['status'] == 'COMPLETED'
        assert execution['playbook_id'] == playbook['playbook_id']
        assert 'started_at' in execution
        assert 'completed_at' in execution

    def test_execute_action_sequence(self):
        """✅ Execute action sequence in order."""
        service = PlaybookDefinitionService()
        engine = PlaybookExecutionEngine()

        playbook = service.create_playbook(
            name='Multi-Action Playbook',
            description='Test',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_snapshot',
                    'skip_on_failure': True
                },
                {
                    'order': 2,
                    'action_type': 'ec2_stop',
                    'skip_on_failure': False
                },
                {
                    'order': 3,
                    'action_type': 'sns_notify',
                    'skip_on_failure': True
                }
            ],
            priority=5
        )

        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Test',
            'severity': 8
        }

        execution = engine.execute_playbook(threat, playbook)

        assert len(execution['actions_executed']) == 3
        # Verify order
        assert execution['actions_executed'][0]['order'] == 1
        assert execution['actions_executed'][1]['order'] == 2
        assert execution['actions_executed'][2]['order'] == 3

    def test_rollback_playbook_execution(self):
        """✅ Rollback completed actions."""
        service = PlaybookDefinitionService()
        engine = PlaybookExecutionEngine()

        playbook = service.create_playbook(
            name='Test Playbook',
            description='Test',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_stop',
                    'skip_on_failure': True
                }
            ],
            priority=5
        )

        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Test',
            'severity': 7
        }

        execution = engine.execute_playbook(threat, playbook)
        execution_id = execution['execution_id']

        rollback = engine.rollback_playbook_execution(execution_id)

        assert rollback['success'] is True
        assert execution_id in rollback['execution_id']


class TestPlaybookBuilderService:
    """Playbook builder and templates tests."""

    def test_get_action_templates(self):
        """✅ Return available action templates."""
        builder = PlaybookBuilderService()

        templates = builder.get_action_templates()

        assert 'ec2_stop' in templates
        assert 'ec2_terminate' in templates
        assert 's3_block_public' in templates
        assert 'iam_revoke_roles' in templates
        assert 'webhook_post' in templates

        # Check structure
        assert templates['ec2_stop']['name'] == 'Stop EC2 Instance'
        assert templates['ec2_stop']['category'] == 'compute'
        assert 'parameters' in templates['ec2_stop']

        # Check validation
        result = builder.validate_action('ec2_stop', {'instance_ids': ['i-123']})
        assert result['is_valid'] is True

        # Invalid action type
        result = builder.validate_action('unknown_action', {})
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
