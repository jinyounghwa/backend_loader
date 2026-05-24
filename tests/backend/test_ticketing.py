"""Tests for automated ticketing system - Phase 1 of Sprint 44"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda/guardian'))

from services.jira_service import JiraTicketService
from services.servicenow_service import ServiceNowTicketService
from handlers.ticketing_handler import TicketingHandler


class TestJiraTicketCreation:
    """Group 1: Jira ticket creation tests"""

    @pytest.fixture
    def jira_service(self):
        return JiraTicketService(
            base_url='https://company.atlassian.net',
            api_token='test_token',
            project_key='SEC'
        )

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'rule_123',
            'severity': 8,
            'message': 'Unauthorized API call detected',
            'threat_type': 'unauthorized_action',
            'account_id': 'aws_123456',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'evidence': {
                'event_name': 'StopInstances',
                'principal': 'arn:aws:iam::123456:user/attacker',
                'source_ip': '192.168.1.1'
            }
        }

    @patch('services.jira_service.requests.post')
    def test_jira_create_issue_success(self, mock_post, jira_service, sample_threat):
        """Test successful Jira issue creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'key': 'SEC-123'}
        mock_post.return_value = mock_response

        issue_key = jira_service.create_issue(sample_threat)

        assert issue_key == 'SEC-123'
        mock_post.assert_called_once()

    @patch('services.jira_service.requests.post')
    def test_jira_create_issue_high_severity(self, mock_post, jira_service, sample_threat):
        """Test Jira issue creation with high severity (8/10)"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'key': 'SEC-456'}
        mock_post.return_value = mock_response

        issue_key = jira_service.create_issue(sample_threat)

        assert issue_key == 'SEC-456'
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['fields']['priority']['name'] == 'Highest'
        assert payload['fields']['issuetype']['name'] == 'Critical'

    @patch('services.jira_service.requests.post')
    def test_jira_create_issue_low_severity(self, mock_post, jira_service, sample_threat):
        """Test Jira issue creation with low severity (3/10)"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'key': 'SEC-789'}
        mock_post.return_value = mock_response

        sample_threat['severity'] = 3
        issue_key = jira_service.create_issue(sample_threat)

        assert issue_key == 'SEC-789'
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['fields']['priority']['name'] == 'Low'


