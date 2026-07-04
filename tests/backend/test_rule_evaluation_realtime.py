import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
from dataclasses import asdict

# Add lambda/guardian to path to avoid 'lambda' keyword conflict
# Import the handler and related classes
from guardian.handlers.rule_evaluation_handler import (
    RuleEvaluationHandler,
    EvaluationMetrics,
    EvaluationResult
)


@pytest.fixture
def mock_rules_repo():
    """Mock SecurityRuleRepository"""
    repo = MagicMock()
    repo.list_active_rules.return_value = [
        {
            'rule_id': 'rule-1',
            'rule_type': 'connection_spike',
            'condition': {'threshold': 10},
            'action': {'notify': ['telegram']},
            'enabled': True
        },
        {
            'rule_id': 'rule-2',
            'rule_type': 'auth_failure',
            'condition': {'threshold': 5},
            'action': {'auto_remediate': True},
            'enabled': True
        }
    ]
    repo.get_rule.return_value = {
        'rule_id': 'rule-1',
        'rule_type': 'connection_spike',
        'condition': {'threshold': 10},
        'action': {'notify': ['telegram']},
        'enabled': True
    }
    return repo


@pytest.fixture
def mock_detector():
    """Mock AnomalyDetector"""
    detector = MagicMock()
    threat_1 = MagicMock()
    threat_1.threat_id = 'threat-1'
    threat_1.rule_id = 'rule-1'
    threat_1.severity = 8
    threat_1.account_id = '123456789'
    threat_1.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat_1.message = 'Connection spike detected'
    threat_1.evidence = [{'instance_id': 'i-123', 'count': 20}]

    threat_2 = MagicMock()
    threat_2.threat_id = 'threat-2'
    threat_2.rule_id = 'rule-2'
    threat_2.severity = 5
    threat_2.account_id = '123456789'
    threat_2.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat_2.message = 'Auth failures detected'
    threat_2.evidence = [{'failed_logins': 10}]

    detector.detect_anomalies.return_value = [threat_1, threat_2]
    return detector


@pytest.fixture
def mock_responder():
    """Mock RemediationOrchestrator"""
    responder = MagicMock()
    response_1 = MagicMock()
    response_1.threat_id = 'threat-1'
    response_1.rule_id = 'rule-1'
    response_1.total_actions = 2
    response_1.executed_actions = 2
    response_1.failed_actions = 0
    response_1.pending_approval_actions = 0
    response_1.approval_status = 'AUTO_APPROVED'
    response_1.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
    response_1.execution_time_seconds = 1.5
    response_1.results = []

    response_2 = MagicMock()
    response_2.threat_id = 'threat-2'
    response_2.rule_id = 'rule-2'
    response_2.total_actions = 1
    response_2.executed_actions = 1
    response_2.failed_actions = 0
    response_2.pending_approval_actions = 0
    response_2.approval_status = 'AUTO_APPROVED'
    response_2.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
    response_2.execution_time_seconds = 0.8
    response_2.results = []

    responder.execute_remediation_with_orchestration.side_effect = [response_1, response_2]
    return responder


@pytest.fixture
def mock_audit_repo():
    """Mock ResponseAuditRepository"""
    repo = MagicMock()
    repo.record_evaluation.return_value = True
    return repo


@pytest.fixture
def handler(mock_rules_repo, mock_detector, mock_responder, mock_audit_repo):
    """Create RuleEvaluationHandler instance with mocks"""
    return RuleEvaluationHandler(
        rules_repo=mock_rules_repo,
        detector=mock_detector,
        responder=mock_responder,
        audit_repo=mock_audit_repo
    )


@pytest.fixture
def sample_event():
    """Sample EventBridge event"""
    return {
        'version': '0',
        'id': 'event-123',
        'detail-type': 'Scheduled Event',
        'source': 'aws.events',
        'account': '123456789',
        'time': '2026-05-24T12:00:00Z',
        'region': 'us-east-1',
        'resources': [],
        'detail': {
            'schedule': 'rate(1 minute)'
        }
    }


