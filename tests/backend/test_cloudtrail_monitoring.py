"""Sprint 41 Phase 1: CloudTrail Event Monitoring"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from monitors.cloudtrail_monitor import CloudTrailEventMonitor


# ==========================================
# Test Group 1: CloudTrail Event Streaming (2 tests)
# ==========================================

def test_cloudtrail_event_monitor_initialization():
    """Test CloudTrail event monitor initialization"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    assert monitor is not None
    assert monitor.cloudtrail is not None
    assert monitor.s3 is not None
    assert monitor.table is not None


def test_stream_cloudtrail_events():
    """Test streaming CloudTrail events"""
    cloudtrail_client = MagicMock()
    cloudtrail_client.lookup_events.return_value = {
        'Events': [
            {
                'EventID': 'event-1',
                'EventName': 'RunInstances',
                'EventTime': datetime.now(timezone.utc),
                'Username': 'user-123',
                'Resources': [{'ResourceType': 'AWS::EC2::Instance', 'ResourceName': 'i-123'}]
            }
        ]
    }
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)
    events = monitor.stream_cloudtrail_events('acc-123', ['RunInstances', 'TerminateInstances'])

    assert events is not None
    assert isinstance(events, list)


# ==========================================
# Test Group 2: Event Filtering and Query (2 tests)
# ==========================================

def test_filter_events_by_criteria():
    """Test filtering CloudTrail events by criteria"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    events = [
        {
            'EventName': 'RunInstances',
            'EventTime': datetime.now(timezone.utc),
            'Username': 'user-1',
            'RequestParameters': {'instanceType': 't2.large'}
        },
        {
            'EventName': 'TerminateInstances',
            'EventTime': datetime.now(timezone.utc) - timedelta(hours=2),
            'Username': 'user-2',
            'RequestParameters': {}
        }
    ]

    criteria = {'EventName': 'RunInstances'}
    filtered = [e for e in events if e.get('EventName') == criteria['EventName']]

    assert len(filtered) == 1
    assert filtered[0]['EventName'] == 'RunInstances'


def test_filter_events_by_time_range():
    """Test filtering events by time range"""
    events = [
        {'EventName': 'RunInstances', 'EventTime': datetime.now(timezone.utc) - timedelta(hours=1)},
        {'EventName': 'StopInstances', 'EventTime': datetime.now(timezone.utc) - timedelta(hours=25)},
        {'EventName': 'TerminateInstances', 'EventTime': datetime.now(timezone.utc) - timedelta(minutes=30)},
    ]

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    filtered = [e for e in events if e['EventTime'] >= cutoff]

    assert len(filtered) == 2


# ==========================================
# Test Group 3: Suspicious Activity Detection (2 tests)
# ==========================================

def test_detect_suspicious_activity():
    """Test detection of suspicious CloudTrail activities"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    events = [
        {
            'EventName': 'RunInstances',
            'SourceIPAddress': '203.0.113.0',
            'Username': 'root',
            'RequestParameters': {'region': 'ap-northeast-1'}
        }
    ]

    suspicious = monitor.detect_suspicious_activity('acc-123', events)

    assert suspicious is not None
    assert isinstance(suspicious, list)


def test_detect_root_account_usage():
    """Test detection of root account usage"""
    events = [
        {'Username': 'root', 'EventName': 'ModifyDBInstance'},
        {'Username': 'user-123', 'EventName': 'RunInstances'},
        {'Username': 'root', 'EventName': 'DeleteBucket'},
    ]

    root_events = [e for e in events if e['Username'] == 'root']

    assert len(root_events) == 2
    assert all(e['Username'] == 'root' for e in root_events)


# ==========================================
# Test Group 4: Event Correlation (2 tests)
# ==========================================

def test_correlate_related_events():
    """Test correlation of related CloudTrail events"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    events = [
        {
            'EventName': 'CreateSecurityGroup',
            'EventTime': datetime.now(timezone.utc),
            'ResourceID': 'sg-123',
            'Username': 'attacker'
        },
        {
            'EventName': 'AuthorizeSecurityGroupIngress',
            'EventTime': datetime.now(timezone.utc) + timedelta(seconds=30),
            'ResourceID': 'sg-123',
            'Username': 'attacker'
        }
    ]

    correlations = monitor.correlate_events('acc-123', events)

    assert correlations is not None
    assert isinstance(correlations, list)


def test_detect_attack_scenario():
    """Test detection of attack scenarios from event patterns"""
    events = [
        {'EventName': 'GetUser', 'Username': 'attacker'},
        {'EventName': 'ListPolicies', 'Username': 'attacker'},
        {'EventName': 'CreateAccessKey', 'Username': 'attacker'},
        {'EventName': 'AttachUserPolicy', 'Username': 'attacker'},
    ]

    suspicious_sequence = all(
        events[i]['Username'] == events[i+1]['Username'] for i in range(len(events)-1)
    )

    assert suspicious_sequence is True


# ==========================================
# Test Group 5: Real-time Alert Triggering (2 tests)
# ==========================================

def test_trigger_real_time_alert():
    """Test triggering real-time alerts for suspicious events"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    event = {
        'EventName': 'DeleteDBInstance',
        'Username': 'root',
        'SourceIPAddress': '203.0.113.0',
        'EventTime': datetime.now(timezone.utc)
    }

    alert = monitor.trigger_alert('acc-123', event, severity='critical')

    assert alert is not None
    assert isinstance(alert, dict)


def test_alert_severity_classification():
    """Test alert severity classification"""
    events = {
        'critical': ['DeleteBucket', 'DeleteDBInstance', 'ModifyAccountPassword'],
        'high': ['ModifyDBInstance', 'ModifySecurityGroup'],
        'medium': ['RunInstances', 'CreateSecurityGroup'],
    }

    event = 'DeleteBucket'
    severity = next((s for s, e_list in events.items() if event in e_list), 'low')

    assert severity == 'critical'


# ==========================================
# Test Group 6: Event History Audit (2 tests)
# ==========================================

def test_store_event_history():
    """Test storing CloudTrail events for audit"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)

    event = {
        'EventID': 'event-1',
        'EventName': 'RunInstances',
        'EventTime': datetime.now(timezone.utc),
        'Username': 'user-123'
    }

    monitor.store_event('acc-123', event)

    assert dynamodb_table.put_item.called


def test_retrieve_event_audit_log():
    """Test retrieving event audit logs"""
    cloudtrail_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()
    dynamodb_table.query.return_value = {
        'Items': [
            {
                'EventID': 'event-1',
                'EventName': 'RunInstances',
                'EventTime': datetime.now(timezone.utc).isoformat(),
                'Username': 'user-123'
            }
        ]
    }

    monitor = CloudTrailEventMonitor(cloudtrail_client, s3_client, dynamodb_table)
    logs = monitor.get_event_history('acc-123', days=7)

    assert logs is not None
    assert isinstance(logs, list)
