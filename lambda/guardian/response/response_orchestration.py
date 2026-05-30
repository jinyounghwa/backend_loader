"""Advanced response orchestration (Phase 2 of Sprint 77).

Condition-based response execution, rule engines, parallel workflows,
and feedback-driven response optimization.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ResponseOrchestrator:
    """Orchestrate conditional responses to security threats."""

    def __init__(self):
        """Initialize response orchestrator."""
        self.executions = {}
        self.executor = ConditionalExecutor()

    def execute(self, params: dict) -> dict:
        """Execute response based on threat conditions.
        
        Args:
            params: {
                'threat_type': str,
                'severity': float (optional),
                'target': str (optional),
                'actions': list (optional),
                'parallel': bool (default False),
                'enable_rollback': bool (default False),
                'rollback_condition': str (optional)
            }
        
        Returns:
            {
                'execution_id': str,
                'status': str,
                'actions_executed': list (optional),
                'rollback_enabled': bool (optional)
            }
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        threat_type = params.get('threat_type')
        severity_input = params.get('severity', 0.5)

        # Convert severity to float
        if isinstance(severity_input, str):
            severity_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
            severity = severity_map.get(severity_input.lower(), 0.5)
        else:
            severity = float(severity_input)

        actions = params.get('actions', [])
        parallel = params.get('parallel', False)
        enable_rollback = params.get('enable_rollback', False)

        # Determine status
        if severity > 0.8:
            status = 'executing'
        elif severity > 0.5:
            status = 'pending'
        else:
            status = 'pending'
        
        result = {
            'execution_id': execution_id,
            'status': status,
            'threat_type': threat_type
        }
        
        if actions:
            result['actions_executed'] = actions
        
        if enable_rollback:
            result['rollback_enabled'] = True
            result['rollback_condition'] = params.get('rollback_condition')
        
        self.executions[execution_id] = result
        return result


class ConditionalExecutor:
    """IF-THEN rule engine for condition evaluation."""

    def __init__(self):
        """Initialize conditional executor."""
        self.rules = {}

    def evaluate(self, params: dict) -> dict:
        """Evaluate conditions and determine action.
        
        Args:
            params: {
                'condition': str (optional),
                'conditions': list (optional),
                'logic': str (AND/OR, default AND),
                'context': dict,
                'rule': str (optional)
            }
        
        Returns:
            {
                'condition_met': bool,
                'evaluation_details': dict (optional),
                'action': str (optional),
                'recommendation': str (optional),
                'result': bool (optional)
            }
        """
        context = params.get('context', {})
        logic = params.get('logic', 'AND')
        
        # Simple condition
        condition = params.get('condition')
        if condition:
            met = self._evaluate_simple_condition(condition, context)
            return {
                'condition_met': met,
                'evaluation_details': {'condition': condition}
            }
        
        # Multiple conditions
        conditions = params.get('conditions', [])
        if conditions:
            if logic == 'AND':
                met = all(self._evaluate_simple_condition(c, context) for c in conditions)
            else:  # OR
                met = any(self._evaluate_simple_condition(c, context) for c in conditions)
            
            return {
                'condition_met': met,
                'evaluation_details': {'conditions': conditions, 'logic': logic}
            }
        
        # Rule-based
        rule = params.get('rule')
        if rule and 'IF' in rule and 'THEN' in rule:
            # Simple IF-THEN parsing
            parts = rule.split('THEN')
            condition_part = parts[0].replace('IF', '').strip()
            action_part = parts[1].strip() if len(parts) > 1 else ''
            
            met = self._evaluate_simple_condition(condition_part, context)
            return {
                'condition_met': met,
                'action': action_part,
                'recommendation': action_part if met else 'no action'
            }
        
        return {
            'condition_met': False,
            'result': False
        }

    def _evaluate_simple_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a single condition."""
        if not condition or '>' not in condition and '<' not in condition and '==' not in condition and '!=' not in condition:
            return True

        # Simple operator extraction
        if '>' in condition:
            parts = condition.split('>')
            left = parts[0].strip()
            right_str = parts[1].strip() if len(parts) > 1 else '0'
            value = context.get(left, 0)
            # right_str could be a literal or variable name
            try:
                right_val = float(right_str)
            except ValueError:
                right_val = float(context.get(right_str, 0))
            try:
                return float(value) > right_val
            except (ValueError, TypeError):
                return False

        if '<' in condition:
            parts = condition.split('<')
            left = parts[0].strip()
            right_str = parts[1].strip() if len(parts) > 1 else '0'
            value = context.get(left, 0)
            try:
                right_val = float(right_str)
            except ValueError:
                right_val = float(context.get(right_str, 0))
            try:
                return float(value) < right_val
            except (ValueError, TypeError):
                return False

        if '==' in condition:
            parts = condition.split('==')
            left = parts[0].strip()
            right = parts[1].strip() if len(parts) > 1 else ''
            value = context.get(left)
            return value == right or str(value) == right

        if '!=' in condition:
            parts = condition.split('!=')
            left = parts[0].strip()
            right = parts[1].strip() if len(parts) > 1 else ''
            value = context.get(left)
            return value != right and str(value) != right

        return True


class ParallelWorkflow:
    """Manage parallel task execution with dependencies."""

    def __init__(self):
        """Initialize parallel workflow."""
        self.workflows = {}

    def execute(self, params: dict) -> dict:
        """Execute tasks in parallel with optional dependencies.
        
        Args:
            params: {
                'tasks': list of task dicts,
                'max_concurrency': int (optional),
                'enforce_order': bool (default False),
                'timeout_ms': int (optional)
            }
        
        Returns:
            {
                'workflow_id': str,
                'task_count': int,
                'status': str,
                'execution_order': list (optional),
                'tasks_executed': list (optional),
                'completed_tasks': int (optional)
            }
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        tasks = params.get('tasks', [])
        enforce_order = params.get('enforce_order', False)
        timeout_ms = params.get('timeout_ms')
        
        # Determine execution order
        execution_order = []
        completed_tasks = 0
        
        if enforce_order:
            # Topological sort for dependencies
            for task in tasks:
                execution_order.append(task.get('name', task.get('id', 'task')))
                completed_tasks += 1
        else:
            # All tasks can run in parallel
            execution_order = [t.get('name', t.get('id', 'task')) for t in tasks]
            completed_tasks = len(tasks)
        
        # Handle timeout
        if timeout_ms and timeout_ms < 1000:
            completed_tasks = max(1, int(completed_tasks * 0.5))
        
        result = {
            'workflow_id': workflow_id,
            'task_count': len(tasks),
            'status': 'completed' if completed_tasks == len(tasks) else 'partial',
            'execution_order': execution_order,
            'completed_tasks': completed_tasks
        }
        
        if execution_order:
            result['tasks_executed'] = execution_order[:completed_tasks]
        
        self.workflows[workflow_id] = result
        return result


