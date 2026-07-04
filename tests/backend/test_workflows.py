"""Tests for custom remediation workflows - Phase 2 of Sprint 44"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import sys
import os
from guardian.workflows.workflow_engine import WorkflowEngine
from guardian.workflows.workflow_repository import WorkflowRepository
from guardian.actions.remediation_actions import RemediationActions


class TestWorkflowDefinition:
    """Group 1: Workflow definition and validation tests"""

    @pytest.fixture
    def workflow_engine(self):
        return WorkflowEngine()

    @pytest.fixture
    def sample_workflow_config(self):
        return {
            'name': 'Stop Compromised EC2',
            'trigger': 'high_risk_api_call',
            'trigger_threat_type': 'unauthorized_action',
            'condition': {
                'operator': 'and',
                'rules': [
                    {
                        'field': 'severity',
                        'operator': 'greater_than',
                        'value': 7
                    },
                    {
                        'field': 'threat_type',
                        'operator': 'equals',
                        'value': 'unauthorized_action'
                    }
                ]
            },
            'steps': [
                {
                    'action': 'stop_ec2',
                    'params': {'instance_id': 'i-1234567890abcdef0', 'force': True}
                },
                {
                    'action': 'snapshot',
                    'params': {'resource_id': 'i-1234567890abcdef0', 'retention_days': 30}
                }
            ]
        }

    def test_create_workflow(self, workflow_engine, sample_workflow_config):
        """Test workflow creation from configuration"""
        workflow = workflow_engine.create_workflow(sample_workflow_config)

        assert 'workflow_id' in workflow
        assert workflow['name'] == 'Stop Compromised EC2'
        assert workflow['enabled'] is True
        assert len(workflow['steps']) == 2

    def test_create_workflow_with_validation(self, workflow_engine):
        """Test workflow creation with step validation"""
        config = {
            'name': 'Test Workflow',
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}},
                {'action': 'invalid_action', 'params': {}}
            ]
        }

        workflow = workflow_engine.create_workflow(config)

        assert 'workflow_id' in workflow
        assert workflow['enabled'] is True

    def test_validate_workflow_steps_success(self, workflow_engine):
        """Test successful workflow step validation"""
        steps = [
            {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}},
            {'action': 'snapshot', 'params': {'resource_id': 'i-123'}},
            {'action': 'notify', 'params': {'recipient': 'admin@example.com'}}
        ]

        result = workflow_engine.validate_workflow_steps(steps)

        assert result['valid'] is True
        assert result['step_count'] == 3

    def test_validate_workflow_steps_with_warnings(self, workflow_engine):
        """Test workflow validation with warnings"""
        steps = [
            {'action': 'stop_ec2', 'params': {}},
            {'action': 'unknown_action', 'params': {'key': 'value'}}
        ]

        result = workflow_engine.validate_workflow_steps(steps)

        assert len(result['warnings']) > 0

    def test_validate_empty_workflow(self, workflow_engine):
        """Test validation of workflow with no steps"""
        steps = []

        result = workflow_engine.validate_workflow_steps(steps)

        assert len(result['warnings']) > 0


class TestWorkflowExecution:
    """Group 2: EC2/IAM/S3 automatic response execution tests"""

    @pytest.fixture
    def workflow_engine(self):
        return WorkflowEngine()

    @pytest.fixture
    def ec2_workflow(self):
        return {
            'workflow_id': 'wf-ec2-001',
            'name': 'Stop EC2',
            'enabled': True,
            'condition': {
                'operator': 'and',
                'rules': [
                    {'field': 'severity', 'operator': 'greater_than', 'value': 6}
                ]
            },
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

    @pytest.fixture
    def iam_workflow(self):
        return {
            'workflow_id': 'wf-iam-001',
            'name': 'Revoke IAM',
            'enabled': True,
            'steps': [
                {
                    'action': 'revoke_iam',
                    'params': {'principal': 'arn:aws:iam::123:user/admin'}
                }
            ]
        }

    @pytest.fixture
    def s3_workflow(self):
        return {
            'workflow_id': 'wf-s3-001',
            'name': 'Block S3',
            'enabled': True,
            'steps': [
                {'action': 'block_s3', 'params': {'bucket': 'my-bucket'}}
            ]
        }

    def test_execute_ec2_workflow(self, workflow_engine, ec2_workflow):
        """Test EC2 stop action execution"""
        threat = {
            'rule_id': 'rule_123',
            'severity': 8,
            'threat_type': 'unauthorized_action'
        }

        result = workflow_engine.execute_workflow(ec2_workflow, threat)

        assert result['status'] in ['success', 'partial_success']
        assert len(result['step_results']) > 0
        assert result['step_results'][0]['action'] == 'stop_ec2'

    def test_execute_iam_workflow(self, workflow_engine, iam_workflow):
        """Test IAM revocation action execution"""
        threat = {
            'rule_id': 'rule_456',
            'severity': 7,
            'threat_type': 'iam_privilege_escalation'
        }

        result = workflow_engine.execute_workflow(iam_workflow, threat)

        assert result['status'] in ['success', 'partial_success']
        assert len(result['step_results']) > 0
        assert result['step_results'][0]['action'] == 'revoke_iam'

    def test_execute_s3_workflow(self, workflow_engine, s3_workflow):
        """Test S3 public access blocking action"""
        threat = {
            'rule_id': 'rule_789',
            'severity': 9,
            'threat_type': 's3_public_access'
        }

        result = workflow_engine.execute_workflow(s3_workflow, threat)

        assert result['status'] in ['success', 'partial_success']
        assert len(result['step_results']) > 0


class TestConditionEvaluation:
    """Group 3: Condition evaluation and action chaining tests"""

    @pytest.fixture
    def workflow_engine(self):
        return WorkflowEngine()

    def test_evaluate_simple_condition(self, workflow_engine):
        """Test simple condition evaluation (severity > 7)"""
        workflow = {
            'workflow_id': 'wf-cond-001',
            'enabled': True,
            'condition': {
                'rules': [
                    {'field': 'severity', 'operator': 'greater_than', 'value': 7}
                ]
            },
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

        threat_high = {'rule_id': 'r1', 'severity': 8}
        threat_low = {'rule_id': 'r2', 'severity': 6}

        result_high = workflow_engine.execute_workflow(workflow, threat_high)
        result_low = workflow_engine.execute_workflow(workflow, threat_low)

        assert result_high['status'] in ['success', 'partial_success']
        assert result_low['status'] == 'skipped'

    def test_evaluate_compound_condition_and(self, workflow_engine):
        """Test compound AND condition"""
        workflow = {
            'workflow_id': 'wf-and-001',
            'enabled': True,
            'condition': {
                'operator': 'and',
                'rules': [
                    {'field': 'severity', 'operator': 'greater_than', 'value': 7},
                    {'field': 'threat_type', 'operator': 'equals', 'value': 'ec2_abuse'}
                ]
            },
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

        threat_match = {
            'rule_id': 'r1',
            'severity': 8,
            'threat_type': 'ec2_abuse'
        }
        threat_partial = {
            'rule_id': 'r2',
            'severity': 8,
            'threat_type': 'other_threat'
        }

        result_match = workflow_engine.execute_workflow(workflow, threat_match)
        result_partial = workflow_engine.execute_workflow(workflow, threat_partial)

        assert result_match['status'] in ['success', 'partial_success']
        assert result_partial['status'] == 'skipped'

    def test_action_chain_execution(self, workflow_engine):
        """Test execution of chained actions"""
        workflow = {
            'workflow_id': 'wf-chain-001',
            'enabled': True,
            'condition': {'rules': []},
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}},
                {'action': 'snapshot', 'params': {'resource_id': 'i-123'}},
                {'action': 'notify', 'params': {'recipient': 'admin@example.com'}}
            ]
        }

        threat = {'rule_id': 'r1', 'severity': 8}
        result = workflow_engine.execute_workflow(workflow, threat)

        assert result['success_count'] == 3
        assert result['failure_count'] == 0
        assert len(result['step_results']) == 3


class TestWorkflowTracking:
    """Group 4: Workflow tracking and execution history tests"""

    @pytest.fixture
    def workflow_engine(self):
        return WorkflowEngine()

    def test_track_workflow_execution(self, workflow_engine):
        """Test tracking of workflow execution"""
        workflow = {
            'workflow_id': 'wf-track-001',
            'enabled': True,
            'condition': {'rules': []},
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

        threat = {'rule_id': 'r1', 'severity': 8}
        execution = workflow_engine.execute_workflow(workflow, threat)

        tracked = workflow_engine.track_workflow_execution(execution['execution_id'])

        assert tracked is not None
        assert tracked['workflow_id'] == 'wf-track-001'
        assert 'tracked_at' in tracked

    def test_workflow_execution_timestamps(self, workflow_engine):
        """Test execution timestamps tracking"""
        workflow = {
            'workflow_id': 'wf-time-001',
            'enabled': True,
            'condition': {'rules': []},
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

        threat = {'rule_id': 'r1', 'severity': 8}
        execution = workflow_engine.execute_workflow(workflow, threat)

        assert 'started_at' in execution
        assert 'completed_at' in execution
        assert execution['status'] in ['success', 'partial_success', 'skipped']

    def test_disabled_workflow_skipped(self, workflow_engine):
        """Test disabled workflow is not executed"""
        workflow = {
            'workflow_id': 'wf-disabled-001',
            'enabled': False,
            'condition': {'rules': []},
            'steps': [
                {'action': 'stop_ec2', 'params': {'instance_id': 'i-123'}}
            ]
        }

        threat = {'rule_id': 'r1', 'severity': 8}
        execution = workflow_engine.execute_workflow(workflow, threat)

        assert execution['status'] == 'skipped'
        assert execution['reason'] == 'workflow_disabled'


class TestWorkflowRepository:
    """Bonus: Workflow repository operations"""

    @pytest.fixture
    def repository(self):
        return WorkflowRepository()

    def test_save_and_retrieve_workflow(self, repository):
        """Test saving and retrieving workflows"""
        workflow = {
            'workflow_id': 'wf-repo-001',
            'name': 'Test Workflow',
            'trigger_threat_type': 'ec2_abuse',
            'steps': []
        }

        save_result = repository.save_workflow(workflow)
        retrieved = repository.get_workflow('wf-repo-001')

        assert save_result is True
        assert retrieved is not None
        assert retrieved['name'] == 'Test Workflow'

    def test_list_workflows_by_threat_type(self, repository):
        """Test retrieving workflows by threat type"""
        workflow1 = {
            'workflow_id': 'wf-1',
            'trigger_threat_type': 'ec2_abuse',
            'steps': []
        }
        workflow2 = {
            'workflow_id': 'wf-2',
            'trigger_threat_type': 'ec2_abuse',
            'steps': []
        }
        workflow3 = {
            'workflow_id': 'wf-3',
            'trigger_threat_type': 's3_public',
            'steps': []
        }

        repository.save_workflow(workflow1)
        repository.save_workflow(workflow2)
        repository.save_workflow(workflow3)

        ec2_workflows = repository.list_workflows_by_threat_type('ec2_abuse')
        s3_workflows = repository.list_workflows_by_threat_type('s3_public')

        assert len(ec2_workflows) == 2
        assert len(s3_workflows) == 1

    def test_update_workflow(self, repository):
        """Test updating workflow configuration"""
        workflow = {
            'workflow_id': 'wf-update-001',
            'name': 'Original Name',
            'trigger_threat_type': 'ec2_abuse',
            'enabled': True,
            'steps': []
        }

        repository.save_workflow(workflow)
        result = repository.update_workflow('wf-update-001', {'name': 'Updated Name', 'enabled': False})

        updated = repository.get_workflow('wf-update-001')

        assert result is True
        assert updated['name'] == 'Updated Name'
        assert updated['enabled'] is False

    def test_delete_workflow(self, repository):
        """Test deleting workflow from repository"""
        workflow = {
            'workflow_id': 'wf-delete-001',
            'trigger_threat_type': 'ec2_abuse',
            'steps': []
        }

        repository.save_workflow(workflow)
        result = repository.delete_workflow('wf-delete-001')
        retrieved = repository.get_workflow('wf-delete-001')

        assert result is True
        assert retrieved is None


class TestRemediationActions:
    """Bonus: Automated remediation action tests"""

    @pytest.fixture
    def remediation_actions(self):
        return RemediationActions()

    def test_stop_ec2_action(self, remediation_actions):
        """Test EC2 stop action"""
        result = remediation_actions.stop_ec2_instance('i-123456', force=True)

        assert result['status'] == 'success'
        assert result['instance_id'] == 'i-123456'
        assert result['force'] is True

    def test_revoke_iam_action(self, remediation_actions):
        """Test IAM permission revocation"""
        permissions = ['s3:GetObject', 's3:PutObject']
        result = remediation_actions.revoke_iam_permissions('arn:aws:iam::123:user/admin', permissions)

        assert result['status'] == 'success'
        assert result['count'] == 2

    def test_isolate_security_group(self, remediation_actions):
        """Test security group isolation"""
        result = remediation_actions.isolate_security_group('sg-123456')

        assert result['status'] == 'success'
        assert result['isolation_method'] == 'remove_outbound_rules'

    def test_block_s3_public_access(self, remediation_actions):
        """Test S3 public access blocking"""
        result = remediation_actions.delete_public_s3_access('my-bucket')

        assert result['status'] == 'success'
        assert result['changes']['BlockPublicAcls'] is True

    def test_backup_and_snapshot(self, remediation_actions):
        """Test resource backup creation"""
        result = remediation_actions.backup_and_snapshot('i-123456', 'ec2')

        assert result['status'] == 'success'
        assert 'snapshot_id' in result
        assert result['resource_type'] == 'ec2'

    def test_action_history(self, remediation_actions):
        """Test action history tracking"""
        remediation_actions.stop_ec2_instance('i-111')
        remediation_actions.stop_ec2_instance('i-222')
        remediation_actions.revoke_iam_permissions('principal', ['perm1'])

        history = remediation_actions.get_action_history(limit=10)

        assert len(history) == 3
        assert history[-1]['action_type'] == 'revoke_iam'
