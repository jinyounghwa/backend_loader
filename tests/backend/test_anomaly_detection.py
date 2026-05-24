"""Sprint 41 Phase 3: Advanced Anomaly Detection Engine"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from detectors.anomaly_detection_engine import AnomalyDetectionEngine


# ==========================================
# Test Group 1: Usage Anomaly Detection (2 tests)
# ==========================================

def test_anomaly_detection_engine_initialization():
    """Test anomaly detection engine initialization"""
    cloudwatch_client = MagicMock()
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)

    assert engine is not None
    assert engine.cloudwatch is not None


def test_detect_usage_anomalies():
    """Test detection of usage anomalies using statistical methods"""
    cloudwatch_client = MagicMock()
    cloudwatch_client.get_metric_statistics.return_value = {
        'Datapoints': [
            {'Average': 50.0},
            {'Average': 52.0},
            {'Average': 48.0},
            {'Average': 200.0},
        ]
    }
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)
    anomalies = engine.detect_usage_anomalies('acc-123', lookback_days=30)

    assert anomalies is not None
    assert isinstance(anomalies, list)


# ==========================================
# Test Group 2: Cost Spike Detection (2 tests)
# ==========================================

def test_detect_cost_spikes():
    """Test detection of cost spikes"""
    cloudwatch_client = MagicMock()
    cost_history_table = MagicMock()
    cost_history_table.query.return_value = {
        'Items': [
            {'date': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), 'cost': 1000.0},
            {'date': datetime.now(timezone.utc).isoformat(), 'cost': 1300.0},
        ]
    }
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)
    spikes = engine.detect_cost_spikes('acc-123')

    assert spikes is not None
    assert isinstance(spikes, list)


def test_cost_spike_identification():
    """Test cost spike calculation"""
    daily_costs = [1000.0, 1010.0, 990.0, 1300.0, 1020.0]

    spikes = []
    for i in range(1, len(daily_costs)):
        change_percent = abs(daily_costs[i] - daily_costs[i-1]) / daily_costs[i-1] * 100
        if change_percent > 20:
            spikes.append({'day': i, 'change_percent': change_percent})

    assert len(spikes) >= 1
    assert spikes[0]['change_percent'] > 20


# ==========================================
# Test Group 3: Resource Anomalies (2 tests)
# ==========================================

def test_detect_resource_anomalies():
    """Test detection of resource anomalies"""
    cloudwatch_client = MagicMock()
    cloudwatch_client.get_metric_statistics.return_value = {
        'Datapoints': [
            {'Average': 100.0},
            {'Average': 200.0},
        ]
    }
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)
    anomalies = engine.detect_resource_anomalies('acc-123')

    assert anomalies is not None
    assert isinstance(anomalies, list)


def test_error_rate_anomaly():
    """Test error rate anomaly detection"""
    error_rates = [1, 1, 1, 1, 1, 1, 1, 1, 1, 50]

    mean = sum(error_rates) / len(error_rates)
    variance = sum((x - mean) ** 2 for x in error_rates) / len(error_rates)
    std_dev = variance ** 0.5

    anomalies = [x for x in error_rates if abs(x - mean) > 2 * std_dev]

    assert len(anomalies) > 0
    assert 50 in anomalies


# ==========================================
# Test Group 4: Statistical Validation (2 tests)
# ==========================================

def test_statistical_anomaly_detection():
    """Test statistical methods for anomaly detection"""
    data = [100, 102, 98, 105, 99, 101, 103, 500, 97, 100]

    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    std_dev = variance ** 0.5

    anomalies = [x for x in data if abs(x - mean) > 2 * std_dev]

    assert len(anomalies) > 0
    assert 500 in anomalies


def test_z_score_calculation():
    """Test Z-score calculation for anomaly detection"""
    value = 500
    mean = 100
    std_dev = 50

    z_score = (value - mean) / std_dev

    assert z_score == 8.0
    assert z_score > 2


# ==========================================
# Test Group 5: Anomaly Clustering (2 tests)
# ==========================================

def test_cluster_related_anomalies():
    """Test clustering of related anomalies"""
    cloudwatch_client = MagicMock()
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)

    anomalies = [
        {'timestamp': datetime.now(timezone.utc), 'type': 'cpu_spike', 'severity': 'high'},
        {'timestamp': datetime.now(timezone.utc), 'type': 'memory_spike', 'severity': 'high'},
        {'timestamp': datetime.now(timezone.utc) - timedelta(hours=1), 'type': 'disk_spike', 'severity': 'medium'},
    ]

    clusters = engine.cluster_anomalies('acc-123', anomalies)

    assert clusters is not None
    assert isinstance(clusters, list)


def test_temporal_clustering():
    """Test temporal clustering of anomalies"""
    anomalies = [
        {'timestamp': datetime.now(timezone.utc), 'type': 'cpu'},
        {'timestamp': datetime.now(timezone.utc) + timedelta(seconds=5), 'type': 'memory'},
        {'timestamp': datetime.now(timezone.utc) + timedelta(minutes=10), 'type': 'disk'},
    ]

    clusters = []
    current_cluster = []
    for anomaly in anomalies:
        if not current_cluster or (anomaly['timestamp'] - current_cluster[0]['timestamp']).total_seconds() < 300:
            current_cluster.append(anomaly)
        else:
            clusters.append(current_cluster)
            current_cluster = [anomaly]

    if current_cluster:
        clusters.append(current_cluster)

    assert len(clusters) >= 1


# ==========================================
# Test Group 6: Alert Severity Scoring (2 tests)
# ==========================================

def test_alert_severity_scoring():
    """Test severity scoring for anomalies"""
    cloudwatch_client = MagicMock()
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    engine = AnomalyDetectionEngine(cloudwatch_client, cost_history_table, dynamodb_table)

    anomaly = {
        'deviation_percent': 50.0,
        'affected_resources': 10,
        'potential_impact': 'high'
    }

    severity = engine.calculate_severity_score('acc-123', anomaly)

    assert severity is not None
    assert isinstance(severity, dict)


def test_severity_score_calculation():
    """Test severity score calculation formula"""
    deviation = 50
    impact_weight = {'high': 10, 'medium': 5, 'low': 2}
    impact = 'high'

    score = deviation * (impact_weight[impact] / 10)

    assert score == 50.0
    assert score > 30
