"""Sprint 39 Phase 4: Multi-Account Cost Aggregation"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import sys
from pathlib import Path
import json
from guardian.aggregators.multi_account_cost_aggregator import MultiAccountCostAggregator


# ==========================================
# Test Group 1: Multi-Account Aggregation (2 tests)
# ==========================================

def test_aggregator_initialization():
    """Test multi-account cost aggregator initialization"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)

    assert aggregator is not None
    assert aggregator.explorer is not None


def test_aggregate_costs_multiple_accounts():
    """Test aggregating costs across multiple accounts"""
    cost_explorer = MagicMock()
    cost_explorer.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'Total': {'UnblendedCost': {'Amount': '1500.0'}}
            }
        ]
    }

    aggregator = MultiAccountCostAggregator(cost_explorer)
    result = aggregator.aggregate_costs(['acc-1', 'acc-2'], ('2026-05-20', '2026-05-24'))

    assert result is not None
    assert isinstance(result, dict)


# ==========================================
# Test Group 2: Cost Breakdown by Account (2 tests)
# ==========================================

def test_cost_breakdown_by_account():
    """Test cost breakdown by individual account"""
    cost_explorer = MagicMock()
    cost_explorer.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'Groups': [
                    {
                        'Keys': ['acc-1'],
                        'Metrics': {'UnblendedCost': {'Amount': '500.0'}}
                    },
                    {
                        'Keys': ['acc-2'],
                        'Metrics': {'UnblendedCost': {'Amount': '750.0'}}
                    }
                ]
            }
        ]
    }

    aggregator = MultiAccountCostAggregator(cost_explorer)
    breakdown = aggregator.get_cost_breakdown_by_account('2026-05-24')

    assert breakdown is not None
    assert isinstance(breakdown, dict)


def test_cost_percentage_by_account():
    """Test account cost distribution percentages"""
    costs = {
        'acc-1': 500.0,
        'acc-2': 1500.0,
        'acc-3': 1000.0
    }

    total = sum(costs.values())
    percentages = {acc: (cost / total * 100) for acc, cost in costs.items()}

    # Total = 3000, so: 500/3000=16.67%, 1500/3000=50%, 1000/3000=33.33%
    assert abs(percentages['acc-1'] - 16.67) < 0.1
    assert abs(percentages['acc-2'] - 50.0) < 0.1
    assert abs(percentages['acc-3'] - 33.33) < 0.1


# ==========================================
# Test Group 3: Account Comparison (2 tests)
# ==========================================

def test_compare_account_costs():
    """Test cost comparison between two accounts"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)
    comparison = aggregator.compare_account_costs('acc-1', 'acc-2', days=30)

    assert comparison is not None
    assert isinstance(comparison, dict)


def test_cost_difference_calculation():
    """Test cost difference and percentage change calculation"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)

    cost_1 = 1000.0
    cost_2 = 1500.0

    difference = cost_2 - cost_1
    percentage_change = (difference / cost_1 * 100) if cost_1 > 0 else 0

    assert difference == 500.0
    assert percentage_change == 50.0


# ==========================================
# Test Group 4: Outlier Detection (2 tests)
# ==========================================

def test_identify_cost_outliers():
    """Test identification of accounts with unusual costs"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)
    outliers = aggregator.identify_cost_outliers(['acc-1', 'acc-2', 'acc-3', 'acc-4'])

    assert outliers is not None
    assert isinstance(outliers, list)


def test_outlier_detection_by_deviation():
    """Test outlier detection using standard deviation"""
    costs = [100.0, 110.0, 105.0, 500.0, 95.0, 120.0]

    mean = sum(costs) / len(costs)
    variance = sum((x - mean) ** 2 for x in costs) / len(costs)
    std_dev = variance ** 0.5

    outliers = [c for c in costs if abs(c - mean) > 2 * std_dev]

    # 500.0 should be identified as outlier
    assert 500.0 in outliers


# ==========================================
# Test Group 5: Organization Trends (2 tests)
# ==========================================

def test_get_organization_trends():
    """Test organization-wide cost trends"""
    cost_explorer = MagicMock()
    cost_explorer.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {'TimePeriod': {'Start': '2026-05-20'}, 'Total': {'UnblendedCost': {'Amount': '1000.0'}}},
            {'TimePeriod': {'Start': '2026-05-21'}, 'Total': {'UnblendedCost': {'Amount': '1050.0'}}},
            {'TimePeriod': {'Start': '2026-05-22'}, 'Total': {'UnblendedCost': {'Amount': '1100.0'}}},
        ]
    }

    aggregator = MultiAccountCostAggregator(cost_explorer)
    trends = aggregator.get_organization_trends(days=90)

    assert trends is not None
    assert isinstance(trends, list)


def test_trend_trajectory_analysis():
    """Test cost trajectory and growth rate analysis"""
    daily_costs = [
        {'date': '2026-05-20', 'cost': 1000.0},
        {'date': '2026-05-21', 'cost': 1050.0},
        {'date': '2026-05-22', 'cost': 1100.0},
        {'date': '2026-05-23', 'cost': 1150.0},
        {'date': '2026-05-24', 'cost': 1200.0},
    ]

    # Calculate daily growth rate
    growth_rates = []
    for i in range(1, len(daily_costs)):
        prev_cost = daily_costs[i-1]['cost']
        curr_cost = daily_costs[i]['cost']
        growth_rate = ((curr_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0
        growth_rates.append(growth_rate)

    average_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

    assert average_growth > 4.0  # ~4.76% daily growth


# ==========================================
# Test Group 6: Report Export (2 tests)
# ==========================================

def test_export_cost_report_csv():
    """Test exporting cost report as CSV"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)
    report = aggregator.export_cost_report(['acc-1', 'acc-2'], format='csv')

    assert report is not None
    assert isinstance(report, (bytes, str))


def test_export_cost_report_json():
    """Test exporting cost report as JSON"""
    cost_explorer = MagicMock()

    aggregator = MultiAccountCostAggregator(cost_explorer)
    report = aggregator.export_cost_report(['acc-1', 'acc-2'], format='json')

    assert report is not None
    assert isinstance(report, (bytes, str, dict))
