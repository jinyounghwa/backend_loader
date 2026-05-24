"""Tests for incident orchestration and workflow automation - Phase 4 of Sprint 44"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda/guardian'))

from orchestrators.incident_orchestrator import IncidentOrchestrator


class TestIncidentOrchestrationBasics:
    """Group 1: Basic incident orchestration workflow"""

    @pytest.fixture
    def orchestrator_with_all_components(self):
        ticketing = Mock()
        workflows = Mock()
        soar = Mock()
        return IncidentOrchestrator(ticketing, workflows, soar)

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'unauthorized_access_001',
            'severity': 8,
            'event_name': 'UnauthorizedOperation',
            'principal': 'arn:aws:iam::123456789:user/attacker',
            'source_ip': '192.168.1.100'
        }

    def test_orchestrate_incident_creates_incident_id(self, orchestrator_with_all_components, sample_threat):
        """Test that orchestration creates unique incident ID"""
        orchestrator_with_all_components.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator_with_all_components.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator_with_all_components.soar.send_incident_to_soar.return_value = 'soar-123'

        result = orchestrator_with_all_components.orchestrate_incident_response(sample_threat)

        assert 'incident_id' in result
        assert result['incident_id'] in orchestrator_with_all_components.incidents
        assert result['status'] == 'orchestrated'

    def test_orchestrate_incident_creates_ticket(self, orchestrator_with_all_components, sample_threat):
        """Test that orchestration creates ticket for incident"""
        orchestrator_with_all_components.ticketing.create_ticket.return_value = {
            'tickets': {'jira': 'SECURITY-001', 'servicenow': 'INC0001'}
        }
        orchestrator_with_all_components.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator_with_all_components.soar.send_incident_to_soar.return_value = 'soar-123'

        result = orchestrator_with_all_components.orchestrate_incident_response(sample_threat)

        assert result['components']['ticket'] is not None
        assert result['components']['ticket']['jira'] == 'SECURITY-001'
        orchestrator_with_all_components.ticketing.create_ticket.assert_called_once()

    def test_orchestrate_incident_executes_workflow(self, orchestrator_with_all_components, sample_threat):
        """Test that orchestration executes remediation workflow"""
        orchestrator_with_all_components.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator_with_all_components.workflows.execute_workflow.return_value = {
            'workflow_id': 'default_remediation',
            'execution_id': 'exec-123',
            'status': 'success'
        }
        orchestrator_with_all_components.soar.send_incident_to_soar.return_value = 'soar-123'

        result = orchestrator_with_all_components.orchestrate_incident_response(sample_threat)

        assert result['components']['workflow'] is not None
        assert result['components']['workflow']['status'] == 'success'
        orchestrator_with_all_components.workflows.execute_workflow.assert_called_once()

    def test_orchestrate_incident_sends_to_soar(self, orchestrator_with_all_components, sample_threat):
        """Test that orchestration sends incident to SOAR"""
        orchestrator_with_all_components.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator_with_all_components.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator_with_all_components.soar.send_incident_to_soar.return_value = 'soar-incident-456'

        result = orchestrator_with_all_components.orchestrate_incident_response(sample_threat)

        assert result['components']['soar'] is not None
        assert result['components']['soar']['incident_id'] == 'soar-incident-456'
        orchestrator_with_all_components.soar.send_incident_to_soar.assert_called_once()

    def test_orchestrate_incident_tracks_timeline(self, orchestrator_with_all_components, sample_threat):
        """Test that orchestration tracks complete timeline"""
        orchestrator_with_all_components.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator_with_all_components.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator_with_all_components.soar.send_incident_to_soar.return_value = 'soar-123'

        result = orchestrator_with_all_components.orchestrate_incident_response(sample_threat)

        assert len(result['timeline']) >= 3
        assert any(e['event'] == 'ticket_created' for e in result['timeline'])
        assert any(e['event'] == 'workflow_executed' for e in result['timeline'])
        assert any(e['event'] == 'sent_to_soar' for e in result['timeline'])


class TestIncidentOrchestrationWithMissingComponents:
    """Group 2: Orchestration with missing/disabled components"""

    @pytest.fixture
    def orchestrator_ticketing_only(self):
        ticketing = Mock()
        return IncidentOrchestrator(ticketing, None, None)

    @pytest.fixture
    def orchestrator_no_components(self):
        return IncidentOrchestrator(None, None, None)

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'cost_spike_001',
            'severity': 5,
            'event_name': 'CostAnomaly',
            'cost_delta': 500.00
        }

    def test_orchestrate_without_ticketing_handler(self, orchestrator_ticketing_only, sample_threat):
        """Test orchestration when ticketing is disabled"""
        orchestrator_ticketing_only.ticketing.create_ticket.return_value = {'tickets': {}}

        result = orchestrator_ticketing_only.orchestrate_incident_response(sample_threat)

        assert result['components']['ticket'] is not None
        assert result['status'] == 'orchestrated'

    def test_orchestrate_without_any_components(self, orchestrator_no_components, sample_threat):
        """Test orchestration with no handlers configured"""
        result = orchestrator_no_components.orchestrate_incident_response(sample_threat)

        assert result['incident_id'] is not None
        assert result['components']['ticket'] is None
        assert result['components']['workflow'] is None
        assert result['components']['soar'] is None
        assert result['status'] == 'orchestrated'

    def test_orchestrate_handles_ticket_creation_failure(self, orchestrator_ticketing_only, sample_threat):
        """Test orchestration continues if ticket creation fails"""
        orchestrator_ticketing_only.ticketing.create_ticket.side_effect = Exception("Ticket service down")

        result = orchestrator_ticketing_only.orchestrate_incident_response(sample_threat)

        assert result['status'] == 'error' or result['components']['ticket'] is None

    def test_orchestrate_handles_exception_gracefully(self, orchestrator_no_components, sample_threat):
        """Test orchestration error handling"""
        bad_threat = None
        try:
            result = orchestrator_no_components.orchestrate_incident_response(bad_threat)
        except TypeError:
            pass  # Expected when threat is None


class TestParallelWorkflowCoordination:
    """Group 3: Parallel workflow execution and coordination"""

    @pytest.fixture
    def orchestrator(self):
        workflows = Mock()
        return IncidentOrchestrator(None, workflows, None)

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'security_incident_001',
            'severity': 9,
            'event_name': 'CredentialTheft'
        }

    @pytest.fixture
    def sample_workflows(self):
        return [
            {
                'workflow_id': 'revoke_access',
                'name': 'Revoke Credentials',
                'enabled': True
            },
            {
                'workflow_id': 'isolate_host',
                'name': 'Isolate Compromised Host',
                'enabled': True
            },
            {
                'workflow_id': 'log_forensics',
                'name': 'Collect Forensic Data',
                'enabled': True
            }
        ]

    def test_coordinate_parallel_workflows_executes_all(self, orchestrator, sample_threat, sample_workflows):
        """Test that all workflows are executed"""
        orchestrator.workflows.execute_workflow.side_effect = [
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0}
        ]

        result = orchestrator.coordinate_parallel_workflows(sample_workflows, sample_threat)

        assert result['workflow_count'] == 3
        assert result['success_count'] == 3
        assert result['failure_count'] == 0
        assert orchestrator.workflows.execute_workflow.call_count == 3

    def test_coordinate_workflows_handles_partial_success(self, orchestrator, sample_threat, sample_workflows):
        """Test coordination with some workflow failures"""
        orchestrator.workflows.execute_workflow.side_effect = [
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'failed', 'success_count': 0, 'failure_count': 1},
            {'status': 'partial_success', 'success_count': 1, 'failure_count': 1}
        ]

        result = orchestrator.coordinate_parallel_workflows(sample_workflows, sample_threat)

        assert result['workflow_count'] == 3
        assert result['success_count'] == 2
        assert result['failure_count'] == 1

    def test_coordinate_workflows_includes_threat_id(self, orchestrator, sample_threat, sample_workflows):
        """Test that coordination result includes threat identification"""
        orchestrator.workflows.execute_workflow.side_effect = [
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0}
        ]

        result = orchestrator.coordinate_parallel_workflows(sample_workflows, sample_threat)

        assert result['threat_id'] == sample_threat['rule_id']

    def test_coordinate_workflows_includes_timestamp(self, orchestrator, sample_threat, sample_workflows):
        """Test that coordination result includes execution timestamp"""
        orchestrator.workflows.execute_workflow.side_effect = [
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0}
        ]

        result = orchestrator.coordinate_parallel_workflows(sample_workflows, sample_threat)

        assert 'timestamp' in result
        assert result['timestamp'] is not None


class TestIncidentTracking:
    """Group 4: Incident lifecycle tracking and status management"""

    @pytest.fixture
    def orchestrator(self):
        ticketing = Mock()
        workflows = Mock()
        soar = Mock()
        return IncidentOrchestrator(ticketing, workflows, soar)

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'unauthorized_ec2_001',
            'severity': 7,
            'event_name': 'UnauthorizedEC2Start'
        }

    def test_track_incident_to_resolution_found(self, orchestrator, sample_threat):
        """Test tracking incident that exists"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        incident_id = incident['incident_id']

        tracked = orchestrator.track_incident_to_resolution(incident_id)

        assert tracked is not None
        assert tracked['incident_id'] == incident_id
        assert 'lifecycle' in tracked
        assert 'created' in tracked['lifecycle']
        assert 'orchestrated' in tracked['lifecycle']
        assert 'tracked' in tracked['lifecycle']

    def test_track_incident_not_found(self, orchestrator):
        """Test tracking non-existent incident"""
        result = orchestrator.track_incident_to_resolution('non-existent-id')

        assert result is None

    def test_track_incident_includes_lifecycle_status(self, orchestrator, sample_threat):
        """Test that tracking includes full lifecycle status"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        tracked = orchestrator.track_incident_to_resolution(incident['incident_id'])

        assert tracked['lifecycle']['status'] == 'orchestrated'
        assert tracked['lifecycle']['components'] == incident['components']

    def test_track_incident_includes_all_timestamps(self, orchestrator, sample_threat):
        """Test that tracking includes all relevant timestamps"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        tracked = orchestrator.track_incident_to_resolution(incident['incident_id'])

        assert 'created' in tracked['lifecycle']
        assert 'orchestrated' in tracked['lifecycle']
        assert 'tracked' in tracked['lifecycle']