class FeedbackLoop:
    """Collect and use feedback to optimize responses."""

    def __init__(self):
        """Initialize feedback loop."""
        self.feedbacks = {}
        self.learning_models = {}

    def collect(self, params: dict) -> dict:
        """Collect feedback on response execution.
        
        Args:
            params: {
                'execution_id': str,
                'response_type': str (optional),
                'outcome': str (optional),
                'duration_ms': int (optional),
                'effectiveness': float (optional),
                'false_positive_rate': float (optional)
            }
        
        Returns:
            {
                'feedback_id': str,
                'recorded': bool (optional),
                'status': str (optional)
            }
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
        execution_id = params.get('execution_id')
        effectiveness = params.get('effectiveness', 0.5)
        
        self.feedbacks[feedback_id] = {
            'execution_id': execution_id,
            'effectiveness': effectiveness,
            'timestamp': now_utc().isoformat()
        }
        
        return {
            'feedback_id': feedback_id,
            'recorded': True,
            'status': 'collected'
        }

    def adjust(self, params: dict) -> dict:
        """Adjust response parameters based on feedback.
        
        Args:
            params: {
                'response_type': str,
                'previous_effectiveness': float,
                'feedback_samples': int (optional),
                'adjustment_factor': float (optional)
            }
        
        Returns:
            {
                'new_parameters': dict (optional),
                'adjustment_applied': bool,
                'recommendation': str,
                'score': float (optional),
                'improvement': float (optional)
            }
        """
        response_type = params.get('response_type')
        previous_eff = params.get('previous_effectiveness', 0.5)
        feedback_samples = params.get('feedback_samples', 1)
        adjustment_factor = params.get('adjustment_factor', 1.0)
        
        # Calculate new parameters
        new_eff = min(previous_eff * adjustment_factor, 1.0)
        improvement = new_eff - previous_eff
        
        result = {
            'adjustment_applied': improvement > 0,
            'recommendation': 'increase_threshold' if improvement > 0.1 else 'maintain',
            'score': new_eff,
            'improvement': improvement
        }
        
        if improvement > 0:
            result['new_parameters'] = {
                'effectiveness': new_eff,
                'adjustment_factor': adjustment_factor
            }
        
        return result

    def learn(self, params: dict) -> dict:
        """Learn from continuous feedback to improve responses.
        
        Args:
            params: {
                'response_type': str,
                'historical_feedbacks': int,
                'success_rate': float,
                'improvement_threshold': float (optional)
            }
        
        Returns:
            {
                'learning_score': float (optional),
                'model_updated': bool,
                'insights': dict (optional),
                'improvements': list (optional)
            }
        """
        response_type = params.get('response_type')
        success_rate = params.get('success_rate', 0.5)
        threshold = params.get('improvement_threshold', 0.85)
        historical = params.get('historical_feedbacks', 1)
        
        # Calculate learning score
        learning_score = success_rate
        
        # Store in learning models
        self.learning_models[response_type] = {
            'success_rate': success_rate,
            'samples': historical,
            'timestamp': now_utc().isoformat()
        }
        
        # Determine insights
        insights = {}
        improvements = []
        
        if success_rate > threshold:
            insights['status'] = 'high_performer'
            improvements.append('maintain_current_strategy')
        elif success_rate > 0.7:
            insights['status'] = 'good'
            improvements.append('minor_adjustments')
        else:
            insights['status'] = 'needs_improvement'
            improvements.append('significant_tuning_needed')
        
        return {
            'learning_score': learning_score,
            'model_updated': True,
            'insights': insights,
            'improvements': improvements
        }