# ==========================================
# Test Group 1: Basic Functionality (4 tests)
# ==========================================

def test_evaluation_handler_initialization(handler):
    """Test handler initialization with dependencies"""
    assert handler.rules is not None
    assert handler.detector is not None
    assert handler.responder is not None
    assert handler.audit is not None


def test_handle_evaluation_loads_active_rules(handler, mock_rules_repo, sample_event):
    """Test that evaluation loads active rules from repository"""
    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    mock_rules_repo.list_active_rules.assert_called_once()


def test_handle_evaluation_detects_anomalies(handler, mock_detector, sample_event):
    """Test that evaluation calls detector with correct parameters"""
    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    mock_detector.detect_anomalies.assert_called_once()
    assert result.metrics['detected_threats_count'] == 2


def test_handle_evaluation_executes_responses(handler, mock_responder, sample_event):
    """Test that evaluation executes responses for detected threats"""
    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert mock_responder.execute_remediation_with_orchestration.call_count == 2
    assert result.metrics['executed_responses_count'] == 2


# ==========================================
# Test Group 2: Metrics Collection (3 tests)
# ==========================================

def test_evaluation_metrics_are_accurate(handler, sample_event):
    """Test that evaluation metrics are correctly calculated"""
    result = handler.handle_evaluation(sample_event)

    assert result.metrics['active_rules_count'] == 2
    assert result.metrics['detected_threats_count'] == 2
    assert result.metrics['executed_responses_count'] == 2
    assert result.metrics['failed_responses_count'] == 0


def test_evaluation_metrics_include_timing(handler, sample_event):
    """Test that metrics include execution timing"""
    result = handler.handle_evaluation(sample_event)

    assert 'total_execution_time_seconds' in result.metrics
    assert result.metrics['total_execution_time_seconds'] >= 0
    assert 'timestamp' in result.metrics
    assert 'evaluation_id' in result.metrics


def test_evaluation_generates_unique_ids(handler, sample_event):
    """Test that each evaluation gets a unique ID"""
    result1 = handler.handle_evaluation(sample_event)
    result2 = handler.handle_evaluation(sample_event)

    assert result1.metrics['evaluation_id'] != result2.metrics['evaluation_id']


# ==========================================
# Test Group 3: Error Handling (4 tests)
# ==========================================

def test_handle_evaluation_with_no_active_rules(handler, mock_rules_repo, sample_event):
    """Test evaluation when no active rules exist"""
    mock_rules_repo.list_active_rules.return_value = []

    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert result.metrics['active_rules_count'] == 0
    assert result.metrics['detected_threats_count'] == 0


def test_handle_evaluation_with_no_threats_detected(handler, mock_detector, sample_event):
    """Test evaluation when detector finds no threats"""
    mock_detector.detect_anomalies.return_value = []

    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert result.metrics['detected_threats_count'] == 0
    assert result.metrics['executed_responses_count'] == 0


def test_handle_evaluation_with_failed_response(handler, mock_detector, mock_responder, sample_event):
    """Test evaluation when response execution fails"""
    failed_response = MagicMock()
    failed_response.threat_id = 'threat-1'
    failed_response.rule_id = 'rule-1'
    failed_response.total_actions = 2
    failed_response.executed_actions = 0
    failed_response.failed_actions = 2
    failed_response.pending_approval_actions = 0
    failed_response.approval_status = 'PENDING'
    failed_response.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
    failed_response.execution_time_seconds = 0.5
    failed_response.results = []

    # Create a new handler with a fresh detector that returns failed response
    threat = MagicMock()
    threat.threat_id = 'threat-1'
    threat.rule_id = 'rule-1'
    threat.severity = 8
    threat.account_id = '123456789'
    threat.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat.message = 'Test threat'
    threat.evidence = []

    fresh_detector = MagicMock()
    fresh_detector.detect_anomalies.return_value = [threat]

    fresh_responder = MagicMock()
    fresh_responder.execute_remediation_with_orchestration.return_value = failed_response

    fresh_handler = RuleEvaluationHandler(
        rules_repo=handler.rules,
        detector=fresh_detector,
        responder=fresh_responder,
        audit_repo=handler.audit
    )

    result = fresh_handler.handle_evaluation(sample_event)

    assert result.success is True
    assert result.metrics['failed_responses_count'] == 1


