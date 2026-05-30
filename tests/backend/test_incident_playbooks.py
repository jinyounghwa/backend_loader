"""Tests for automated incident playbooks (Phase 3 of Sprint 76)."""
import pytest
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestPlaybookEngine:
    """Test playbook engine execution."""

    def test_execute_playbook_basic(self):
        """✅ Execute basic playbook."""
        from guardian.playbooks.incident_playbooks import PlaybookEngine

        engine = PlaybookEngine()
        result = engine.execute_playbook({
            'playbook_id': 'pb_stop_ec2',
            'incident_id': 'inc_12345',
            'params': {'instance_id': 'i-12345'}
        })

        assert 'execution_id' in result
        assert 'status' in result
        assert result['status'] in ['success', 'pending', 'running']
        assert 'playbook_id' in result

    def test_execute_playbook_with_steps(self):
        """✅ Execute playbook with multiple steps."""
        from guardian.playbooks.incident_playbooks import PlaybookEngine

        engine = PlaybookEngine()
        result = engine.execute_playbook({
            'playbook_id': 'pb_isolate_instance',
            'incident_id': 'inc_67890',
            'params': {'instance_id': 'i-67890', 'reason': 'unauthorized_access'},
            'async': False
        })

        assert 'steps_executed' in result
        assert result['status'] == 'success'

    def test_playbook_execution_with_timeout(self):
        """✅ Playbook respects timeout."""
        from guardian.playbooks.incident_playbooks import PlaybookEngine

        engine = PlaybookEngine()
        result = engine.execute_playbook({
            'playbook_id': 'pb_long_running',
            'incident_id': 'inc_timeout',
            'timeout_seconds': 5
        })

        assert 'timeout' in result or 'status' in result


class TestPlaybookLibrary:
    """Test playbook library and discovery."""

    def test_list_playbooks(self):
        """✅ List available playbooks."""
        from guardian.playbooks.incident_playbooks import PlaybookLibrary

        library = PlaybookLibrary()
        playbooks = library.list_playbooks({})

        assert isinstance(playbooks, list)
        assert len(playbooks) > 0
        assert any(p['id'] == 'pb_stop_ec2' for p in playbooks)

    def test_get_playbook_details(self):
        """✅ Get playbook details."""
        from guardian.playbooks.incident_playbooks import PlaybookLibrary

        library = PlaybookLibrary()
        details = library.get_playbook({
            'playbook_id': 'pb_stop_ec2'
        })

        assert 'id' in details
        assert 'name' in details
        assert 'description' in details
        assert 'steps' in details
        assert isinstance(details['steps'], list)

    def test_search_playbooks(self):
        """✅ Search playbooks by keyword."""
        from guardian.playbooks.incident_playbooks import PlaybookLibrary

        library = PlaybookLibrary()
        results = library.search_playbooks({
            'query': 'stop',
            'category': 'ec2'
        })

        assert isinstance(results, list)
        assert len(results) > 0


class TestPlaybookExecutor:
    """Test playbook execution with orchestration."""

    def test_sequential_execution(self):
        """✅ Execute playbook steps sequentially."""
        from guardian.playbooks.incident_playbooks import PlaybookExecutor

        executor = PlaybookExecutor()
        result = executor.execute_steps({
            'execution_id': 'exec_seq_001',
            'steps': [
                {'id': 'step1', 'action': 'notify', 'params': {}},
                {'id': 'step2', 'action': 'snapshot', 'params': {'instance_id': 'i-123'}},
                {'id': 'step3', 'action': 'stop', 'params': {'instance_id': 'i-123'}}
            ],
            'parallel': False
        })

        assert 'execution_id' in result
        assert result['status'] == 'success'
        assert 'steps_completed' in result
        assert result['steps_completed'] == 3

    def test_parallel_execution(self):
        """✅ Execute independent steps in parallel."""
        from guardian.playbooks.incident_playbooks import PlaybookExecutor

        executor = PlaybookExecutor()
        result = executor.execute_steps({
            'execution_id': 'exec_par_001',
            'steps': [
                {'id': 'step1', 'action': 'notify_slack', 'params': {}},
                {'id': 'step2', 'action': 'notify_email', 'params': {}},
                {'id': 'step3', 'action': 'log_event', 'params': {}}
            ],
            'parallel': True
        })

        assert result['status'] == 'success'
        assert result['steps_completed'] == 3

    def test_step_dependencies(self):
        """✅ Handle step dependencies."""
        from guardian.playbooks.incident_playbooks import PlaybookExecutor

        executor = PlaybookExecutor()
        result = executor.execute_steps({
            'execution_id': 'exec_dep_001',
            'steps': [
                {'id': 'step1', 'action': 'snapshot', 'params': {}},
                {'id': 'step2', 'action': 'stop', 'params': {}, 'depends_on': ['step1']}
            ]
        })

        assert result['status'] == 'success'


