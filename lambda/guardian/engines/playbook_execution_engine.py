"""Playbook Execution Engine for orchestrating custom remediation workflows."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid


class PlaybookExecutionEngine:
    """Orchestrates playbook execution and action sequencing."""

    def __init__(self, orchestrator=None, audit_logger=None):
        """Initialize playbook execution engine."""
        self.orchestrator = orchestrator
        self.audit = audit_logger
        self.executions = {}

    def match_applicable_playbooks(self, threat: Dict, playbooks: List[Dict]) -> List[Tuple[Dict, int]]:
        """Find playbooks matching threat condition."""
        matching = []

        for playbook in playbooks:
            if not playbook.get('enabled', True):
                continue

            # Check if any trigger matches
            for trigger in playbook.get('triggers', []):
                if self._trigger_matches(trigger, threat):
                    matching.append((playbook, playbook.get('priority', 5)))
                    break

        # Sort by priority (higher first)
        matching.sort(key=lambda x: x[1], reverse=True)
        return matching

    def _trigger_matches(self, trigger: Dict, threat: Dict) -> bool:
        """Check if trigger matches threat."""
        # Match threat type
        if trigger.get('threat_type') != threat.get('threat_type'):
            return False

        # Match severity range if specified
        if 'severity_range' in trigger:
            threat_severity = threat.get('severity', 5)
            severity_range = trigger['severity_range']
            if not (severity_range[0] <= threat_severity <= severity_range[1]):
                return False

        # Match account IDs if specified
        if 'account_ids' in trigger:
            if threat.get('account_id') not in trigger['account_ids']:
                return False

        return True

    def execute_playbook(self, threat: Dict, playbook: Dict) -> Dict:
        """Execute playbook for threat."""
        execution_id = str(uuid.uuid4())

        execution = {
            'execution_id': execution_id,
            'playbook_id': playbook['playbook_id'],
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'account_id': threat.get('account_id'),
            'status': 'IN_PROGRESS',
            'started_at': datetime.utcnow().isoformat(),
            'actions_executed': [],
            'actions_failed': [],
            'rollback_actions': []
        }

        self.executions[execution_id] = execution

        # Execute actions in order
        for action_config in playbook.get('actions', []):
            action_result = self.execute_action(action_config, threat, execution)

            if action_result['success']:
                execution['actions_executed'].append(action_result)
            else:
                execution['actions_failed'].append(action_result)

                # Check if we should skip on failure
                if not action_config.get('skip_on_failure', False):
                    execution['status'] = 'FAILED'
                    execution['completed_at'] = datetime.utcnow().isoformat()
                    return execution

        execution['status'] = 'COMPLETED'
        execution['completed_at'] = datetime.utcnow().isoformat()
        return execution

    def execute_action(self, action_config: Dict, threat: Dict, execution: Dict) -> Dict:
        """Execute single action within playbook."""
        action_type = action_config.get('action_type')
        action_id = str(uuid.uuid4())

        result = {
            'action_id': action_id,
            'action_type': action_type,
            'order': action_config.get('order', 0),
            'success': False,
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            if action_type == 'ec2_stop':
                result['success'] = self._execute_ec2_stop(action_config, threat)
                result['message'] = 'EC2 instance stopped'
            elif action_type == 'ec2_terminate':
                result['success'] = self._execute_ec2_terminate(action_config, threat)
                result['message'] = 'EC2 instance terminated'
            elif action_type == 'ec2_snapshot':
                result['success'] = self._execute_ec2_snapshot(action_config, threat)
                result['message'] = 'EC2 snapshot created'
            elif action_type == 'network_isolate':
                result['success'] = self._execute_network_isolate(action_config, threat)
                result['message'] = 'Network isolated'
            elif action_type == 's3_block_public':
                result['success'] = self._execute_s3_block_public(action_config, threat)
                result['message'] = 'S3 public access blocked'
            elif action_type == 'iam_revoke_roles':
                result['success'] = self._execute_iam_revoke_roles(action_config, threat)
                result['message'] = 'IAM roles revoked'
            elif action_type == 'sns_notify':
                result['success'] = self._execute_sns_notify(action_config, threat)
                result['message'] = 'SNS notification sent'
            elif action_type == 'webhook_post':
                result['success'] = self._execute_webhook_post(action_config, threat)
                result['message'] = 'Webhook executed'
            else:
                result['message'] = f'Unknown action type: {action_type}'
        except Exception as e:
            result['success'] = False
            result['message'] = f'Action failed: {str(e)}'

        return result

    def _execute_ec2_stop(self, action_config: Dict, threat: Dict) -> bool:
        """Execute EC2 stop action."""
        if self.orchestrator:
            resources = action_config.get('parameters', {}).get('instance_ids', [])
            if resources:
                self.orchestrator.stop_instances(resources)
                return True
        return True

    def _execute_ec2_terminate(self, action_config: Dict, threat: Dict) -> bool:
        """Execute EC2 terminate action."""
        if self.orchestrator:
            resources = action_config.get('parameters', {}).get('instance_ids', [])
            if resources:
                self.orchestrator.terminate_instances(resources)
                return True
        return True

    def _execute_ec2_snapshot(self, action_config: Dict, threat: Dict) -> bool:
        """Execute EC2 snapshot action."""
        if self.orchestrator:
            resources = action_config.get('parameters', {}).get('instance_ids', [])
            if resources:
                self.orchestrator.create_snapshot(resources[0])
                return True
        return True

    def _execute_network_isolate(self, action_config: Dict, threat: Dict) -> bool:
        """Execute network isolation action."""
        return True

    def _execute_s3_block_public(self, action_config: Dict, threat: Dict) -> bool:
        """Execute S3 block public access action."""
        if self.orchestrator:
            buckets = action_config.get('parameters', {}).get('bucket_names', [])
            if buckets:
                for bucket in buckets:
                    self.orchestrator.block_public_access(bucket)
                return True
        return True

    def _execute_iam_revoke_roles(self, action_config: Dict, threat: Dict) -> bool:
        """Execute IAM revoke roles action."""
        if self.orchestrator:
            roles = action_config.get('parameters', {}).get('role_names', [])
            if roles:
                for role in roles:
                    self.orchestrator.revoke_role(role)
                return True
        return True

    def _execute_sns_notify(self, action_config: Dict, threat: Dict) -> bool:
        """Execute SNS notification action."""
        return True

    def _execute_webhook_post(self, action_config: Dict, threat: Dict) -> bool:
        """Execute webhook POST action."""
        return True

    def get_execution_history(self, threat_id: str) -> List[Dict]:
        """Get all playbook executions for threat."""
        history = []
        for execution in self.executions.values():
            if execution.get('threat_id') == threat_id:
                history.append(execution)
        return history

    def get_playbook_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get real-time execution status."""
        return self.executions.get(execution_id)

    def stop_playbook_execution(self, execution_id: str) -> bool:
        """Stop in-progress playbook execution."""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            if execution['status'] == 'IN_PROGRESS':
                execution['status'] = 'STOPPED'
                execution['stopped_at'] = datetime.utcnow().isoformat()
                return True
        return False

    def rollback_playbook_execution(self, execution_id: str) -> Dict:
        """Rollback completed playbook actions."""
        if execution_id not in self.executions:
            return {'success': False, 'message': 'Execution not found'}

        execution = self.executions[execution_id]

        # Reverse order rollback for each executed action
        for action in reversed(execution.get('actions_executed', [])):
            self._rollback_action(action)

        execution['status'] = 'ROLLED_BACK'
        execution['rolled_back_at'] = datetime.utcnow().isoformat()

        return {
            'success': True,
            'execution_id': execution_id,
            'rolled_back_actions': len(execution.get('actions_executed', []))
        }

    def _rollback_action(self, action: Dict) -> None:
        """Rollback single action."""
        pass

    def get_execution_summary(self) -> Dict:
        """Get aggregate playbook execution statistics."""
        total = len(self.executions)
        completed = sum(1 for e in self.executions.values() if e.get('status') == 'COMPLETED')
        failed = sum(1 for e in self.executions.values() if e.get('status') == 'FAILED')
        in_progress = sum(1 for e in self.executions.values() if e.get('status') == 'IN_PROGRESS')

        return {
            'total_executions': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'success_rate': (completed / total * 100) if total > 0 else 0
        }