class TestIncidentReporting:
    """Group 5: Comprehensive incident response reporting"""

    @pytest.fixture
    def orchestrator(self):
        ticketing = Mock()
        workflows = Mock()
        soar = Mock()
        return IncidentOrchestrator(ticketing, workflows, soar)

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'public_bucket_001',
            'severity': 8,
            'event_name': 'PublicBucketCreated',
            'bucket_name': 's3-public-bucket'
        }

    def test_generate_incident_report_found(self, orchestrator, sample_threat):
        """Test report generation for existing incident"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        report = orchestrator.generate_incident_report(incident['incident_id'])

        assert report is not None
        assert report['incident_id'] == incident['incident_id']
        assert report['threat_id'] == sample_threat['rule_id']

    def test_generate_incident_report_not_found(self, orchestrator):
        """Test report generation for non-existent incident"""
        result = orchestrator.generate_incident_report('non-existent-id')

        assert result is None

    def test_generate_incident_report_includes_severity(self, orchestrator, sample_threat):
        """Test that report includes incident severity"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        report = orchestrator.generate_incident_report(incident['incident_id'])

        assert report['severity'] == sample_threat['severity']

    def test_generate_incident_report_includes_response_summary(self, orchestrator, sample_threat):
        """Test that report includes response component summary"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {'jira': 'SECURITY-001'}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        report = orchestrator.generate_incident_report(incident['incident_id'])

        assert 'response_summary' in report
        assert 'ticket_created' in report['response_summary']
        assert 'workflow_executed' in report['response_summary']
        assert 'soar_integration' in report['response_summary']

    def test_generate_incident_report_includes_timeline(self, orchestrator, sample_threat):
        """Test that report includes incident timeline"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        report = orchestrator.generate_incident_report(incident['incident_id'])

        assert 'timeline' in report
        assert isinstance(report['timeline'], list)

    def test_generate_incident_report_includes_generation_timestamp(self, orchestrator, sample_threat):
        """Test that report includes generation timestamp"""
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(sample_threat)
        report = orchestrator.generate_incident_report(incident['incident_id'])

        assert 'generated_at' in report
        assert report['generated_at'] is not None


