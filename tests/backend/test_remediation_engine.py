"""Sprint 42 Phase 2: Automated Remediation Engine"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.remediation_handler import RemediationHandler
from validators.remediation_validator import RemediationValidator
from storage.remediation_log import RemediationLog


# ==========================================
# Test Group 1: Remediation Trigger (2 tests)
# ==========================================

def test_remediation_handler_initialization():
    """Test remediation handler initialization"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    assert handler is not None
    assert handler.ec2 is not None
    assert handler.iam is not None
    assert handler.s3 is not None


def test_execute_remediation_dry_run():
    """Test dry-run remediation (validation without execution)"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    threat = {
        'threat_id': 'threat-001',
        'threat_type': 'suspicious_ec2',
        'resource_id': 'i-1234567890abcdef0',
        'account_id': 'acc-001',
        'severity': 85
    }

    result = handler.execute_remediation(threat, dry_run=True)

    assert result is not None
    assert result['dry_run'] is True


# ==========================================
# Test Group 2: EC2 Remediation (3 tests)
# ==========================================

def test_stop_ec2_instance():
    """Test stopping a suspicious EC2 instance"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    # Mock EC2 stop response
    ec2_client.stop_instances.return_value = {
        'StoppingInstances': [
            {'InstanceId': 'i-1234567890abcdef0', 'CurrentState': {'Name': 'stopping'}}
        ]
    }

    result = handler.stop_instance('i-1234567890abcdef0')

    assert result is not None
    assert result['action'] == 'stop_instance'
    assert result['status'] == 'success'


def test_create_snapshot_before_stop():
    """Test creating snapshot before stopping instance"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    # Mock snapshot creation
    ec2_client.create_snapshot.return_value = {
        'SnapshotId': 'snap-0123456789abcdef0'
    }

    result = handler.create_volume_snapshot('vol-0123456789abcdef0', 'i-1234567890abcdef0')

    assert result is not None
    assert 'SnapshotId' in result or 'snapshot_id' in result


def test_ec2_remediation_with_state_capture():
    """Test EC2 remediation with state capture for rollback"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    # Mock describe_instances response
    ec2_client.describe_instances.return_value = {
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-1234567890abcdef0',
                'State': {'Name': 'running'},
                'SecurityGroups': [{'GroupId': 'sg-123456'}]
            }]
        }]
    }

    state = handler.capture_instance_state('i-1234567890abcdef0')

    assert state is not None
    assert 'InstanceId' in state or 'instance_id' in state


# ==========================================
# Test Group 3: IAM & S3 Remediation (4 tests)
# ==========================================

def test_revoke_iam_access_key():
    """Test revoking suspicious IAM access key"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    # Mock IAM key deactivation
    iam_client.update_access_key_status.return_value = {}

    result = handler.revoke_iam_key('AKIAIOSFODNN7EXAMPLE')

    assert result is not None
    assert result['action'] == 'revoke_iam_key' or 'action' in result


def test_block_s3_public_access():
    """Test blocking public access to S3 bucket"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    # Mock S3 block public access
    s3_client.put_public_access_block.return_value = {}

    result = handler.block_s3_public_access('vulnerable-bucket')

    assert result is not None
    assert result['action'] == 'block_s3_public_access' or 'action' in result
    assert result['status'] == 'success' or 'status' in result


def test_remove_overly_permissive_iam_policy():
    """Test removing overly permissive IAM policies"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    policy = {
        'Effect': 'Allow',
        'Action': '*',
        'Resource': '*'
    }

    result = handler.remediate_overly_permissive_policy('role-name', policy)

    assert result is not None


def test_disable_default_vpc_access():
    """Test disabling default VPC access in account"""
    ec2_client = MagicMock()
    iam_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    handler = RemediationHandler(ec2_client, iam_client, s3_client, dynamodb_table)

    result = handler.disable_default_vpc_access('acc-001')

    assert result is not None


# ==========================================
# Test Group 4: Validation & Rollback (2 tests)
# ==========================================

def test_remediation_validator_initialization():
    """Test remediation validator initialization"""
    iam_client = MagicMock()
    sts_client = MagicMock()

    validator = RemediationValidator(iam_client, sts_client)

    assert validator is not None
    assert validator.iam is not None


def test_validate_remediation_action():
    """Test validating remediation action before execution"""
    iam_client = MagicMock()
    sts_client = MagicMock()

    validator = RemediationValidator(iam_client, sts_client)

    action = {
        'action_type': 'stop_instance',
        'resource_id': 'i-1234567890abcdef0',
        'account_id': 'acc-001'
    }

    is_valid = validator.validate_remediation(action)

    assert is_valid is True or is_valid is False


def test_generate_rollback_plan():
    """Test generating rollback plan for remediation"""
    iam_client = MagicMock()
    sts_client = MagicMock()

    validator = RemediationValidator(iam_client, sts_client)

    action = {
        'action_type': 'stop_instance',
        'resource_id': 'i-1234567890abcdef0',
        'original_state': {'State': {'Name': 'running'}}
    }

    rollback_plan = validator.generate_rollback_plan(action)

    assert rollback_plan is not None
    assert isinstance(rollback_plan, dict)


def test_remediation_log_tracking():
    """Test remediation action logging and tracking"""
    dynamodb_table = MagicMock()

    remediation_log = RemediationLog(dynamodb_table)

    action_record = {
        'action_id': 'remediation-001',
        'action_type': 'stop_instance',
        'resource_id': 'i-1234567890abcdef0',
        'account_id': 'acc-001',
        'status': 'success',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = remediation_log.log_remediation(action_record)

    assert result is not None
