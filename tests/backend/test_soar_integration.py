"""Tests for SOAR platform integration - Phase 3 of Sprint 44"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import sys
import os
from guardian.integrations.splunk_phantom_connector import SplunkPhantomConnector
from guardian.integrations.swimlane_connector import SwimlaneConnector


class TestSplunkPhantomIncidentCreation:
    """Group 1: Splunk Phantom incident/container creation"""

    @pytest.fixture
    def phantom_connector(self):
        return SplunkPhantomConnector('https://phantom.example.com', 'api_token')

    @pytest.fixture
    def sample_incident(self):
        return {
            'title': 'Unauthorized API Access',
            'description': 'Suspicious API calls detected',
            'severity': 8,
            'threat_id': 'threat_123',
            'account_id': 'aws_account',
            'threat_type': 'unauthorized_access'
        }

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_send_incident_to_phantom(self, mock_post, phantom_connector, sample_incident):
        """Test sending incident to Splunk Phantom"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 12345}
        mock_post.return_value = mock_response

        container_id = phantom_connector.send_incident_to_soar(sample_incident)

        assert container_id == '12345'
        mock_post.assert_called_once()

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_send_incident_creates_container(self, mock_post, phantom_connector, sample_incident):
        """Test incident is created as Phantom container"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 54321}
        mock_post.return_value = mock_response

        phantom_connector.send_incident_to_soar(sample_incident)

        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'name' in payload
        assert payload['label'] == 'aws_guardian'
        assert 'data' in payload

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_send_incident_failure(self, mock_post, phantom_connector, sample_incident):
        """Test handling of failed incident submission"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        container_id = phantom_connector.send_incident_to_soar(sample_incident)

        assert container_id is None


class TestSplunkPhantomPlaybookExecution:
    """Group 2: Splunk Phantom playbook execution"""

    @pytest.fixture
    def phantom_connector(self):
        return SplunkPhantomConnector('https://phantom.example.com', 'api_token')

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_run_phantom_playbook(self, mock_post, phantom_connector):
        """Test running Phantom playbook"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 999}
        mock_post.return_value = mock_response

        run_id = phantom_connector.run_phantom_playbook('12345', 'Stop EC2')

        assert run_id == '999'
        mock_post.assert_called_once()

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_run_playbook_payload(self, mock_post, phantom_connector):
        """Test playbook run payload structure"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 888}
        mock_post.return_value = mock_response

        phantom_connector.run_phantom_playbook('12345', 'Isolate Host')

        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['container_id'] == '12345'
        assert payload['playbook_name'] == 'Isolate Host'

    @patch('guardian.integrations.splunk_phantom_connector.requests.get')
    def test_track_playbook_status(self, mock_get, phantom_connector):
        """Test tracking playbook execution status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 999,
            'status': 'success',
            'result': {'action': 'stopped_ec2', 'instance': 'i-123'}
        }
        mock_get.return_value = mock_response

        status = phantom_connector.track_playbook_status('999')

        assert status['status'] == 'success'
        assert 'timestamp' in status
        assert status['run_id'] == '999'

    @patch('guardian.integrations.splunk_phantom_connector.requests.get')
    def test_get_available_playbooks(self, mock_get, phantom_connector):
        """Test retrieving available playbooks"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'name': 'Stop EC2', 'id': '1'},
                {'name': 'Isolate Host', 'id': '2'},
                {'name': 'Block IP', 'id': '3'}
            ]
        }
        mock_get.return_value = mock_response

        playbooks = phantom_connector.get_available_playbooks()

        assert len(playbooks) == 3
        assert playbooks[0]['name'] == 'Stop EC2'


