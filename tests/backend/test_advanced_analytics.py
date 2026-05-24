"""Sprint 42 Phase 4: Advanced Visualization & Analytics"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from analytics.dashboard_generator import DashboardGenerator
from analytics.trend_analyzer import TrendAnalyzer
from storage.metrics_warehouse import MetricsWarehouse


# ==========================================
# Test Group 1: Metrics Collection (2 tests)
# ==========================================

def test_metrics_warehouse_initialization():
    """Test metrics warehouse initialization"""
    dynamodb_table = MagicMock()
    cloudwatch_client = MagicMock()

    warehouse = MetricsWarehouse(dynamodb_table, cloudwatch_client)

    assert warehouse is not None
    assert warehouse.table is not None
    assert warehouse.cloudwatch is not None


def test_store_and_retrieve_metrics():
    """Test storing and retrieving metrics from warehouse"""
    dynamodb_table = MagicMock()
    cloudwatch_client = MagicMock()

    warehouse = MetricsWarehouse(dynamodb_table, cloudwatch_client)

    # Store metric
    metric = {
        'metric_name': 'total_cost',
        'value': 150.75,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'dimensions': {'account_id': 'acc-001'}
    }

    store_result = warehouse.store_metric(metric)
    assert store_result is not None

    # Retrieve metrics
    timeseries = warehouse.get_timeseries_data('total_cost', days=7)
    assert timeseries is not None


# ==========================================
# Test Group 2: Trend Analysis (2 tests)
# ==========================================

def test_trend_analyzer_initialization():
    """Test trend analyzer initialization"""
    dynamodb_table = MagicMock()

    analyzer = TrendAnalyzer(dynamodb_table)

    assert analyzer is not None
    assert analyzer.table is not None


def test_analyze_cost_trends():
    """Test analyzing cost trends over time"""
    dynamodb_table = MagicMock()

    analyzer = TrendAnalyzer(dynamodb_table)

    # Mock historical cost data
    cost_data = [
        {'date': '2026-05-20', 'cost': 100},
        {'date': '2026-05-21', 'cost': 110},
        {'date': '2026-05-22', 'cost': 115},
        {'date': '2026-05-23', 'cost': 125},
        {'date': '2026-05-24', 'cost': 130}
    ]

    trend = analyzer.analyze_cost_trends(cost_data)

    assert trend is not None
    assert 'trend_direction' in trend or 'slope' in trend


# ==========================================
# Test Group 3: Dashboard Generation (3 tests)
# ==========================================

def test_dashboard_generator_initialization():
    """Test dashboard generator initialization"""
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    generator = DashboardGenerator(cloudwatch_client, dynamodb_table)

    assert generator is not None
    assert generator.cloudwatch is not None


def test_generate_health_dashboard():
    """Test generating health status dashboard"""
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    generator = DashboardGenerator(cloudwatch_client, dynamodb_table)

    dashboard = generator.generate_health_dashboard('acc-001')

    assert dashboard is not None
    assert 'status' in dashboard or 'summary' in dashboard


def test_generate_cost_dashboard():
    """Test generating cost analysis dashboard"""
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    generator = DashboardGenerator(cloudwatch_client, dynamodb_table)

    dashboard = generator.generate_cost_dashboard('acc-001')

    assert dashboard is not None


# ==========================================
# Test Group 4: Predictions & Insights (3 tests)
# ==========================================

def test_predict_future_costs():
    """Test predicting future costs using trend analysis"""
    dynamodb_table = MagicMock()

    analyzer = TrendAnalyzer(dynamodb_table)

    # Historical cost data
    historical_costs = [100, 105, 110, 115, 120]

    prediction = analyzer.predict_future_costs(historical_costs, days_ahead=7)

    assert prediction is not None
    assert isinstance(prediction, dict)


def test_identify_cost_drivers():
    """Test identifying top cost drivers in account"""
    dynamodb_table = MagicMock()

    analyzer = TrendAnalyzer(dynamodb_table)

    cost_breakdown = {
        'EC2': 450,
        'S3': 200,
        'RDS': 150,
        'Lambda': 50
    }

    drivers = analyzer.identify_cost_drivers(cost_breakdown)

    assert drivers is not None
    assert isinstance(drivers, list)


def test_generate_executive_summary():
    """Test generating executive summary with insights"""
    cloudwatch_client = MagicMock()
    dynamodb_table = MagicMock()

    generator = DashboardGenerator(cloudwatch_client, dynamodb_table)

    summary = generator.generate_executive_summary('acc-001')

    assert summary is not None
    assert isinstance(summary, dict)