class TestEndToEndOrchestration:
    """Group 6: End-to-end orchestration workflows"""

    @pytest.fixture
    def orchestrator(self):
        ticketing = Mock()
        workflows = Mock()
        soar = Mock()
        return IncidentOrchestrator(ticketing, workflows, soar)

    def test_complete_incident_lifecycle(self, orchestrator):
        """Test complete incident lifecycle from detection to report"""
        threat = {
            'rule_id': 'security_threat_001',
            'severity': 9,
            'event_name': 'CriticalSecurityEvent'
        }

        orchestrator.ticketing.create_ticket.return_value = {
            'tickets': {'jira': 'SECURITY-001', 'servicenow': 'INC0001'}
        }
        orchestrator.workflows.execute_workflow.return_value = {
            'status': 'success',
            'success_count': 1,
            'failure_count': 0
        }
        orchestrator.soar.send_incident_to_soar.return_value = 'phantom-incident-123'

        incident = orchestrator.orchestrate_incident_response(threat)
        incident_id = incident['incident_id']

        tracked = orchestrator.track_incident_to_resolution(incident_id)
        report = orchestrator.generate_incident_report(incident_id)

        assert incident['status'] == 'orchestrated'
        assert tracked is not None
        assert report is not None
        assert report['threat_id'] == threat['rule_id']

    def test_multiple_incidents_independently_tracked(self, orchestrator):
        """Test that multiple incidents are tracked independently"""
        threat1 = {'rule_id': 'threat_001', 'severity': 7, 'event_name': 'Event1'}
        threat2 = {'rule_id': 'threat_002', 'severity': 8, 'event_name': 'Event2'}

        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.workflows.execute_workflow.return_value = {'status': 'success'}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident1 = orchestrator.orchestrate_incident_response(threat1)
        incident2 = orchestrator.orchestrate_incident_response(threat2)

        assert incident1['incident_id'] != incident2['incident_id']
        assert orchestrator.track_incident_to_resolution(incident1['incident_id'])['threat_id'] == 'threat_001'
        assert orchestrator.track_incident_to_resolution(incident2['incident_id'])['threat_id'] == 'threat_002'

    def test_workflow_coordination_with_orchestration(self, orchestrator):
        """Test workflow coordination integrated with orchestration"""
        threat = {'rule_id': 'coordinated_threat', 'severity': 8}
        workflows = [
            {'workflow_id': 'wf1', 'enabled': True},
            {'workflow_id': 'wf2', 'enabled': True}
        ]

        orchestrator.workflows.execute_workflow.side_effect = [
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0},
            {'status': 'success', 'success_count': 1, 'failure_count': 0}
        ]
        orchestrator.ticketing.create_ticket.return_value = {'tickets': {}}
        orchestrator.soar.send_incident_to_soar.return_value = 'soar-123'

        incident = orchestrator.orchestrate_incident_response(threat)
        coordination = orchestrator.coordinate_parallel_workflows(workflows, threat)

        assert incident['incident_id'] is not None
        assert coordination['success_count'] == 2
