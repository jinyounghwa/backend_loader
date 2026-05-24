"""Sprint 43 Phase 1: Real-time CloudTrail Integration"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.cloudtrail_stream_handler import CloudTrailStreamHandler
from processors.event_normalizer import EventNormalizer


# ==========================================
# Test Group 1: Real-time Stream Processing (3 tests)
# ==========================================

def test_cloudtrail_stream_handler_initialization():
    """Test CloudTrail stream handler initialization"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    assert handler is not None
    assert handler.table is not None


def test_process_cloudtrail_stream():
    """Test processing CloudTrail events from stream"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    records = [
        {
            'eventID': 'event-001',
            'eventSource': 'ec2.amazonaws.com',
            'eventName': 'RunInstances',
            'awsRegion': 'us-east-1',
            'sourceIPAddress': '192.168.1.1',
            'userAgent': 'aws-cli/2.0',
            'requestParameters': {'instanceType': 't2.micro'},
            'responseElements': {'instancesSet': {'items': [{'instanceId': 'i-123'}]}},
            'eventTime': datetime.now(timezone.utc).isoformat()
        }
    ]

    result = handler.process_cloudtrail_stream(records)

    assert result is not None
    assert isinstance(result, dict)


def test_extract_api_calls():
    """Test extracting API calls from CloudTrail events"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    event = {
        'eventID': 'event-001',
        'eventSource': 'ec2.amazonaws.com',
        'eventName': 'RunInstances',
        'userIdentity': {'principalId': 'AIDACKCEVSQ6C2EXAMPLE'},
        'sourceIPAddress': '192.168.1.1',
        'requestParameters': {'instanceType': 't2.micro'}
    }

    calls = handler.extract_api_calls(event)

    assert calls is not None
    assert isinstance(calls, list)


# ==========================================
# Test Group 2: Event Normalization (3 tests)
# ==========================================

def test_event_normalizer_initialization():
    """Test event normalizer initialization"""
    normalizer = EventNormalizer()

    assert normalizer is not None


def test_normalize_cloudtrail_event():
    """Test normalizing CloudTrail event for analysis"""
    normalizer = EventNormalizer()

    raw_event = {
        'eventID': 'event-001',
        'eventSource': 'ec2.amazonaws.com',
        'eventName': 'RunInstances',
        'awsRegion': 'us-east-1',
        'sourceIPAddress': '192.168.1.1',
        'userIdentity': {'principalId': 'AIDACKCEVSQ6C2EXAMPLE', 'type': 'IAMUser'},
        'requestParameters': {'instanceType': 't2.micro', 'imageId': 'ami-123'},
        'responseElements': {'instancesSet': {'items': [{'instanceId': 'i-123'}]}},
        'eventTime': datetime.now(timezone.utc).isoformat()
    }

    normalized = normalizer.normalize_cloudtrail_event(raw_event)

    assert normalized is not None
    assert isinstance(normalized, dict)


def test_extract_principal():
    """Test extracting principal (user/role) from event"""
    normalizer = EventNormalizer()

    event = {
        'userIdentity': {
            'principalId': 'AIDACKCEVSQ6C2EXAMPLE',
            'type': 'IAMUser',
            'arn': 'arn:aws:iam::123456789012:user/testuser',
            'accountId': '123456789012'
        }
    }

    principal = normalizer.extract_principal(event)

    assert principal is not None
    assert isinstance(principal, dict)


# ==========================================
# Test Group 3: Threat Correlation (3 tests)
# ==========================================

def test_filter_by_risk_level():
    """Test filtering API calls by risk level"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    calls = [
        {'eventName': 'GetObject', 'riskScore': 1},
        {'eventName': 'DeleteBucket', 'riskScore': 9},
        {'eventName': 'ListBuckets', 'riskScore': 2}
    ]

    high_risk = handler.filter_by_risk_level(calls, threshold=5)

    assert high_risk is not None
    assert isinstance(high_risk, list)


def test_correlate_suspicious_events():
    """Test correlating suspicious events for pattern detection"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    events = [
        {
            'eventName': 'FailedLogin',
            'sourceIPAddress': '10.0.0.1',
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        {
            'eventName': 'FailedLogin',
            'sourceIPAddress': '10.0.0.1',
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        {
            'eventName': 'FailedLogin',
            'sourceIPAddress': '10.0.0.1',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    ]

    correlated = handler.correlate_suspicious_events(events)

    assert correlated is not None
    assert isinstance(correlated, list)


def test_calculate_event_risk_score():
    """Test calculating risk score for API calls"""
    normalizer = EventNormalizer()

    event = {
        'eventName': 'DeleteBucket',
        'sourceIPAddress': '10.0.0.1',
        'userIdentity': {'type': 'IAMUser'},
        'awsRegion': 'us-east-1'
    }

    score = normalizer.calculate_event_risk_score(event)

    assert score is not None
    assert isinstance(score, (int, float))
    assert 0 <= score <= 10


# ==========================================
# Test Group 4: Immediate Alert Triggering (3 tests)
# ==========================================

def test_trigger_immediate_alert():
    """Test triggering immediate alert for detected threat"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    threat = {
        'threatType': 'unauthorized_deletion',
        'severity': 9,
        'eventId': 'event-001',
        'principal': 'arn:aws:iam::123456789012:user/testuser',
        'resource': 'arn:aws:s3:::my-bucket',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = handler.trigger_immediate_alert(threat)

    assert result is not None
    assert isinstance(result, dict)


def test_stream_handler_alert_notification():
    """Test alert notification sent through handler"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    alert = {
        'alert_id': 'alert-001',
        'severity': 'high',
        'message': 'Suspicious API call detected',
        'events': [
            {'eventName': 'DeleteBucket', 'timestamp': datetime.now(timezone.utc).isoformat()}
        ],
        'recommended_action': 'Review and take remediation action'
    }

    notification = handler._format_alert_message(alert)

    assert notification is not None
    assert isinstance(notification, str)


def test_stream_handler_error_handling():
    """Test error handling in stream processor"""
    dynamodb_table = MagicMock()

    handler = CloudTrailStreamHandler(dynamodb_table)

    invalid_records = [
        {
            'malformed_field': 'missing_required_fields'
        }
    ]

    result = handler.process_cloudtrail_stream(invalid_records)

    assert result is not None
    assert isinstance(result, dict)