class TestServiceNowIncidentCreation:
    """Group 2: ServiceNow incident creation tests"""

    @pytest.fixture
    def servicenow_service(self):
        return ServiceNowTicketService(
            instance_url='https://company.service-now.com',
            api_key='test_api_key'
        )

    @pytest.fixture
    def sample_threat(self):
        return {
            'rule_id': 'rule_456',
            'severity': 7,
            'message': 'Suspected credential compromise',
            'threat_type': 'iam_anomaly',
            'account_id': 'aws_789012',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @patch('services.servicenow_service.requests.post')
    def test_servicenow_create_incident_success(self, mock_post, servicenow_service, sample_threat):
        """Test successful ServiceNow incident creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'result': {'number': 'INC0010001'}}
        mock_post.return_value = mock_response

        incident_number = servicenow_service.create_incident(sample_threat)

        assert incident_number == 'INC0010001'
        mock_post.assert_called_once()

    @patch('services.servicenow_service.requests.post')
    def test_servicenow_create_incident_severity_mapping(self, mock_post, servicenow_service, sample_threat):
        """Test ServiceNow severity conversion (AWS 7/10 -> SNOW 2)"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'result': {'number': 'INC0010002'}}
        mock_post.return_value = mock_response

        incident_number = servicenow_service.create_incident(sample_threat)

        assert incident_number == 'INC0010002'
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['severity'] == 2
        assert payload['urgency'] == 2

    @patch('services.servicenow_service.requests.post')
    def test_servicenow_escalate_incident(self, mock_post, servicenow_service):
        """Test ServiceNow incident escalation for critical severity"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = servicenow_service.escalate_incident('INC0010001', severity=9)

        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['escalation'] == 3
        assert payload['assignment_group'] == 'AWS Security Leadership'


class TestEvidenceEnrichment:
    """Group 3: Evidence collection and enrichment tests"""

    @pytest.fixture
    def ticketing_handler(self):
        return TicketingHandler()

    @pytest.fixture
    def threat_with_evidence(self):
        return {
            'rule_id': 'rule_789',
            'severity': 6,
            'message': 'Unusual API activity',
            'threat_type': 'api_abuse',
            'account_id': 'aws_345678',
            'evidence': {
                'event_name': 'CreateAccessKey',
                'principal': 'arn:aws:iam::123456:user/admin',
                'source_ip': '10.0.0.5',
                'user_agent': 'aws-cli/2.0.0'
            }
        }

    def test_enrich_threat_with_evidence(self, ticketing_handler, threat_with_evidence):
        """Test threat enrichment with CloudTrail evidence"""
        enriched = ticketing_handler.enrich_ticket_with_evidence(threat_with_evidence)

        assert 'evidence_summary' in enriched
        assert 'evidence_logs' in enriched
        assert 'detection_timestamp' in enriched
        assert enriched['risk_score'] == 6

    def test_evidence_summary_formatting(self, ticketing_handler, threat_with_evidence):
        """Test evidence summary contains key details"""
        enriched = ticketing_handler.enrich_ticket_with_evidence(threat_with_evidence)
        summary = enriched['evidence_summary']

        assert 'CreateAccessKey' in summary
        assert 'admin' in summary
        assert '10.0.0.5' in summary

    def test_enrich_threat_without_evidence(self, ticketing_handler):
        """Test enrichment when evidence is missing"""
        threat = {
            'rule_id': 'rule_000',
            'severity': 4,
            'message': 'Low risk activity',
            'threat_type': 'monitor'
        }

        enriched = ticketing_handler.enrich_ticket_with_evidence(threat)

        assert 'risk_score' in enriched
        assert 'detection_timestamp' in enriched
        assert enriched == threat.copy() or 'evidence_logs' not in enriched


class TestAssigneeAndEscalation:
    """Group 4: Assignee assignment and escalation tests"""

    @pytest.fixture
    def ticketing_handler(self):
        return TicketingHandler()

    def test_assign_ec2_threat_to_infrastructure(self, ticketing_handler):
        """Test EC2 threat assignment to infrastructure team"""
        threat = {
            'rule_id': 'rule_ec2',
            'severity': 5,
            'threat_type': 'EC2_Unauthorized_Access'
        }

        assignee = ticketing_handler.add_assignee_by_rule(threat)

        assert assignee['team'] == 'infrastructure'
        assert assignee['on_call_group'] == 'infra-oncall'

    def test_assign_s3_threat_to_storage(self, ticketing_handler):
        """Test S3 threat assignment to storage team"""
        threat = {
            'rule_id': 'rule_s3',
            'severity': 7,
            'threat_type': 'S3_Public_Access'
        }

        assignee = ticketing_handler.add_assignee_by_rule(threat)

        assert assignee['team'] == 'storage'
        assert assignee['on_call_group'] == 'storage-oncall'

    def test_assign_iam_threat_to_identity(self, ticketing_handler):
        """Test IAM threat assignment to identity team"""
        threat = {
            'rule_id': 'rule_iam',
            'severity': 8,
            'threat_type': 'IAM_Privilege_Escalation'
        }

        assignee = ticketing_handler.add_assignee_by_rule(threat)

        assert assignee['team'] == 'identity'
        assert assignee['on_call_group'] == 'identity-oncall'

    def test_escalate_critical_threat_to_leadership(self, ticketing_handler):
        """Test critical threat (severity >= 8) escalation"""
        threat = {
            'rule_id': 'rule_critical',
            'severity': 9,
            'threat_type': 'unknown_threat'
        }

        assignee = ticketing_handler.add_assignee_by_rule(threat)

        assert assignee['escalation_required'] is True
        assert assignee['escalate_to'] == 'Security Leadership'

    def test_no_escalation_for_low_severity(self, ticketing_handler):
        """Test low severity threat not escalated"""
        threat = {
            'rule_id': 'rule_low',
            'severity': 3,
            'threat_type': 'monitoring_event'
        }

        assignee = ticketing_handler.add_assignee_by_rule(threat)

        assert 'escalation_required' not in assignee or assignee.get('escalation_required') is False


class TestTicketLifecycleTracking:
    """Group 4 (bonus): Ticket lifecycle tracking tests"""

    @pytest.fixture
    def ticketing_handler(self):
        return TicketingHandler()

    def test_track_ticket_creation(self, ticketing_handler):
        """Test tracking ticket creation event"""
        threat_id = 'rule_123'
        status = {'jira': 'SEC-100', 'servicenow': 'INC0001'}

        record = ticketing_handler.track_ticket_lifecycle(threat_id, 'created', status)

        assert record['threat_id'] == threat_id
        assert record['event_type'] == 'created'
        assert 'timestamp' in record

    def test_track_ticket_update(self, ticketing_handler):
        """Test tracking ticket status update"""
        threat_id = 'rule_456'
        status = {'status': 'in_progress'}

        record = ticketing_handler.track_ticket_lifecycle(threat_id, 'updated', status)

        assert record['event_type'] == 'updated'
        assert record['status'] == status

    def test_parse_sns_event_threats(self, ticketing_handler):
        """Test parsing threats from SNS event"""
        event = {
            'Records': [
                {
                    'Sns': {
                        'Message': json.dumps({
                            'threat': {
                                'rule_id': 'rule_1',
                                'severity': 7,
                                'message': 'Test threat'
                            }
                        })
                    }
                }
            ]
        }

        threats = ticketing_handler._parse_event_threats(event)

        assert len(threats) == 1
        assert threats[0]['rule_id'] == 'rule_1'

    def test_parse_eventbridge_event_threats(self, ticketing_handler):
        """Test parsing threats from EventBridge event"""
        event = {
            'detail': {
                'threat': {
                    'rule_id': 'rule_2',
                    'severity': 5,
                    'message': 'Another threat'
                }
            }
        }

        threats = ticketing_handler._parse_event_threats(event)

        assert len(threats) == 1
        assert threats[0]['rule_id'] == 'rule_2'


class TestEndToEndTicketing:
    """Integration tests for end-to-end ticketing"""

    def test_create_ticket_without_services(self):
        """Test creating ticket when no services configured"""
        handler = TicketingHandler()

        threat = {
            'rule_id': 'rule_no_service',
            'severity': 5,
            'message': 'Test with no services',
            'threat_type': 'test',
            'account_id': 'aws_test'
        }

        result = handler.create_ticket(threat)

        assert result['threat_id'] == 'rule_no_service'
        assert result['status'] == 'failed'
        assert 'tickets' in result
        assert len(result['tickets']) == 0

    def test_handler_enrich_and_assign_flow(self):
        """Test the enrichment and assignment flow through handler"""
        handler = TicketingHandler()

        threat = {
            'rule_id': 'rule_flow',
            'severity': 7,
            'message': 'Flow test',
            'threat_type': 's3_public',
            'account_id': 'aws_flow',
            'evidence': {
                'event': 'PutBucketPolicy',
                'bucket': 'my-bucket'
            }
        }

        enriched = handler.enrich_ticket_with_evidence(threat)
        assignee = handler.add_assignee_by_rule(enriched)

        assert enriched['risk_score'] == 7
        assert assignee['team'] == 'storage'
        assert 'escalation_required' not in assignee or assignee['escalation_required'] is False