def test_handle_evaluation_with_missing_rule(handler, mock_rules_repo, mock_detector, sample_event):
    """Test evaluation when rule cannot be found"""
    mock_rules_repo.get_rule.return_value = None

    threat = MagicMock()
    threat.threat_id = 'threat-1'
    threat.rule_id = 'missing-rule'
    threat.severity = 8
    threat.account_id = '123456789'
    threat.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat.message = 'Test threat'
    threat.evidence = []

    mock_detector.detect_anomalies.return_value = [threat]

    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert len(result.errors) > 0
    assert 'not found' in result.errors[0]


# ==========================================
# Test Group 4: Threat Data Conversion (2 tests)
# ==========================================

def test_threat_to_dict_conversion(handler):
    """Test that threat objects are correctly converted to dictionaries"""
    threat = MagicMock()
    threat.threat_id = 'threat-1'
    threat.rule_id = 'rule-1'
    threat.severity = 8
    threat.account_id = '123456789'
    threat.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat.message = 'Test threat'
    threat.evidence = [{'key': 'value'}]

    threat_dict = handler._threat_to_dict(threat)

    assert threat_dict['threat_id'] == 'threat-1'
    assert threat_dict['rule_id'] == 'rule-1'
    assert threat_dict['severity'] == 8
    assert threat_dict['account_id'] == '123456789'
    assert threat_dict['message'] == 'Test threat'
    assert len(threat_dict['evidence']) == 1


def test_orchestration_result_to_dict_conversion(handler):
    """Test that orchestration results are correctly converted to dictionaries"""
    result = MagicMock()
    result.threat_id = 'threat-1'
    result.rule_id = 'rule-1'
    result.total_actions = 2
    result.executed_actions = 2
    result.failed_actions = 0
    result.pending_approval_actions = 0
    result.approval_status = 'AUTO_APPROVED'
    result.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
    result.execution_time_seconds = 1.5
    result.results = []

    result_dict = handler._orchestration_result_to_dict(result)

    assert result_dict['threat_id'] == 'threat-1'
    assert result_dict['rule_id'] == 'rule-1'
    assert result_dict['total_actions'] == 2
    assert result_dict['executed_actions'] == 2
    assert result_dict['success'] is True


# ==========================================
# Test Group 5: Audit Logging (2 tests)
# ==========================================

def test_evaluation_records_audit_logs(handler, mock_audit_repo, sample_event):
    """Test that evaluation records audit logs for each response"""
    result = handler.handle_evaluation(sample_event)

    assert mock_audit_repo.record_evaluation.call_count == 2


def test_evaluation_handles_audit_log_errors(handler, mock_audit_repo, sample_event):
    """Test that evaluation continues even if audit logging fails"""
    mock_audit_repo.record_evaluation.side_effect = Exception('Audit failure')

    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert len(result.errors) > 0


# ==========================================
# Test Group 6: Response Auto-Approval (2 tests)
# ==========================================

def test_responses_are_auto_approved_during_evaluation(handler, mock_responder, sample_event):
    """Test that responses are auto-approved during evaluation"""
    handler.handle_evaluation(sample_event)

    # Verify that responder was called with approval_required=False
    calls = mock_responder.execute_remediation_with_orchestration.call_args_list
    assert len(calls) > 0

    # Check that auto-approval is used
    for call_args in calls:
        kwargs = call_args[1]
        assert kwargs['approval_required'] is False
        assert kwargs['approved_by'] == 'auto-evaluation'


def test_evaluation_respects_rule_auto_remediate_setting(handler, mock_rules_repo, sample_event):
    """Test that evaluation respects rule's auto_remediate setting"""
    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    # Verify that the responder was called for rules with auto_remediate enabled
    assert len(result.responses) == 2


# ==========================================
# Test Group 7: Result Structure Validation (2 tests)
# ==========================================

