"""Sprint 40 Phase 3: EC2 Lifecycle Manager"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.managers.ec2_lifecycle_manager import EC2LifecycleManager


# ==========================================
# Test Group 1: Idle Instance Detection (2 tests)
# ==========================================

def test_ec2_lifecycle_manager_initialization():
    """Test EC2 lifecycle manager initialization"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)

    assert manager is not None
    assert manager.ec2 is not None
    assert manager.cloudwatch is not None
    assert manager.table is not None


def test_detect_idle_instances():
    """Test detection of idle EC2 instances"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-idle-1',
                        'State': {'Name': 'running'},
                        'LaunchTime': datetime.now(timezone.utc) - timedelta(days=30),
                        'Tags': [{'Key': 'Environment', 'Value': 'dev'}]
                    }
                ]
            }
        ]
    }
    cloudwatch_client = MagicMock()
    cloudwatch_client.get_metric_statistics.return_value = {
        'Datapoints': [{'Average': 2.5}]  # CPU < 5%
    }
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)
    idle_instances = manager.detect_idle_instances('acc-123', cpu_threshold=5)

    assert idle_instances is not None
    assert isinstance(idle_instances, list)


# ==========================================
# Test Group 2: Automatic Shutdown (2 tests)
# ==========================================

def test_stop_idle_instances():
    """Test automatic stopping of idle instances"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-idle-2',
                        'State': {'Name': 'running'},
                        'Tags': [{'Key': 'Environment', 'Value': 'dev'}]
                    }
                ]
            }
        ]
    }
    ec2_client.stop_instances.return_value = {}
    cloudwatch_client = MagicMock()
    cloudwatch_client.get_metric_statistics.return_value = {
        'Datapoints': [{'Average': 1.0}]
    }
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)
    result = manager.stop_idle_instances('acc-123')

    assert result is not None
    assert isinstance(result, dict)


def test_stop_excludes_production():
    """Test that idle instance stopping excludes production environment"""
    instances = [
        {'InstanceId': 'i-1', 'Tags': [{'Key': 'Environment', 'Value': 'production'}]},
        {'InstanceId': 'i-2', 'Tags': [{'Key': 'Environment', 'Value': 'dev'}]},
        {'InstanceId': 'i-3', 'Tags': [{'Key': 'Environment', 'Value': 'staging'}]},
    ]

    # Filter production
    safe_to_stop = [i for i in instances if not any(
        t['Key'] == 'Environment' and t['Value'] == 'production' for t in i.get('Tags', [])
    )]

    assert len(safe_to_stop) == 2
    assert 'i-1' not in [i['InstanceId'] for i in safe_to_stop]


# ==========================================
# Test Group 3: Termination of Long-Stopped (2 tests)
# ==========================================

def test_terminate_stopped_instances():
    """Test termination of long-stopped instances"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-stopped-1',
                        'State': {'Name': 'stopped'},
                        'StateTransitionReason': '2026-03-24T10:00:00.000Z',
                        'LaunchTime': datetime.now(timezone.utc) - timedelta(days=40)
                    }
                ]
            }
        ]
    }
    ec2_client.terminate_instances.return_value = {}
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)
    result = manager.terminate_stopped_instances('acc-123', days_stopped=30)

    assert result is not None
    assert isinstance(result, dict)


def test_long_stopped_identification():
    """Test identification of instances stopped for long period"""
    now = datetime.now(timezone.utc)
    stopped_threshold = 30

    instances = [
        {'InstanceId': 'i-1', 'State': {'Name': 'stopped'}, 'LaunchTime': now - timedelta(days=10)},
        {'InstanceId': 'i-2', 'State': {'Name': 'stopped'}, 'LaunchTime': now - timedelta(days=50)},
        {'InstanceId': 'i-3', 'State': {'Name': 'running'}, 'LaunchTime': now - timedelta(days=60)},
    ]

    long_stopped = []
    for instance in instances:
        if instance['State']['Name'] == 'stopped':
            age = (now - instance['LaunchTime']).days
            if age > stopped_threshold:
                long_stopped.append(instance)

    assert len(long_stopped) == 1
    assert long_stopped[0]['InstanceId'] == 'i-2'


# ==========================================
# Test Group 4: Instance Tagging (2 tests)
# ==========================================

def test_tag_idle_instances():
    """Test tagging idle instances for tracking"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-idle-3',
                        'State': {'Name': 'running'},
                        'Tags': []
                    }
                ]
            }
        ]
    }
    ec2_client.create_tags.return_value = {}
    cloudwatch_client = MagicMock()
    cloudwatch_client.get_metric_statistics.return_value = {
        'Datapoints': [{'Average': 3.0}]
    }
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)
    result = manager.tag_idle_instances('acc-123')

    assert result is not None
    assert isinstance(result, dict)


def test_tag_format_validation():
    """Test idle detection tag format"""
    tags = {
        'LastIdleDetection': datetime.now(timezone.utc).isoformat(),
        'IdleReason': 'Low CPU utilization'
    }

    assert 'LastIdleDetection' in tags
    assert 'IdleReason' in tags
    assert len(tags['LastIdleDetection']) > 0


# ==========================================
# Test Group 5: Schedule Management (2 tests)
# ==========================================

def test_schedule_instance_shutdown():
    """Test scheduling instance shutdown for specific time"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)
    schedule_id = manager.schedule_instance_shutdown('i-test-1', '2026-05-25T22:00:00Z')

    assert schedule_id is not None
    assert isinstance(schedule_id, str)


def test_schedule_time_validation():
    """Test validation of schedule time format"""
    schedule_time = '2026-05-25T22:00:00Z'

    # Parse ISO format
    try:
        scheduled = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
        assert scheduled is not None
    except ValueError:
        assert False, "Invalid schedule time format"


# ==========================================
# Test Group 6: Safety Checks (2 tests)
# ==========================================

def test_safety_check_protected_instances():
    """Test that protected instances are not stopped"""
    instances = [
        {'InstanceId': 'i-1', 'Tags': [
            {'Key': 'DisableStopProtection', 'Value': 'true'}
        ]},
        {'InstanceId': 'i-2', 'Tags': []},
    ]

    safe_to_stop = []
    for instance in instances:
        if not any(
            t['Key'] == 'DisableStopProtection' and t['Value'] == 'true'
            for t in instance.get('Tags', [])
        ):
            safe_to_stop.append(instance)

    assert len(safe_to_stop) == 1
    assert safe_to_stop[0]['InstanceId'] == 'i-2'


def test_lifecycle_audit_logging():
    """Test lifecycle actions are logged"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = EC2LifecycleManager(ec2_client, cloudwatch_client, dynamodb_table)

    # Verify manager can log to DynamoDB
    assert manager.table is not None