class TestSwimlaneIncidentCreation:
    """Group 3: Swimlane record creation and workflow trigger"""

    @pytest.fixture
    def swimlane_connector(self):
        return SwimlaneConnector('https://swimlane.example.com', 'api_key', 'app_123')

    @pytest.fixture
    def sample_incident(self):
        return {
            'title': 'Credential Compromise',
            'description': 'Suspicious login detected',
            'severity': 9,
            'threat_id': 'threat_456',
            'account_id': 'aws_account',
            'threat_type': 'credential_abuse'
        }

    @patch('guardian.integrations.swimlane_connector.requests.post')
    def test_send_incident_to_swimlane(self, mock_post, swimlane_connector, sample_incident):
        """Test sending incident to Swimlane"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'rec-789'}
        mock_post.return_value = mock_response

        record_id = swimlane_connector.send_incident_to_soar(sample_incident)

        assert record_id == 'rec-789'
        mock_post.assert_called_once()

    @patch('guardian.integrations.swimlane_connector.requests.post')
    def test_trigger_swimlane_workflow(self, mock_post, swimlane_connector):
        """Test triggering Swimlane workflow"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = swimlane_connector.trigger_swimlane_workflow('rec-789', 'Revoke Access')

        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['workflowName'] == 'Revoke Access'

    @patch('guardian.integrations.swimlane_connector.requests.patch')
    def test_update_record_status(self, mock_patch, swimlane_connector):
        """Test updating Swimlane record status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        result = swimlane_connector.update_record_status('rec-789', 'resolved')

        assert result is True
        call_args = mock_patch.call_args
        payload = call_args[1]['json']
        assert payload['status'] == 'resolved'

    @patch('guardian.integrations.swimlane_connector.requests.patch')
    def test_attach_evidence_to_record(self, mock_patch, swimlane_connector):
        """Test attaching evidence to Swimlane record"""
        evidence = {
            'event_name': 'ConsoleLogin',
            'principal': 'arn:aws:iam::123:user/admin',
            'source_ip': '192.168.1.1'
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        result = swimlane_connector.attach_evidence_to_record('rec-789', evidence)

        assert result is True
        call_args = mock_patch.call_args
        payload = call_args[1]['json']
        assert 'evidence' in payload


class TestSwimlaneWorkflowResults:
    """Group 4: Swimlane workflow results and status synchronization"""

    @pytest.fixture
    def swimlane_connector(self):
        return SwimlaneConnector('https://swimlane.example.com', 'api_key', 'app_123')

    @patch('guardian.integrations.swimlane_connector.requests.get')
    def test_receive_playbook_result(self, mock_get, swimlane_connector):
        """Test retrieving playbook/workflow results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'workflow_id': 'wf-123',
            'status': 'completed',
            'result': {'action': 'revoked_access', 'users_affected': 2}
        }
        mock_get.return_value = mock_response

        result = swimlane_connector.receive_playbook_result('wf-123')

        assert result['status'] == 'completed'
        assert result['result']['users_affected'] == 2

    @patch('guardian.integrations.swimlane_connector.requests.patch')
    def test_sync_status_with_swimlane(self, mock_patch, swimlane_connector):
        """Test synchronizing incident status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        result = swimlane_connector.sync_status_with_soar('rec-789', 'in_progress')

        assert result is True

    @patch('guardian.integrations.swimlane_connector.requests.get')
    def test_get_available_workflows(self, mock_get, swimlane_connector):
        """Test retrieving available workflows"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'name': 'Revoke Access', 'id': 'wf-1'},
                {'name': 'Isolate Network', 'id': 'wf-2'},
                {'name': 'Block IP', 'id': 'wf-3'}
            ]
        }
        mock_get.return_value = mock_response

        workflows = swimlane_connector.get_available_playbooks()

        assert len(workflows) == 3
        assert workflows[0]['name'] == 'Revoke Access'

    @patch('guardian.integrations.swimlane_connector.requests.get')
    def test_get_available_workflows_empty(self, mock_get, swimlane_connector):
        """Test when no workflows available"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        mock_get.return_value = mock_response

        workflows = swimlane_connector.get_available_playbooks()

        assert len(workflows) == 0


class TestBidirectionalSynchronization:
    """Bonus: Bidirectional status synchronization tests"""

    @patch('guardian.integrations.splunk_phantom_connector.requests.post')
    def test_phantom_sync_status(self, mock_post):
        """Test Phantom status synchronization"""
        connector = SplunkPhantomConnector('https://phantom.example.com', 'token')

        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = connector.sync_status_with_soar('12345', 'closed')

        assert result is True

    @patch('guardian.integrations.splunk_phantom_connector.requests.get')
    def test_phantom_get_case_summary(self, mock_get):
        """Test getting Phantom case summary"""
        connector = SplunkPhantomConnector('https://phantom.example.com', 'token')

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'AWS Security Alert',
            'status': 'open',
            'severity': 'high',
            'artifact_count': 5
        }
        mock_get.return_value = mock_response

        summary = connector.get_phantom_case_summary('12345')

        assert summary['name'] == 'AWS Security Alert'
        assert summary['artifact_count'] == 5

    def test_severity_conversion(self):
        """Test AWS to SOAR severity conversion"""
        connector = SplunkPhantomConnector('https://phantom.example.com', 'token')

        assert connector._convert_severity(9) == 'critical'
        assert connector._convert_severity(7) == 'high'
        assert connector._convert_severity(5) == 'medium'
        assert connector._convert_severity(2) == 'low'

    def test_swimlane_format_incident(self):
        """Test incident formatting for Swimlane"""
        connector = SwimlaneConnector('https://swimlane.example.com', 'key', 'app')

        incident = {
            'title': 'Security Alert',
            'description': 'Test alert',
            'severity': 8,
            'threat_id': 'threat_1',
            'account_id': 'account_1'
        }

        formatted = connector._format_for_swimlane(incident)

        assert formatted['title'] == 'Security Alert'
        assert formatted['threat_id'] == 'threat_1'