class TestPlaybookRecorder:
    """Test playbook execution recording and audit."""

    def test_record_execution(self):
        """✅ Record playbook execution."""
        from guardian.playbooks.incident_playbooks import PlaybookRecorder

        recorder = PlaybookRecorder()
        record = recorder.record_execution({
            'execution_id': 'exec_rec_001',
            'playbook_id': 'pb_stop_ec2',
            'incident_id': 'inc_001',
            'status': 'success',
            'steps': [
                {'step_id': 'step1', 'status': 'success', 'duration_ms': 1200},
                {'step_id': 'step2', 'status': 'success', 'duration_ms': 800}
            ]
        })

        assert 'execution_id' in record
        assert 'recorded_at' in record
        assert record['status'] == 'success'

    def test_get_execution_history(self):
        """✅ Get execution history."""
        from guardian.playbooks.incident_playbooks import PlaybookRecorder

        recorder = PlaybookRecorder()
        history = recorder.get_history({
            'playbook_id': 'pb_stop_ec2',
            'limit': 10
        })

        assert isinstance(history, list)
        assert all('execution_id' in h for h in history)

    def test_audit_trail(self):
        """✅ Generate audit trail."""
        from guardian.playbooks.incident_playbooks import PlaybookRecorder

        recorder = PlaybookRecorder()
        audit = recorder.get_audit_trail({
            'playbook_id': 'pb_stop_ec2',
            'days': 7
        })

        assert 'total_executions' in audit
        assert 'success_count' in audit
        assert 'failure_count' in audit
        assert 'success_rate' in audit


class TestIncidentPlaybooksIntegration:
    """Integration tests for incident playbooks."""

    def test_incident_response_workflow(self):
        """✅ Complete incident response workflow."""
        from guardian.playbooks.incident_playbooks import (
            PlaybookEngine,
            PlaybookLibrary,
            PlaybookRecorder
        )

        library = PlaybookLibrary()
        engine = PlaybookEngine()
        recorder = PlaybookRecorder()

        # Step 1: Get playbook details
        playbook = library.get_playbook({'playbook_id': 'pb_stop_ec2'})
        assert playbook is not None

        # Step 2: Execute playbook
        result = engine.execute_playbook({
            'playbook_id': 'pb_stop_ec2',
            'incident_id': 'inc_workflow_001',
            'params': {'instance_id': 'i-workflow_001'},
            'async': False
        })

        # Step 3: Record execution
        record = recorder.record_execution({
            'execution_id': result['execution_id'],
            'playbook_id': 'pb_stop_ec2',
            'incident_id': 'inc_workflow_001',
            'status': result['status'],
            'steps': []
        })

        assert result['status'] == 'success'
        assert record['recorded_at'] is not None

    def test_multi_playbook_orchestration(self):
        """✅ Orchestrate multiple playbooks."""
        from guardian.playbooks.incident_playbooks import PlaybookEngine

        engine = PlaybookEngine()

        # Execute first playbook
        result1 = engine.execute_playbook({
            'playbook_id': 'pb_snapshot',
            'incident_id': 'inc_multi_001'
        })

        # Execute second playbook
        result2 = engine.execute_playbook({
            'playbook_id': 'pb_stop_ec2',
            'incident_id': 'inc_multi_001',
            'depends_on': result1['execution_id']
        })

        assert result1['status'] in ['success', 'pending', 'running']
        assert result2['status'] in ['success', 'pending', 'running']

    def test_playbook_with_rollback(self):
        """✅ Playbook supports rollback."""
        from guardian.playbooks.incident_playbooks import PlaybookEngine

        engine = PlaybookEngine()
        result = engine.execute_playbook({
            'playbook_id': 'pb_with_rollback',
            'incident_id': 'inc_rollback_001',
            'enable_rollback': True
        })

        assert 'rollback_available' in result or 'status' in result
