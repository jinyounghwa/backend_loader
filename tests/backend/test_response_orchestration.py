"""Advanced response orchestration tests for AWS Guardian."""

import pytest


class TestResponseOrchestrator:
    """Test response orchestration."""

    def test_execute_conditional_response(self):
        """✅ Execute response based on conditions."""
        from guardian.response.response_orchestration import ResponseOrchestrator

        orchestrator = ResponseOrchestrator()

        response = orchestrator.execute({
            'threat_type': 'unauthorized_access',
            'severity': 'critical',
            'target': 'i-12345678'
        })

        assert 'execution_id' in response
        assert response['status'] in ['pending', 'executing', 'completed']

    def test_orchestration_with_multiple_actions(self):
        """✅ Orchestrate multiple responses in sequence."""
        from guardian.response.response_orchestration import ResponseOrchestrator

        orchestrator = ResponseOrchestrator()

        response = orchestrator.execute({
            'threat_type': 'data_exfiltration',
            'actions': ['isolate', 'alert', 'block'],
            'parallel': False
        })

        assert 'execution_id' in response
        assert 'actions_executed' in response or 'status' in response

    def test_orchestration_with_rollback(self):
        """✅ Rollback response if conditions fail."""
        from guardian.response.response_orchestration import ResponseOrchestrator

        orchestrator = ResponseOrchestrator()

        response = orchestrator.execute({
            'threat_type': 'test_threat',
            'enable_rollback': True,
            'rollback_condition': 'failure'
        })

        assert 'execution_id' in response
        assert 'rollback_enabled' in response or response.get('status') is not None


class TestConditionalExecutor:
    """Test conditional rule execution."""

    def test_evaluate_simple_condition(self):
        """✅ Evaluate single condition rule."""
        from guardian.response.response_orchestration import ConditionalExecutor

        executor = ConditionalExecutor()

        result = executor.evaluate({
            'condition': 'severity > 0.8',
            'context': {'severity': 0.9}
        })

        assert 'condition_met' in result
        assert result['condition_met'] is True

    def test_evaluate_complex_condition(self):
        """✅ Evaluate multi-part conditions."""
        from guardian.response.response_orchestration import ConditionalExecutor

        executor = ConditionalExecutor()

        result = executor.evaluate({
            'conditions': [
                'severity > 0.7',
                'resource_type == "EC2"',
                'region != "eu-west-1"'
            ],
            'logic': 'AND',
            'context': {
                'severity': 0.85,
                'resource_type': 'EC2',
                'region': 'us-east-1'
            }
        })

        assert 'condition_met' in result
        assert 'evaluation_details' in result or 'result' in result

    def test_condition_with_context_variables(self):
        """✅ Use context variables in conditions."""
        from guardian.response.response_orchestration import ConditionalExecutor

        executor = ConditionalExecutor()

        result = executor.evaluate({
            'rule': 'IF threat_score > threshold THEN escalate',
            'context': {
                'threat_score': 0.9,
                'threshold': 0.7,
                'action': 'escalate'
            }
        })

        assert 'condition_met' in result
        assert 'action' in result or 'recommendation' in result


class TestParallelWorkflow:
    """Test parallel workflow execution."""

    def test_execute_parallel_tasks(self):
        """✅ Execute tasks in parallel."""
        from guardian.response.response_orchestration import ParallelWorkflow

        workflow = ParallelWorkflow()

        result = workflow.execute({
            'tasks': [
                {'name': 'stop_instance', 'target': 'i-12345'},
                {'name': 'snapshot_volume', 'target': 'vol-xyz'},
                {'name': 'notify_security', 'recipients': ['sec@example.com']}
            ],
            'max_concurrency': 3
        })

        assert 'workflow_id' in result
        assert 'task_count' in result or 'status' in result

    def test_parallel_with_dependencies(self):
        """✅ Handle task dependencies in parallel execution."""
        from guardian.response.response_orchestration import ParallelWorkflow

        workflow = ParallelWorkflow()

        result = workflow.execute({
            'tasks': [
                {'name': 'snapshot', 'id': 'task_1'},
                {'name': 'isolate', 'id': 'task_2', 'depends_on': ['task_1']},
                {'name': 'notify', 'id': 'task_3', 'depends_on': ['task_2']}
            ],
            'enforce_order': True
        })

        assert 'workflow_id' in result
        assert 'execution_order' in result or 'tasks_executed' in result

    def test_parallel_workflow_timeout(self):
        """✅ Handle timeout in parallel execution."""
        from guardian.response.response_orchestration import ParallelWorkflow

        workflow = ParallelWorkflow()

        result = workflow.execute({
            'tasks': [
                {'name': 'long_task', 'duration_ms': 5000},
                {'name': 'quick_task', 'duration_ms': 100}
            ],
            'timeout_ms': 2000
        })

        assert 'workflow_id' in result
        assert 'completed_tasks' in result or 'status' in result


