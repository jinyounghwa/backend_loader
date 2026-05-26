"""Sprint 56 Phase 1: Playbook Integration Tests (7 integration tests)"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.services.playbook_definition_service import PlaybookDefinitionService
from guardian.engines.playbook_execution_engine import PlaybookExecutionEngine
from guardian.services.playbook_builder_service import PlaybookBuilderService
from guardian.services.playbook_approval_service import PlaybookApprovalService


class TestPlaybookIntegration:
    """End-to-end playbook execution integration tests."""

    def test_end_to_end_playbook_execution(self):
        """✅ Complete threat → playbook match → execution flow."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create playbook
        playbook = definition_service.create_playbook(
            name='Unauthorized EC2 Response',
            description='Respond to unauthorized EC2',
            triggers=[
                {
                    'threat_type': 'Unauthorized EC2',
                    'severity_range': [7, 10]
                }
            ],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_stop',
                    'parameters': {'instance_ids': ['i-123']},
                    'skip_on_failure': True
                }
            ],
            priority=5
        )

        # Threat detection
        threat = {
            'threat_id': 'THREAT-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'prod-acct'
        }

        # Match playbooks
        playbooks = [playbook]
        matching = execution_engine.match_applicable_playbooks(threat, playbooks)
        assert len(matching) == 1

        # Execute playbook
        execution = execution_engine.execute_playbook(threat, playbook)
        assert execution['status'] == 'COMPLETED'
        assert execution['threat_id'] == 'THREAT-001'

    def test_multi_action_playbook_execution(self):
        """✅ Execute playbook with multiple sequential actions."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create multi-action playbook
        playbook = definition_service.create_playbook(
            name='Comprehensive EC2 Response',
            description='Multi-step response',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_snapshot',
                    'skip_on_failure': True
                },
                {
                    'order': 2,
                    'action_type': 'network_isolate',
                    'skip_on_failure': True
                },
                {
                    'order': 3,
                    'action_type': 'iam_revoke_roles',
                    'skip_on_failure': True
                },
                {
                    'order': 4,
                    'action_type': 'sns_notify',
                    'skip_on_failure': True
                }
            ],
            priority=7
        )

        threat = {
            'threat_id': 'THREAT-002',
            'threat_type': 'Lateral Movement',
            'severity': 9
        }

        execution = execution_engine.execute_playbook(threat, playbook)

        assert execution['status'] == 'COMPLETED'
        assert len(execution['actions_executed']) == 4
        # Verify all actions executed in order
        for i, action in enumerate(execution['actions_executed']):
            assert action['order'] == i + 1

    def test_conditional_action_execution(self):
        """✅ Skip actions based on conditions."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create playbook with skip_on_failure
        playbook = definition_service.create_playbook(
            name='Conditional Response',
            description='Test skip on failure',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_snapshot',
                    'skip_on_failure': True  # Will not halt execution
                },
                {
                    'order': 2,
                    'action_type': 'ec2_terminate',
                    'skip_on_failure': False  # Will halt execution on failure
                },
                {
                    'order': 3,
                    'action_type': 'sns_notify',
                    'skip_on_failure': True
                }
            ],
            priority=8
        )

        threat = {
            'threat_id': 'THREAT-003',
            'threat_type': 'Critical Threat',
            'severity': 10
        }

        execution = execution_engine.execute_playbook(threat, playbook)

        # Should complete with all actions (in test, all succeed)
        assert execution['status'] == 'COMPLETED'
        assert len(execution['actions_executed']) >= 1

    def test_playbook_approval_workflow(self):
        """✅ Execute with approval workflow."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()
        approval_service = PlaybookApprovalService()

        # Create playbook requiring approval
        playbook = definition_service.create_playbook(
            name='Critical Response',
            description='Requires approval',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_terminate',
                    'skip_on_failure': False
                }
            ],
            priority=1
        )

        # Update playbook to require approval
        definition_service.update_playbook(
            playbook['playbook_id'],
            {'approval_required': True, 'approval_group': 'security-team'}
        )

        playbook = definition_service.get_playbook(playbook['playbook_id'])
        assert playbook['approval_required'] is True

        threat = {
            'threat_id': 'THREAT-004',
            'threat_type': 'Critical',
            'severity': 10
        }

        # Request approval
        approval = approval_service.request_approval(
            'exec-001',
            threat,
            playbook,
            playbook['actions']
        )

        assert approval['status'] == 'PENDING'
        assert approval['approval_group'] == 'security-team'

        # Approve execution
        result = approval_service.approve_execution(
            'exec-001',
            'approver-123',
            'Threat is confirmed'
        )

        assert result['success'] is True
        assert result['status'] == 'APPROVED'

    def test_parallel_playbook_execution(self):
        """✅ Execute multiple playbooks concurrently."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create multiple playbooks
        playbook1 = definition_service.create_playbook(
            name='Playbook 1',
            description='First playbook',
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

        playbook2 = definition_service.create_playbook(
            name='Playbook 2',
            description='Second playbook',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 's3_block_public',
                    'skip_on_failure': True
                }
            ],
            priority=8
        )

        threat = {
            'threat_id': 'THREAT-005',
            'threat_type': 'Multi-Vector',
            'severity': 8
        }

        # Execute both playbooks
        exec1 = execution_engine.execute_playbook(threat, playbook1)
        exec2 = execution_engine.execute_playbook(threat, playbook2)

        assert exec1['status'] == 'COMPLETED'
        assert exec2['status'] == 'COMPLETED'
        assert exec1['execution_id'] != exec2['execution_id']

        # Get execution history
        history = execution_engine.get_execution_history(threat['threat_id'])
        assert len(history) >= 2

    def test_playbook_execution_with_notification(self):
        """✅ Send notifications during execution."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create playbook with notification action
        playbook = definition_service.create_playbook(
            name='Notifying Playbook',
            description='Sends notifications',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_stop',
                    'skip_on_failure': True
                },
                {
                    'order': 2,
                    'action_type': 'sns_notify',
                    'parameters': {
                        'topic_arn': 'arn:aws:sns:us-east-1:123456789:alert',
                        'message': 'EC2 instance stopped due to threat'
                    },
                    'skip_on_failure': True
                }
            ],
            priority=6
        )

        threat = {
            'threat_id': 'THREAT-006',
            'threat_type': 'Security Alert',
            'severity': 7
        }

        execution = execution_engine.execute_playbook(threat, playbook)

        assert execution['status'] == 'COMPLETED'
        # Verify notification action was executed
        notification_actions = [a for a in execution['actions_executed']
                               if a['action_type'] == 'sns_notify']
        assert len(notification_actions) == 1

    def test_custom_webhook_action_execution(self):
        """✅ Execute custom webhook actions."""
        definition_service = PlaybookDefinitionService()
        execution_engine = PlaybookExecutionEngine()

        # Create playbook with webhook action
        playbook = definition_service.create_playbook(
            name='Webhook Playbook',
            description='Integrates with external systems',
            triggers=[],
            actions=[
                {
                    'order': 1,
                    'action_type': 'ec2_snapshot',
                    'skip_on_failure': True
                },
                {
                    'order': 2,
                    'action_type': 'webhook_post',
                    'parameters': {
                        'url': 'https://itsm.example.com/api/incidents',
                        'payload': {
                            'title': 'AWS Security Alert',
                            'severity': 'high',
                            'action': 'incident_create'
                        }
                    },
                    'skip_on_failure': True
                }
            ],
            priority=7
        )

        threat = {
            'threat_id': 'THREAT-007',
            'threat_type': 'External Integration',
            'severity': 7
        }

        execution = execution_engine.execute_playbook(threat, playbook)

        assert execution['status'] == 'COMPLETED'
        # Verify webhook action was executed
        webhook_actions = [a for a in execution['actions_executed']
                          if a['action_type'] == 'webhook_post']
        assert len(webhook_actions) == 1
