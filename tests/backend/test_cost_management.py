"""Sprint 38 Phase 3: Cost Management System Tests"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.analyzers.cost_analyzer import CostAnalyzer, CostThreat
from guardian.storage.cost_history import CostHistoryRepository, CostRecord


# ==========================================
# Test Group 1: Cost History Basics (2 tests)
# ==========================================

def test_cost_history_repository_initialization():
    """Test cost history repository initialization"""
    table = MagicMock()
    repo = CostHistoryRepository(table)

    assert repo is not None
    assert repo.table is not None


def test_save_and_retrieve_cost_record():
    """Test saving and retrieving cost records"""
    table = MagicMock()
    table.put_item.return_value = {}
    table.get_item.return_value = {
        'Item': {
            'account_id': 'acc-123',
            'date': '2026-05-24',
            'daily_cost': 85.50,
            'service_costs': {'EC2': 45.0, 'RDS': 35.0, 'S3': 5.5},
            'timestamp': '2026-05-24T00:00:00Z'
        }
    }

    repo = CostHistoryRepository(table)

    # Save
    repo.save_daily_cost(
        account_id='acc-123',
        date='2026-05-24',
        daily_cost=85.50,
        service_costs={'EC2': 45.0, 'RDS': 35.0, 'S3': 5.5}
    )

    assert table.put_item.called

    # Retrieve
    record = repo.get_daily_cost('acc-123', '2026-05-24')
    assert record['daily_cost'] == 85.50


# ==========================================
# Test Group 2: Cost Trend Analysis (2 tests)
# ==========================================

def test_calculate_daily_trend():
    """Test daily cost trend calculation"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {'date': '2026-05-20', 'daily_cost': 80.0},
            {'date': '2026-05-21', 'daily_cost': 82.5},
            {'date': '2026-05-22', 'daily_cost': 85.0},
            {'date': '2026-05-23', 'daily_cost': 87.5},
            {'date': '2026-05-24', 'daily_cost': 90.0},
        ]
    }

    repo = CostHistoryRepository(table)
    trend = repo.get_daily_trend('acc-123', days=5)

    assert len(trend) == 5
    assert trend[0]['daily_cost'] == 80.0
    assert trend[-1]['daily_cost'] == 90.0


def test_calculate_weekly_average():
    """Test weekly average cost calculation"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {'date': '2026-05-18', 'daily_cost': 100.0},
            {'date': '2026-05-19', 'daily_cost': 105.0},
            {'date': '2026-05-20', 'daily_cost': 110.0},
            {'date': '2026-05-21', 'daily_cost': 102.0},
            {'date': '2026-05-22', 'daily_cost': 108.0},
            {'date': '2026-05-23', 'daily_cost': 115.0},
            {'date': '2026-05-24', 'daily_cost': 112.0},
        ]
    }

    repo = CostHistoryRepository(table)
    weekly_avg = repo.get_weekly_average('acc-123')

    assert weekly_avg > 0
    assert pytest.approx(weekly_avg, abs=1) == 107.4


# ==========================================
# Test Group 3: Cost Anomaly Detection (2 tests)
# ==========================================

def test_detect_cost_spike():
    """Test detection of cost spikes"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {'date': '2026-05-20', 'daily_cost': 100.0},
            {'date': '2026-05-21', 'daily_cost': 102.0},
            {'date': '2026-05-22', 'daily_cost': 101.0},
            {'date': '2026-05-23', 'daily_cost': 99.0},
            {'date': '2026-05-24', 'daily_cost': 250.0},  # Spike!
        ]
    }

    repo = CostHistoryRepository(table)
    spikes = repo.detect_cost_anomalies('acc-123', threshold_percent=100)

    assert len(spikes) > 0
    spike = spikes[0]
    assert spike['date'] == '2026-05-24'
    assert spike['daily_cost'] == 250.0
    assert spike['spike_percent'] > 100


def test_detect_sustained_high_cost():
    """Test detection of sustained high cost periods"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {'date': '2026-05-18', 'daily_cost': 100.0},
            {'date': '2026-05-19', 'daily_cost': 85.0},
            {'date': '2026-05-20', 'daily_cost': 90.0},
            {'date': '2026-05-21', 'daily_cost': 180.0},
            {'date': '2026-05-22', 'daily_cost': 175.0},
            {'date': '2026-05-23', 'daily_cost': 170.0},
            {'date': '2026-05-24', 'daily_cost': 168.0},
        ]
    }

    repo = CostHistoryRepository(table)
    sustained = repo.detect_sustained_high_cost('acc-123', days=3, threshold=150)

    assert sustained is not None
    assert sustained['duration_days'] >= 3
    assert sustained['avg_cost'] > 150


# ==========================================
# Test Group 4: Service Cost Tracking (1 test)
# ==========================================

def test_service_cost_breakdown():
    """Test service cost breakdown and tracking"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {
                'date': '2026-05-24',
                'service_costs': {
                    'EC2': 45.0,
                    'RDS': 35.0,
                    'S3': 5.5,
                    'Lambda': 2.5,
                    'DynamoDB': 7.0
                }
            }
        ]
    }

    repo = CostHistoryRepository(table)
    services = repo.get_service_breakdown('acc-123', '2026-05-24')

    assert 'EC2' in services
    assert services['EC2'] == 45.0
    assert sum(services.values()) == 95.0


# ==========================================
# Test Group 5: Cost Projection (1 test)
# ==========================================

def test_monthly_cost_projection():
    """Test monthly cost projection based on current trend"""
    table = MagicMock()
    table.query.return_value = {
        'Items': [
            {'date': '2026-05-01', 'daily_cost': 100.0},
            {'date': '2026-05-02', 'daily_cost': 102.0},
            {'date': '2026-05-03', 'daily_cost': 101.0},
            {'date': '2026-05-04', 'daily_cost': 103.0},
            {'date': '2026-05-05', 'daily_cost': 102.0},
            # ... assume daily average of 102
        ]
    }

    repo = CostHistoryRepository(table)
    projection = repo.project_monthly_cost('acc-123', current_day=5)

    assert projection is not None
    assert projection['projected_total'] > 0
    assert projection['days_elapsed'] == 5
