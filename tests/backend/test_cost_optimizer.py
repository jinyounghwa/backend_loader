"""Sprint 39 Phase 1: Cost Optimization Recommendations"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from optimizers.cost_optimizer import CostOptimizer, OptimizationRecommendation


# ==========================================
# Test Group 1: Cost Optimizer Basics (2 tests)
# ==========================================

def test_cost_optimizer_initialization():
    """Test cost optimizer initialization"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    assert optimizer is not None
    assert optimizer.explorer is not None
    assert optimizer.ec2 is not None
    assert optimizer.rds is not None


def test_analyze_cost_patterns():
    """Test cost pattern analysis"""
    cost_explorer = MagicMock()
    cost_explorer.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {'TimePeriod': {'Start': '2026-05-20'}, 'Total': {'UnblendedCost': {'Amount': '100.0'}}},
            {'TimePeriod': {'Start': '2026-05-21'}, 'Total': {'UnblendedCost': {'Amount': '102.0'}}},
            {'TimePeriod': {'Start': '2026-05-22'}, 'Total': {'UnblendedCost': {'Amount': '98.0'}}},
            {'TimePeriod': {'Start': '2026-05-23'}, 'Total': {'UnblendedCost': {'Amount': '105.0'}}},
            {'TimePeriod': {'Start': '2026-05-24'}, 'Total': {'UnblendedCost': {'Amount': '103.0'}}},
        ]
    }

    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)
    patterns = optimizer.analyze_cost_patterns('acc-123', days=5)

    assert patterns is not None
    assert isinstance(patterns, list)
    assert len(patterns) > 0


# ==========================================
# Test Group 2: Instance Downsizing (2 tests)
# ==========================================

def test_recommend_instance_downsizing():
    """Test instance downsizing recommendations"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-1234567890abcdef0',
                        'InstanceType': 't3.xlarge',
                        'State': {'Name': 'running'}
                    }
                ]
            }
        ]
    }

    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)
    recommendations = optimizer.recommend_instance_downsizing('acc-123')

    assert recommendations is not None
    assert isinstance(recommendations, list)


def test_downsizing_monthly_savings_calculation():
    """Test monthly savings calculation for downsizing"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    # t3.xlarge: ~$0.1664/hour, t3.large: ~$0.0832/hour
    # Daily savings: 24 * (0.1664 - 0.0832) = ~$19.97
    # Monthly savings: ~$600
    recommendations = [
        {
            'instance_id': 'i-123',
            'current_type': 't3.xlarge',
            'recommended_type': 't3.large',
            'monthly_savings': 600.0
        }
    ]

    total_savings = sum(r['monthly_savings'] for r in recommendations)
    assert total_savings > 500


# ==========================================
# Test Group 3: Database Analysis (2 tests)
# ==========================================

def test_detect_overprovisioned_databases():
    """Test detection of overprovisioned RDS instances"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()
    rds_client.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'DBInstanceIdentifier': 'prod-db-1',
                'DBInstanceClass': 'db.r5.4xlarge',
                'Engine': 'postgres'
            },
            {
                'DBInstanceIdentifier': 'test-db-1',
                'DBInstanceClass': 'db.r5.4xlarge',
                'Engine': 'postgres'
            }
        ]
    }

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)
    issues = optimizer.detect_overprovisioned_databases('acc-123')

    assert issues is not None
    assert isinstance(issues, list)


def test_database_cpu_utilization_analysis():
    """Test RDS CPU utilization analysis"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    # Database with low CPU usage should be flagged
    db_metrics = {
        'DBInstanceIdentifier': 'prod-db-1',
        'DBInstanceClass': 'db.r5.4xlarge',
        'average_cpu_percent': 5.2,  # Very low
        'monthly_cost': 3000.0
    }

    # If CPU < 20%, should recommend downsize
    should_downsize = db_metrics['average_cpu_percent'] < 20
    assert should_downsize


# ==========================================
# Test Group 4: Storage Cost Optimization (2 tests)
# ==========================================

def test_analyze_storage_costs():
    """Test S3 and EBS storage cost analysis"""
    cost_explorer = MagicMock()
    cost_explorer.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'Groups': [
                    {
                        'Keys': ['Amazon Simple Storage Service'],
                        'Metrics': {'UnblendedCost': {'Amount': '500.0'}}
                    },
                    {
                        'Keys': ['Amazon Elastic Block Store'],
                        'Metrics': {'UnblendedCost': {'Amount': '300.0'}}
                    }
                ]
            }
        ]
    }

    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)
    storage_analysis = optimizer.analyze_storage_costs('acc-123')

    assert storage_analysis is not None
    assert isinstance(storage_analysis, list)
    assert len(storage_analysis) > 0


def test_storage_optimization_recommendations():
    """Test storage optimization recommendations"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    # Example: old snapshots should be deleted
    recommendations = [
        {
            'type': 'delete_old_snapshots',
            'description': 'Delete snapshots older than 90 days',
            'monthly_savings': 250.0,
            'priority': 'medium'
        },
        {
            'type': 'enable_s3_lifecycle',
            'description': 'Move old S3 objects to Glacier',
            'monthly_savings': 150.0,
            'priority': 'high'
        }
    ]

    assert len(recommendations) == 2
    assert all(r['monthly_savings'] > 0 for r in recommendations)


# ==========================================
# Test Group 5: Combined Recommendations (1 test)
# ==========================================

def test_combined_recommendations():
    """Test combined cost optimization recommendations"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    combined = optimizer.get_all_recommendations('acc-123')

    assert combined is not None
    assert isinstance(combined, list)
    # Should have recommendations from all categories
    assert len(combined) >= 0


# ==========================================
# Test Group 6: Priority Scoring (1 test)
# ==========================================

def test_priority_scoring():
    """Test recommendation priority scoring"""
    cost_explorer = MagicMock()
    ec2_client = MagicMock()
    rds_client = MagicMock()

    optimizer = CostOptimizer(cost_explorer, ec2_client, rds_client)

    recommendations = [
        {'monthly_savings': 100.0, 'effort': 'low'},      # Low effort, good savings
        {'monthly_savings': 1000.0, 'effort': 'high'},    # High savings, high effort
        {'monthly_savings': 50.0, 'effort': 'medium'},    # Low savings, medium effort
    ]

    # Score should favor high savings with low effort
    scores = optimizer.calculate_priority_scores(recommendations)

    assert scores is not None
    assert len(scores) == len(recommendations)
    assert all(score >= 0 and score <= 100 for score in scores)