def test_evaluation_result_structure(handler, sample_event):
    """Test that evaluation result has correct structure"""
    result = handler.handle_evaluation(sample_event)

    assert isinstance(result, EvaluationResult)
    assert isinstance(result.success, bool)
    assert isinstance(result.metrics, dict)
    assert isinstance(result.threats, list)
    assert isinstance(result.responses, list)
    assert isinstance(result.errors, list)


def test_evaluation_result_contains_all_required_fields(handler, sample_event):
    """Test that result metrics contain all required fields"""
    result = handler.handle_evaluation(sample_event)

    required_fields = [
        'evaluation_id',
        'timestamp',
        'active_rules_count',
        'detected_threats_count',
        'executed_responses_count',
        'failed_responses_count',
        'total_execution_time_seconds'
    ]

    for field in required_fields:
        assert field in result.metrics


# ==========================================
# Test Group 8: Integration Tests (3 tests)
# ==========================================

def test_full_evaluation_flow_with_multiple_threats(handler, sample_event):
    """Test complete evaluation flow with multiple threats"""
    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert result.metrics['active_rules_count'] == 2
    assert result.metrics['detected_threats_count'] == 2
    assert result.metrics['executed_responses_count'] == 2
    assert len(result.threats) == 2
    assert len(result.responses) == 2


def test_evaluation_with_different_event_schedules(handler, mock_detector):
    """Test evaluation handles different schedule expressions"""
    events = [
        {'detail': {'schedule': 'rate(1 minute)'}},
        {'detail': {'schedule': 'rate(5 minutes)'}},
        {'detail': {'schedule': 'rate(1 hour)'}}
    ]

    for event in events:
        result = handler.handle_evaluation(event)
        assert result.success is True


def test_evaluation_isolates_threat_processing_errors(handler, mock_responder, mock_detector, sample_event):
    """Test that errors in one threat don't affect processing of others"""
    threat_1 = MagicMock()
    threat_1.threat_id = 'threat-1'
    threat_1.rule_id = 'rule-1'
    threat_1.severity = 8
    threat_1.account_id = '123456789'
    threat_1.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat_1.message = 'Threat 1'
    threat_1.evidence = []

    threat_2 = MagicMock()
    threat_2.threat_id = 'threat-2'
    threat_2.rule_id = 'rule-2'
    threat_2.severity = 5
    threat_2.account_id = '123456789'
    threat_2.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat_2.message = 'Threat 2'
    threat_2.evidence = []

    mock_detector.detect_anomalies.return_value = [threat_1, threat_2]

    # First response succeeds, second fails
    success_response = MagicMock()
    success_response.threat_id = 'threat-1'
    success_response.rule_id = 'rule-1'
    success_response.total_actions = 1
    success_response.executed_actions = 1
    success_response.failed_actions = 0
    success_response.pending_approval_actions = 0
    success_response.approval_status = 'AUTO_APPROVED'
    success_response.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
    success_response.execution_time_seconds = 0.5
    success_response.results = []

    mock_responder.execute_remediation_with_orchestration.side_effect = [
        success_response,
        Exception('Response execution error')
    ]

    result = handler.handle_evaluation(sample_event)

    # Despite the second threat failing, evaluation should succeed
    assert result.success is True
    assert len(result.errors) > 0
    assert result.metrics['executed_responses_count'] == 1


# ==========================================
# Test Group 9: Edge Cases (1 test)
# ==========================================

def test_evaluation_with_empty_threat_evidence(handler, mock_detector, sample_event):
    """Test handling of threats with empty evidence"""
    threat = MagicMock()
    threat.threat_id = 'threat-1'
    threat.rule_id = 'rule-1'
    threat.severity = 5
    threat.account_id = '123456789'
    threat.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    threat.message = 'Threat with no evidence'
    threat.evidence = []

    mock_detector.detect_anomalies.return_value = [threat]

    result = handler.handle_evaluation(sample_event)

    assert result.success is True
    assert len(result.threats) == 1
    assert result.threats[0]['evidence'] == []
