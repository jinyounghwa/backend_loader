"""Sprint 43 Phase 4: Cost Optimization Recommendations"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from optimizers.cost_optimizer_engine import CostOptimizerEngine
from calculators.roi_calculator import ROICalculator


# ==========================================
# Test Group 1: Resource Utilization Analysis (3 tests)
# ==========================================

def test_cost_optimizer_engine_initialization():
    """Test cost optimizer engine initialization"""
    cloudwatch_client = MagicMock()

    optimizer = CostOptimizerEngine(cloudwatch_client)

    assert optimizer is not None
    assert optimizer.cloudwatch is not None


def test_analyze_resource_utilization():
    """Test analyzing resource utilization metrics"""
    cloudwatch_client = MagicMock()

    optimizer = CostOptimizerEngine(cloudwatch_client)

    resources = [
        {
            'resource_id': 'i-123456',
            'resource_type': 'EC2',
            'cpu_utilization': 15.2,
            'memory_utilization': 20.5,
            'network_in': 1000,
            'network_out': 500
        },
        {
            'resource_id': 'i-789012',
            'resource_type': 'EC2',
            'cpu_utilization': 85.0,
            'memory_utilization': 75.0,
            'network_in': 50000,
            'network_out': 30000
        }
    ]

    analysis = optimizer.analyze_resource_utilization(resources)

    assert analysis is not None
    assert isinstance(analysis, dict)


def test_generate_rightsizing_recommendations():
    """Test generating right-sizing recommendations"""
    cloudwatch_client = MagicMock()

    optimizer = CostOptimizerEngine(cloudwatch_client)

    resource = {
        'resource_id': 'i-123456',
        'resource_type': 'EC2',
        'instance_type': 't3.large',
        'cpu_utilization': 12.0,
        'memory_utilization': 18.5,
        'monthly_cost': 45.00
    }

    recommendations = optimizer.generate_rightsizing_recommendations(resource)

    assert recommendations is not None
    assert isinstance(recommendations, list)


# ==========================================
# Test Group 2: ROI Calculation (3 tests)
# ==========================================

def test_roi_calculator_initialization():
    """Test ROI calculator initialization"""
    calculator = ROICalculator()

    assert calculator is not None


def test_calculate_implementation_cost():
    """Test calculating implementation cost for optimization"""
    calculator = ROICalculator()

    optimization = {
        'optimization_type': 'right_sizing',
        'resource_id': 'i-123456',
        'effort_hours': 2,
        'hourly_rate': 50
    }

    cost = calculator.calculate_implementation_cost(optimization)

    assert cost is not None
    assert isinstance(cost, (int, float))


def test_calculate_annual_savings():
    """Test calculating annual savings from optimization"""
    calculator = ROICalculator()

    optimization = {
        'current_monthly_cost': 100.0,
        'optimized_monthly_cost': 60.0,
        'implementation_cost': 500.0
    }

    savings = calculator.calculate_annual_savings(optimization)

    assert savings is not None
    assert isinstance(savings, dict)


# ==========================================
# Test Group 3: Optimization Recommendations (2 tests)
# ==========================================

def test_calculate_payback_period():
    """Test calculating payback period for optimization"""
    calculator = ROICalculator()

    optimization = {
        'implementation_cost': 500.0,
        'monthly_savings': 40.0
    }

    payback_period = calculator.calculate_payback_period(optimization)

    assert payback_period is not None
    assert isinstance(payback_period, (int, float))


def test_prioritize_by_roi():
    """Test prioritizing optimizations by ROI"""
    calculator = ROICalculator()

    optimizations = [
        {
            'optimization_id': 'opt-001',
            'annual_savings': 2000,
            'implementation_cost': 500
        },
        {
            'optimization_id': 'opt-002',
            'annual_savings': 1000,
            'implementation_cost': 200
        },
        {
            'optimization_id': 'opt-003',
            'annual_savings': 5000,
            'implementation_cost': 1000
        }
    ]

    prioritized = calculator.prioritize_by_roi(optimizations)

    assert prioritized is not None
    assert isinstance(prioritized, list)
    assert len(prioritized) <= len(optimizations)


# ==========================================
# Test Group 4: Savings Tracking (2 tests)
# ==========================================

def test_estimate_annual_savings():
    """Test estimating total annual savings"""
    cloudwatch_client = MagicMock()

    optimizer = CostOptimizerEngine(cloudwatch_client)

    optimizations = [
        {
            'resource_id': 'i-123456',
            'monthly_savings': 30.0
        },
        {
            'resource_id': 'i-789012',
            'monthly_savings': 20.0
        },
        {
            'resource_id': 'vol-456789',
            'monthly_savings': 10.0
        }
    ]

    annual_savings = optimizer.estimate_annual_savings(optimizations)

    assert annual_savings is not None
    assert isinstance(annual_savings, (int, float))


def test_track_optimization_impact():
    """Test tracking optimization impact over time"""
    cloudwatch_client = MagicMock()

    optimizer = CostOptimizerEngine(cloudwatch_client)

    optimization = {
        'optimization_id': 'opt-001',
        'resource_id': 'i-123456',
        'optimization_type': 'right_sizing',
        'implementation_date': datetime.now(timezone.utc).isoformat(),
        'pre_optimization_cost': 100.0,
        'post_optimization_cost': 60.0,
        'status': 'implemented'
    }

    impact = optimizer.track_optimization_impact(optimization)

    assert impact is not None
    assert isinstance(impact, dict)