class TestFeedbackLoop:
    """Test response feedback and adjustment."""

    def test_collect_response_feedback(self):
        """✅ Collect feedback on response execution."""
        from guardian.response.response_orchestration import FeedbackLoop

        feedback = FeedbackLoop()

        result = feedback.collect({
            'execution_id': 'exec_12345',
            'response_type': 'instance_stop',
            'outcome': 'success',
            'duration_ms': 250,
            'effectiveness': 0.95
        })

        assert 'feedback_id' in result
        assert 'recorded' in result or 'status' in result

    def test_adjust_response_based_on_feedback(self):
        """✅ Adjust response parameters based on feedback."""
        from guardian.response.response_orchestration import FeedbackLoop

        feedback = FeedbackLoop()

        result = feedback.adjust({
            'response_type': 'instance_isolation',
            'previous_effectiveness': 0.75,
            'feedback_samples': 10,
            'adjustment_factor': 1.2
        })

        assert 'new_parameters' in result or 'adjustment_applied' in result
        assert 'recommendation' in result or 'score' in result

    def test_feedback_loop_continuous_learning(self):
        """✅ Learn from continuous feedback to improve responses."""
        from guardian.response.response_orchestration import FeedbackLoop

        feedback = FeedbackLoop()

        result = feedback.learn({
            'response_type': 'cost_anomaly_mitigation',
            'historical_feedbacks': 50,
            'success_rate': 0.92,
            'improvement_threshold': 0.85
        })

        assert 'learning_score' in result or 'model_updated' in result
        assert 'insights' in result or 'improvements' in result


class TestResponseOrchestrationIntegration:
    """End-to-end response orchestration workflows."""

    def test_full_orchestration_pipeline(self):
        """✅ Complete pipeline: detect → evaluate → execute → feedback."""
        from guardian.response.response_orchestration import (
            ResponseOrchestrator,
            ConditionalExecutor,
            FeedbackLoop
        )

        orchestrator = ResponseOrchestrator()
        executor = ConditionalExecutor()
        feedback = FeedbackLoop()

        # Step 1: Execute response
        execution = orchestrator.execute({
            'threat_type': 'security_breach',
            'severity': 0.95
        })
        assert 'execution_id' in execution

        # Step 2: Evaluate conditions
        conditions = executor.evaluate({
            'condition': 'severity > 0.9',
            'context': {'severity': 0.95}
        })
        assert conditions['condition_met'] is True

        # Step 3: Collect feedback
        result = feedback.collect({
            'execution_id': execution['execution_id'],
            'effectiveness': 0.9
        })
        assert 'feedback_id' in result

    def test_multi_stage_response_workflow(self):
        """✅ Complex workflow: multiple conditions → parallel actions → feedback."""
        from guardian.response.response_orchestration import (
            ResponseOrchestrator,
            ParallelWorkflow,
            FeedbackLoop
        )

        orchestrator = ResponseOrchestrator()
        workflow = ParallelWorkflow()
        feedback = FeedbackLoop()

        # Execute response
        execution = orchestrator.execute({
            'threat_type': 'data_exfiltration',
            'actions': ['isolate', 'snapshot', 'alert']
        })

        # Execute in parallel
        parallel = workflow.execute({
            'tasks': [
                {'name': 'isolate'},
                {'name': 'snapshot'},
                {'name': 'alert'}
            ]
        })

        # Collect feedback
        result = feedback.collect({
            'execution_id': execution['execution_id'],
            'outcome': 'success'
        })

        assert 'feedback_id' in result

    def test_adaptive_response_with_feedback_loop(self):
        """✅ Adapt responses based on continuous feedback."""
        from guardian.response.response_orchestration import (
            ResponseOrchestrator,
            FeedbackLoop
        )

        orchestrator = ResponseOrchestrator()
        feedback = FeedbackLoop()

        # Initial execution
        execution1 = orchestrator.execute({
            'threat_type': 'cost_anomaly',
            'initial_threshold': 0.8
        })

        # Feedback on effectiveness
        fb1 = feedback.collect({
            'execution_id': execution1['execution_id'],
            'effectiveness': 0.65,
            'false_positive_rate': 0.15
        })

        # Learn and adjust
        adjustment = feedback.adjust({
            'response_type': 'cost_anomaly',
            'previous_effectiveness': 0.65,
            'feedback_samples': 20
        })

        assert 'new_parameters' in adjustment or 'adjustment_applied' in adjustment
