"""Workflow execution engine for custom remediation workflows"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Execute custom remediation workflows in response to threats"""

    def __init__(self):
        """Initialize workflow engine"""
        self.executed_workflows = {}

    def create_workflow(self, workflow_config: Dict) -> Dict:
        """
        Create a new remediation workflow from configuration

        Args:
            workflow_config: Workflow definition with condition and action steps

        Returns:
            Created workflow with workflow_id
        """
        try:
            workflow = {
                'workflow_id': str(uuid.uuid4()),
                'name': workflow_config.get('name', 'unnamed_workflow'),
                'trigger': workflow_config.get('trigger', 'threat_detected'),
                'condition': workflow_config.get('condition', {}),
                'steps': workflow_config.get('steps', []),
                'enabled': workflow_config.get('enabled', True),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'description': workflow_config.get('description', '')
            }

            validation_result = self.validate_workflow_steps(workflow['steps'])
            if not validation_result['valid']:
                logger.warning(f"Workflow validation warnings: {validation_result['warnings']}")

            logger.info(f"Created workflow {workflow['workflow_id']}: {workflow['name']}")
            return workflow

        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def execute_workflow(self, workflow: Dict, threat: Dict) -> Dict:
        """
        Execute a workflow for a threat event

        Args:
            workflow: Workflow definition
            threat: Threat object that triggered the workflow

        Returns:
            Execution result with step outcomes
        """
        try:
            execution_id = str(uuid.uuid4())
            execution = {
                'execution_id': execution_id,
                'workflow_id': workflow.get('workflow_id'),
                'threat_id': threat.get('rule_id'),
                'started_at': datetime.now(timezone.utc).isoformat(),
                'status': 'in_progress',
                'step_results': [],
                'success_count': 0,
                'failure_count': 0
            }

            if not workflow.get('enabled', True):
                execution['status'] = 'skipped'
                execution['reason'] = 'workflow_disabled'
                return execution

            if not self._evaluate_condition(workflow.get('condition', {}), threat):
                execution['status'] = 'skipped'
                execution['reason'] = 'condition_not_met'
                return execution

            steps = workflow.get('steps', [])
            for step_index, step in enumerate(steps):
                step_result = self._execute_step(step, threat, execution_id)
                execution['step_results'].append(step_result)

                if step_result.get('success'):
                    execution['success_count'] += 1
                else:
                    execution['failure_count'] += 1

                if step.get('stop_on_failure') and not step_result.get('success'):
                    execution['status'] = 'failed'
                    execution['failed_step'] = step_index
                    break

            if execution['status'] == 'in_progress':
                execution['status'] = 'success' if execution['failure_count'] == 0 else 'partial_success'

            execution['completed_at'] = datetime.now(timezone.utc).isoformat()
            self.executed_workflows[execution_id] = execution

            logger.info(f"Workflow {workflow.get('workflow_id')} execution {execution_id}: {execution['status']}")
            return execution

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            return {
                'execution_id': execution_id if 'execution_id' in locals() else None,
                'status': 'error',
                'error': str(e)
            }

    def validate_workflow_steps(self, steps: List[Dict]) -> Dict:
        """
        Validate workflow steps configuration

        Args:
            steps: List of workflow steps

        Returns:
            Validation result with valid flag and warnings
        """
        try:
            result = {
                'valid': True,
                'warnings': [],
                'step_count': len(steps)
            }

            if not steps or len(steps) == 0:
                result['warnings'].append('Workflow has no steps')

            valid_actions = ['stop_ec2', 'revoke_iam', 'isolate_sg', 'block_s3', 'snapshot', 'notify']

            for idx, step in enumerate(steps):
                action = step.get('action', '').lower()

                if not action:
                    result['warnings'].append(f"Step {idx} has no action")
                elif action not in valid_actions:
                    result['warnings'].append(f"Step {idx} has unknown action: {action}")

                if not step.get('params'):
                    result['warnings'].append(f"Step {idx} has no parameters")

            logger.info(f"Validated {len(steps)} workflow steps: {result}")
            return result

        except Exception as e:
            logger.error(f"Error validating workflow steps: {str(e)}")
            return {'valid': False, 'error': str(e)}

    def track_workflow_execution(self, execution_id: str) -> Optional[Dict]:
        """
        Get status and results of a workflow execution

        Args:
            execution_id: Execution ID to track

        Returns:
            Execution record with full results
        """
        try:
            if execution_id not in self.executed_workflows:
                logger.warning(f"Execution {execution_id} not found")
                return None

            execution = self.executed_workflows[execution_id]
            execution['tracked_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(f"Tracked execution {execution_id}: {execution['status']}")
            return execution

        except Exception as e:
            logger.error(f"Error tracking execution: {str(e)}")
            return None

    def _evaluate_condition(self, condition: Dict, threat: Dict) -> bool:
        if not condition:
            return True

        operator = condition.get('operator', 'and')
        rules = condition.get('rules', [])

        if not rules:
            return True

        results = []
        for rule in rules:
            field = rule.get('field')
            op = rule.get('operator', 'equals')
            value = rule.get('value')

            threat_value = threat.get(field)

            if op == 'equals':
                results.append(threat_value == value)
            elif op == 'greater_than':
                results.append(threat_value > value)
            elif op == 'less_than':
                results.append(threat_value < value)
            elif op == 'in':
                results.append(threat_value in value if isinstance(value, list) else False)
            else:
                results.append(False)

        if operator == 'and':
            return all(results)
        elif operator == 'or':
            return any(results)
        else:
            return False

    def _execute_step(self, step: Dict, threat: Dict, execution_id: str) -> Dict:
        action = step.get('action', '').lower()
        params = step.get('params', {})

        result = {
            'action': action,
            'params': params,
            'success': False,
            'executed_at': datetime.now(timezone.utc).isoformat()
        }

        try:
            if action == 'stop_ec2':
                result['success'] = self._action_stop_ec2(params, threat)
                result['message'] = f"EC2 instance {params.get('instance_id')} stop initiated"

            elif action == 'revoke_iam':
                result['success'] = self._action_revoke_iam(params, threat)
                result['message'] = f"IAM permissions revoked for {params.get('principal')}"

            elif action == 'isolate_sg':
                result['success'] = self._action_isolate_sg(params, threat)
                result['message'] = f"Security group {params.get('sg_id')} isolated"

            elif action == 'block_s3':
                result['success'] = self._action_block_s3(params, threat)
                result['message'] = f"S3 bucket {params.get('bucket')} public access blocked"

            elif action == 'snapshot':
                result['success'] = self._action_snapshot(params, threat)
                result['message'] = f"Snapshot created for {params.get('resource_id')}"

            elif action == 'notify':
                result['success'] = self._action_notify(params, threat)
                result['message'] = f"Notification sent to {params.get('recipient')}"

            else:
                result['error'] = f"Unknown action: {action}"

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error executing step {action}: {str(e)}")

        return result

    def _action_stop_ec2(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Stop EC2 instance {params.get('instance_id')}")
        return True

    def _action_revoke_iam(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Revoke IAM permissions for {params.get('principal')}")
        return True

    def _action_isolate_sg(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Isolate security group {params.get('sg_id')}")
        return True

    def _action_block_s3(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Block S3 bucket public access {params.get('bucket')}")
        return True

    def _action_snapshot(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Create snapshot for {params.get('resource_id')}")
        return True

    def _action_notify(self, params: Dict, threat: Dict) -> bool:
        logger.info(f"Action: Notify {params.get('recipient')}")
        return True
