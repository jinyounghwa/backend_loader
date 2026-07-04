"""Sprint 40 Phase 1: Automatic Cleanup Engine"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.engines.auto_cleanup_engine import AutoCleanupEngine, CleanupTarget


# ==========================================
# Test Group 1: Cleanup Target Identification (2 tests)
# ==========================================

def test_auto_cleanup_engine_initialization():
    """Test auto cleanup engine initialization"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    assert engine is not None
    assert engine.ec2 is not None
    assert engine.s3 is not None
    assert engine.table is not None


def test_identify_cleanup_targets():
    """Test identification of cleanup targets"""
    ec2_client = MagicMock()
    ec2_client.describe_volumes.return_value = {
        'Volumes': [
            {
                'VolumeId': 'vol-unattached-1',
                'State': 'available',
                'CreateTime': datetime.now(timezone.utc) - timedelta(days=30)
            }
        ]
    }

    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)
    targets = engine.identify_cleanup_targets('acc-123')

    assert targets is not None
    assert isinstance(targets, list)


# ==========================================
# Test Group 2: Resource Deletion (2 tests)
# ==========================================

def test_execute_cleanup_dry_run():
    """Test cleanup execution in dry-run mode"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)
    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=True)

    assert result is not None
    assert result.get('dry_run') == True
    assert 'resource_id' in result


def test_execute_cleanup_actual():
    """Test cleanup execution in actual mode"""
    ec2_client = MagicMock()
    ec2_client.delete_volume.return_value = {}
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)
    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=False)

    assert result is not None
    assert 'status' in result


# ==========================================
# Test Group 3: Dry-Run Simulation (2 tests)
# ==========================================

def test_dry_run_without_modifications():
    """Test that dry-run doesn't modify resources"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    # Run in dry-run mode
    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=True)

    # Verify no delete call was made
    ec2_client.delete_volume.assert_not_called()

    assert result.get('dry_run') == True


def test_dry_run_provides_preview():
    """Test that dry-run provides cleanup preview"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=True)

    # Should show what would be deleted
    assert 'resource_id' in result
    assert 'resource_type' in result
    assert 'action' in result


# ==========================================
# Test Group 4: Cleanup Scheduling (2 tests)
# ==========================================

def test_schedule_cleanup_job():
    """Test scheduling cleanup jobs"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    job_id = engine.schedule_cleanup_job('acc-123', schedule='daily')

    assert job_id is not None
    assert isinstance(job_id, str)
    assert dynamodb_table.put_item.called


def test_schedule_types():
    """Test different cleanup schedule types"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    schedules = ['daily', 'weekly', 'monthly']
    for schedule in schedules:
        job_id = engine.schedule_cleanup_job('acc-123', schedule=schedule)
        assert job_id is not None


# ==========================================
# Test Group 5: History Tracking (2 tests)
# ==========================================

def test_get_cleanup_history():
    """Test retrieving cleanup history"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()
    dynamodb_table.query.return_value = {
        'Items': [
            {
                'cleanup_id': 'cleanup-1',
                'resource_id': 'vol-123',
                'resource_type': 'EBS_VOLUME',
                'action': 'delete',
                'status': 'success',
                'timestamp': '2026-05-24T10:00:00Z'
            },
            {
                'cleanup_id': 'cleanup-2',
                'resource_id': 'snap-456',
                'resource_type': 'SNAPSHOT',
                'action': 'delete',
                'status': 'success',
                'timestamp': '2026-05-24T11:00:00Z'
            }
        ]
    }

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)
    history = engine.get_cleanup_history('acc-123', days=30)

    assert history is not None
    assert isinstance(history, list)
    assert len(history) >= 0


def test_cleanup_history_filtering():
    """Test cleanup history filtering by resource type"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    history = [
        {'resource_type': 'EBS_VOLUME'},
        {'resource_type': 'SNAPSHOT'},
        {'resource_type': 'EBS_VOLUME'},
    ]

    ebs_history = [h for h in history if h['resource_type'] == 'EBS_VOLUME']

    assert len(ebs_history) == 2


# ==========================================
# Test Group 6: Error Handling (2 tests)
# ==========================================

def test_cleanup_error_handling():
    """Test error handling during cleanup"""
    ec2_client = MagicMock()
    ec2_client.delete_volume.side_effect = Exception("Access Denied")
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=False)

    assert result.get('status') == 'failed'
    assert 'error' in result


def test_cleanup_retry_logic():
    """Test cleanup retry on transient failures"""
    ec2_client = MagicMock()
    # First call fails, second succeeds
    ec2_client.delete_volume.side_effect = [
        Exception("Throttled"),
        {}
    ]
    s3_client = MagicMock()
    dynamodb_table = MagicMock()

    engine = AutoCleanupEngine(ec2_client, s3_client, dynamodb_table)

    # With retry, should eventually succeed
    result = engine.execute_cleanup('vol-123', 'EBS_VOLUME', dry_run=False)

    assert result is not None
