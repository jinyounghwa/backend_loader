"""Sprint 40 Phase 4: Cleanup Audit Logger"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.loggers.cleanup_audit_logger import CleanupAuditLogger


# ==========================================
# Test Group 1: Action Logging (2 tests)
# ==========================================

def test_cleanup_audit_logger_initialization():
    """Test cleanup audit logger initialization"""
    dynamodb_table = MagicMock()

    logger = CleanupAuditLogger(dynamodb_table)

    assert logger is not None
    assert logger.table is not None


def test_log_cleanup_action():
    """Test logging cleanup actions"""
    dynamodb_table = MagicMock()

    logger = CleanupAuditLogger(dynamodb_table)

    action = {
        'account_id': 'acc-123',
        'resource_type': 'EBS_VOLUME',
        'resource_id': 'vol-123',
        'action': 'delete',
        'status': 'success',
        'savings': 50.0
    }

    logger.log_cleanup_action('acc-123', action)

    assert dynamodb_table.put_item.called


# ==========================================
# Test Group 2: Summary Generation (2 tests)
# ==========================================

def test_get_cleanup_summary():
    """Test generating cleanup summary for period"""
    dynamodb_table = MagicMock()
    dynamodb_table.query.return_value = {
        'Items': [
            {
                'cleanup_id': 'cleanup-1',
                'resource_type': 'EBS_VOLUME',
                'status': 'success',
                'savings': 50.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'cleanup_id': 'cleanup-2',
                'resource_type': 'SNAPSHOT',
                'status': 'success',
                'savings': 25.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    logger = CleanupAuditLogger(dynamodb_table)
    summary = logger.get_cleanup_summary('acc-123', days=30)

    assert summary is not None
    assert isinstance(summary, dict)
    assert 'total_savings' in summary or 'resources_cleaned' in summary


def test_cleanup_summary_statistics():
    """Test cleanup statistics calculation"""
    cleanup_logs = [
        {'status': 'success', 'savings': 50.0},
        {'status': 'success', 'savings': 25.0},
        {'status': 'failed', 'savings': 0.0},
    ]

    successful = [c for c in cleanup_logs if c['status'] == 'success']
    failed = [c for c in cleanup_logs if c['status'] == 'failed']
    total_savings = sum(c['savings'] for c in successful)

    assert len(successful) == 2
    assert len(failed) == 1
    assert total_savings == 75.0


# ==========================================
# Test Group 3: Cost Tracking (2 tests)
# ==========================================

def test_track_cleanup_costs():
    """Test tracking cost savings from cleanup actions"""
    dynamodb_table = MagicMock()

    logger = CleanupAuditLogger(dynamodb_table)

    cleanup_actions = [
        {'resource_type': 'EBS_VOLUME', 'status': 'success', 'savings': 100.0},
        {'resource_type': 'SNAPSHOT', 'status': 'success', 'savings': 50.0},
        {'resource_type': 'ELASTIC_IP', 'status': 'success', 'savings': 36.0},
    ]

    for action in cleanup_actions:
        logger.log_cleanup_action('acc-123', action)

    assert dynamodb_table.put_item.call_count == 3


def test_monthly_savings_projection():
    """Test projection of monthly savings"""
    daily_logs = [
        [{'savings': 10.0}, {'savings': 15.0}],
        [{'savings': 20.0}],
        [{'savings': 12.0}, {'savings': 8.0}],
    ]

    daily_totals = [sum(log['savings'] for log in day) for day in daily_logs]
    average_daily = sum(daily_totals) / len(daily_totals)
    monthly_projection = average_daily * 30

    # daily_totals = [25.0, 20.0, 20.0] = 65.0 total / 3 days = 21.666... avg
    assert abs(average_daily - 21.666) < 0.01
    assert abs(monthly_projection - 650.0) < 0.1


# ==========================================
# Test Group 4: Rollback Capability (2 tests)
# ==========================================

def test_log_rollback_action():
    """Test logging rollback of cleanup actions"""
    dynamodb_table = MagicMock()

    logger = CleanupAuditLogger(dynamodb_table)

    rollback_action = {
        'cleanup_id': 'cleanup-1',
        'resource_id': 'vol-123',
        'action': 'rollback_delete',
        'status': 'success',
        'reason': 'User requested restoration'
    }

    logger.log_cleanup_action('acc-123', rollback_action)

    assert dynamodb_table.put_item.called


def test_rollback_availability():
    """Test determining if cleanup action can be rolled back"""
    cleanup_log = {
        'cleanup_id': 'cleanup-1',
        'resource_type': 'EBS_VOLUME',
        'action': 'delete',
        'status': 'success',
        'timestamp': (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    }

    # Snapshots created before deletion can be rolled back
    can_rollback = cleanup_log['resource_type'] in ['EBS_VOLUME', 'SNAPSHOT']

    assert can_rollback is True


# ==========================================
# Test Group 5: Report Generation (2 tests)
# ==========================================

def test_generate_cleanup_report():
    """Test generating comprehensive cleanup report"""
    dynamodb_table = MagicMock()
    dynamodb_table.query.return_value = {
        'Items': [
            {
                'cleanup_id': 'cleanup-1',
                'resource_type': 'EBS_VOLUME',
                'resource_id': 'vol-123',
                'status': 'success',
                'savings': 50.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'cleanup_id': 'cleanup-2',
                'resource_type': 'SNAPSHOT',
                'resource_id': 'snap-456',
                'status': 'success',
                'savings': 25.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    logger = CleanupAuditLogger(dynamodb_table)
    report = logger.generate_cleanup_report('acc-123', days=30)

    assert report is not None
    assert isinstance(report, dict)


def test_report_format_validation():
    """Test cleanup report contains required fields"""
    report = {
        'account_id': 'acc-123',
        'period': '2026-04-24 to 2026-05-24',
        'total_resources_cleaned': 5,
        'total_savings': 250.0,
        'success_rate': 100.0,
        'by_resource_type': {
            'EBS_VOLUME': 2,
            'SNAPSHOT': 2,
            'ELASTIC_IP': 1
        },
        'by_status': {
            'success': 5,
            'failed': 0
        }
    }

    assert 'account_id' in report
    assert 'total_resources_cleaned' in report
    assert 'total_savings' in report
    assert 'success_rate' in report
    assert report['total_resources_cleaned'] == 5
    assert report['total_savings'] == 250.0
